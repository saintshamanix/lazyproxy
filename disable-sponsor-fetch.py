#!/usr/bin/env python3
"""Reversible sponsor endpoint filter for LazyProxy's nginx topology (3x-ui 3.11).

sudo python3 disable-sponsor-fetch.py --check
sudo python3 disable-sponsor-fetch.py
sudo python3 disable-sponsor-fetch.py --remove

Only edits /etc/nginx/conf.d/single443-web.conf. Does not edit the panel,
database, firewall or README. Regenerating that nginx file removes the filter.
Direct access to the panel port bypasses the filter. Future panel versions
may use different endpoints; this is not a general outbound traffic blocker.
"""
import argparse
import fcntl
import json
import os
from pathlib import Path
import re
import shutil
import signal
import subprocess
import tempfile
import time

CONFIG = Path('/etc/nginx/conf.d/single443-web.conf')
BACKUPS = Path('/var/backups/single443-sponsor-filter')
BEGIN = '    # BEGIN single443-sponsor-filter v1\n'
END = '    # END single443-sponsor-filter v1\n'
EMPTY = '{"success":true,"msg":"","obj":{"contact":"","sponsors":[]}}'


def plan(text, remove=False):
    """Fail closed on unfamiliar layouts; preserve all unmanaged bytes."""
    clean = text
    if text.count(BEGIN) != text.count(END) or text.count(BEGIN) > 1:
        raise ValueError('Повреждены метки фильтра; автоматическое изменение отменено.')
    if BEGIN in text:
        start, stop = text.index(BEGIN), text.index(END) + len(END)
        if stop <= start:
            raise ValueError('Неверный порядок меток фильтра.')
        clean = text[:start] + text[stop:]
    matches = list(re.finditer(
        r'(?m)^    location \^~ (/[A-Za-z0-9_/-]+) \{\n'
        r'(?P<body>[^{}]*?proxy_pass http://127\.0\.0\.1:2053;[^{}]*?)^    \}', clean))
    if len(matches) != 1:
        raise ValueError('Ожидался один стандартный location панели LazyProxy на 127.0.0.1:2053.')
    m = matches[0]
    base = m.group(1)
    if base == '/' or not base.endswith('/') or '//' in base:
        raise ValueError('Неподдерживаемый базовый путь панели.')
    prefix = clean[:m.start()]
    server_start = prefix.rfind('server {')
    server_prefix = prefix[server_start:]
    if not re.search(r'(?m)^    listen 127\.0\.0\.1:7443 ssl(?: http2)?;', server_prefix):
        raise ValueError('Не найден стандартный HTTPS backend nginx на 127.0.0.1:7443.')
    host_match = re.search(r'(?m)^    server_name ([A-Za-z0-9.-]+)(?:\s|;)', server_prefix)
    if not host_match:
        raise ValueError('Не удалось определить домен для локальной проверки TLS.')
    if re.search(r'(?m)^\s*location\s+[^\n]*' + re.escape(base + 'sponsors'), clean):
        raise ValueError('Обнаружены сторонние правила sponsors; автоматическое изменение отменено.')
    block = (BEGIN
             + '    location = ' + base + 'sponsors {\n'
             + '        default_type application/json;\n'
             + '        add_header Cache-Control "no-store" always;\n'
             + '        return 200 \'' + EMPTY + '\';\n'
             + '    }\n'
             + '    location ^~ ' + base + 'sponsors/logo/ {\n'
             + '        return 404;\n'
             + '    }\n' + END)
    if BEGIN in text and text[text.index(BEGIN):text.index(END) + len(END)] != block:
        raise ValueError('Управляемый блок изменён вручную; автоматическая замена отменена.')
    result = clean if remove else clean[:m.start()] + block + clean[m.start():]
    return result, host_match.group(1), base


def run(args):
    result = subprocess.run(args, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                            text=True, timeout=30)
    if result.returncode:
        # Do not print nginx -T, secret panel paths or full curl command lines.
        raise RuntimeError('Ошибка команды: ' + args[0] + ' (код ' + str(result.returncode) + ').')
    return result.stdout


def write_atomic(path, content, metadata):
    fd, name = tempfile.mkstemp(prefix='.sponsor-filter-', dir=path.parent)
    try:
        with os.fdopen(fd, 'w') as stream:
            os.fchmod(stream.fileno(), metadata.st_mode & 0o777)
            os.fchown(stream.fileno(), metadata.st_uid, metadata.st_gid)
            stream.write(content)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(name, path)
    finally:
        if os.path.exists(name):
            os.unlink(name)


