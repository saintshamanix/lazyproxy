#!/usr/bin/env python3
"""Install the sponsor-filter preservation patch into an existing LazyProxy engine.
Does not regenerate nginx, reload services or change documentation.
"""
import ast
import fcntl
import os
from pathlib import Path
import tempfile
import time

HELPER = '''def preserve_sponsor_filter(text, panel_path, current):
    """Carry forward only the exact opt-in filter; regenerate its panel path."""
    begin = '    # BEGIN single443-sponsor-filter v1\\n'
    end = '    # END single443-sponsor-filter v1\\n'
    old = current.read_text() if current.exists() else ''
    if begin not in old and end not in old:
        return text
    require(old.count(begin) == old.count(end) == 1, 'Invalid sponsor filter markers')
    start, stop = old.index(begin), old.index(end) + len(end)
    require(stop > start, 'Invalid sponsor filter marker order')
    block = old[start:stop]
    match = re.search(r'location = (/[A-Za-z0-9_/-]+)sponsors \\{', block)
    require(match is not None, 'Invalid sponsor filter path')
    old_path = match.group(1)
    for path in (old_path, panel_path):
        require(re.fullmatch(r'/[A-Za-z0-9_/-]+/', path) is not None and '//' not in path,
                'Unsupported sponsor filter panel path')
    def rules(path):
        return (begin
                + '    location = ' + path + 'sponsors {\\n'
                + '        default_type application/json;\\n'
                + '        add_header Cache-Control "no-store" always;\\n'
                + '        return 200 \\'{"success":true,"msg":"","obj":{"contact":"","sponsors":[]}}\\';\\n'
                + '    }\\n'
                + '    location ^~ ' + path + 'sponsors/logo/ {\\n'
                + '        return 404;\\n'
                + '    }\\n' + end)
    require(block == rules(old_path), 'Sponsor filter was edited manually; refusing to overwrite')
    location = '    location ^~ ' + panel_path + ' {\\n'
    require(text.count(location) == 1, 'Cannot locate panel for sponsor filter')
    require(begin not in text and end not in text, 'Unexpected filter in nginx template')
    return text.replace(location, rules(panel_path) + location, 1)


'''

OLD = """        Path(target).write_text(text)
        Path(target).chmod(0o644)
"""
NEW = """        if source == 'nginx-web.conf.tpl':
            text = preserve_sponsor_filter(text, s['panel_path'], Path(target))
        rendered.append((target, text))
    for target, text in rendered:
        Path(target).write_text(text)
        Path(target).chmod(0o644)
"""
LOOP = "    for source, target in [('nginx-stream.conf.tpl','/etc/nginx/single443-stream.conf'),"


def patch_engine(source):
    if 'def preserve_sponsor_filter(' in source:
        if source.count(HELPER) != 1 or source.count(NEW) != 1 or '    rendered = []\n' + LOOP not in source:
            raise RuntimeError('Обнаружена другая версия интеграции; файл не изменён.')
        return source
    for anchor in ('def render(templates):\n', OLD, LOOP):
        if source.count(anchor) != 1:
            raise RuntimeError('Неизвестная версия генератора; файл не изменён.')
    result = source.replace('def render(templates):\n', HELPER + 'def render(templates):\n', 1)
    result = result.replace(LOOP, '    rendered = []\n' + LOOP, 1).replace(OLD, NEW, 1)
    ast.parse(result)
    return result


def main():
    if os.geteuid() != 0:
        raise RuntimeError('Запустите через sudo python3.')
    os.umask(0o077)
    engine = Path('/opt/single443/lib/engine.py')
    with open('/run/lock/single443.lock', 'w') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        if engine.is_symlink() or not engine.is_file():
            raise RuntimeError('Не найден стандартный /opt/single443/lib/engine.py.')
        original = engine.read_text()
        updated = patch_engine(original)
        if original == updated:
            print('Сохранение фильтра уже встроено в генератор.')
            return
        backups = Path('/var/backups/single443-sponsor-filter')
        if backups.is_symlink():
            raise RuntimeError('Каталог резервных копий является ссылкой.')
        backups.mkdir(parents=True, exist_ok=True, mode=0o700)
        if backups.stat().st_uid != 0:
            raise RuntimeError('Неверный владелец каталога резервных копий.')
        backups.chmod(0o700)
        backup = backups / ('engine-' + time.strftime('%Y%m%dT%H%M%S') + '-' + str(os.getpid()) + '.py')
        with backup.open('x') as out:
            out.write(original)
            out.flush()
            os.fsync(out.fileno())
        metadata = engine.stat()
        fd, temp = tempfile.mkstemp(prefix='.engine-', dir=engine.parent)
        try:
            with os.fdopen(fd, 'w') as out:
                os.fchown(out.fileno(), metadata.st_uid, metadata.st_gid)
                os.fchmod(out.fileno(), metadata.st_mode & 0o777)
                out.write(updated)
                out.flush()
                os.fsync(out.fileno())
            if engine.read_text() != original:
                raise RuntimeError('Генератор изменился во время установки.')
            os.replace(temp, engine)
        finally:
            if os.path.exists(temp):
                os.unlink(temp)
        print('Сохранение фильтра встроено. nginx и Xray не перезапускались.')
        print('Резервная копия: ' + str(backup))


if __name__ == '__main__':
    try:
        main()
    except Exception as error:
        print('ОШИБКА: ' + str(error))
        raise SystemExit(1)