def request(host, path):
    result = run(['curl', '--silent', '--show-error', '--noproxy', '*',
                  '--connect-timeout', '3', '--max-time', '8',
                  '--resolve', host + ':7443:127.0.0.1',
                  '--write-out', '\n%{http_code}', 'https://' + host + ':7443' + path])
    body, code = result.rsplit('\n', 1)
    return body, int(code)


def verify(host, base, filtered, baseline):
    _, status = request(host, base)
    if status != baseline:
        raise RuntimeError('После reload изменился HTTP-статус страницы входа.')
    if filtered:
        body, status = request(host, base + 'sponsors')
        if status != 200 or json.loads(body) != json.loads(EMPTY):
            raise RuntimeError('Проверка пустого списка sponsors не пройдена.')
        _, status = request(host, base + 'sponsors/logo/filter-test.png')
        if status != 404:
            raise RuntimeError('Проверка блокировки логотипов не пройдена.')


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument('--check', action='store_true', help='Проверка без изменения конфигурации')
    mode.add_argument('--remove', action='store_true', help='Удалить только управляемый блок и reload nginx')
    args = parser.parse_args()
    if os.geteuid() != 0:
        raise RuntimeError('Запустите через sudo python3.')
    os.umask(0o077)
    for command in ('nginx', 'systemctl', 'curl'):
        if not shutil.which(command):
            raise RuntimeError('Не найдена команда: ' + command)
    with open('/run/lock/single443-sponsor-filter.lock', 'w') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        if CONFIG.is_symlink() or not CONFIG.is_file():
            raise RuntimeError('Конфигурация отсутствует или является символической ссылкой.')
        original = CONFIG.read_text()
        candidate, host, base = plan(original, args.remove)
        run(['nginx', '-t'])
        active_config = run(['nginx', '-T'])
        if '# configuration file ' + str(CONFIG) + ':' not in active_config:
            raise RuntimeError('Файл не включён в конфигурацию nginx.')
        run(['systemctl', 'is-active', '--quiet', 'nginx'])
        _, baseline = request(host, base)
        if baseline not in (200, 301, 302, 303, 307, 308):
            raise RuntimeError('Страница входа недоступна до изменения; операция отменена.')
        if args.check:
            if BEGIN in original:
                verify(host, base, True, baseline)
            print('Проверка OK. Фильтр ' + ('установлен и отвечает.' if BEGIN in original else 'ещё не установлен.'))
            return
        if candidate == original:
            verify(host, base, not args.remove, baseline)
            print('Изменения не нужны; проверка OK.')
            return
        BACKUPS.mkdir(mode=0o700, parents=True, exist_ok=True)
        if BACKUPS.is_symlink() or BACKUPS.stat().st_uid != 0:
            raise RuntimeError('Небезопасный каталог резервных копий.')
        os.chmod(BACKUPS, 0o700)
        backup = BACKUPS / (time.strftime('%Y%m%dT%H%M%S') + '-' + str(os.getpid()) + '.conf')
        with backup.open('x') as stream:
            stream.write(original)
            stream.flush()
            os.fsync(stream.fileno())
        metadata = CONFIG.stat()
        def interrupted(signum, frame):
            raise RuntimeError('Получен сигнал ' + str(signum))
        signals = (signal.SIGINT, signal.SIGTERM, signal.SIGHUP)
        for sig in signals:
            signal.signal(sig, interrupted)
        changed = False
        try:
            if CONFIG.read_text() != original:
                raise RuntimeError('Конфигурация изменена другим процессом.')
            changed = True
            write_atomic(CONFIG, candidate, metadata)
            run(['nginx', '-t'])
            run(['systemctl', 'reload', 'nginx'])
            # Reload is asynchronous: allow workers to adopt the new configuration.
            for attempt in range(5):
                try:
                    verify(host, base, not args.remove, baseline)
                    break
                except (RuntimeError, ValueError):
                    if attempt == 4:
                        raise
                    time.sleep(1)
        except BaseException:
            for sig in signals:
                signal.signal(sig, signal.SIG_IGN)
            if changed:
                write_atomic(CONFIG, original, metadata)
                try:
                    run(['nginx', '-t'])
                    run(['systemctl', 'reload', 'nginx'])
                    print('Исходная конфигурация восстановлена; nginx reload выполнен.')
                except Exception:
                    print('Файл восстановлен, но reload не подтверждён. Проверьте nginx вручную.')
            raise
        finally:
            print('Резервная копия: ' + str(backup))
        print('Фильтр ' + ('удалён.' if args.remove else 'установлен; список пуст, логотипы заблокированы.'))
        print('Страница входа доступна. Панель и Xray не перезапускались.')


if __name__ == '__main__':
    try:
        main()
    except Exception as error:
        print('ОШИБКА: ' + str(error))
        raise SystemExit(1)
