# LazyProxy

Автоматическая установка **upstream 3x-ui за nginx reverse proxy** на Ubuntu VPS.
Без форка панели: LazyProxy устанавливает и настраивает компоненты, а управление
клиентами остаётся в оригинальной 3x-ui.

## Архитектура

```text
Интернет
├── TCP/80  → nginx: ACME HTTP-01 и перенаправление на HTTPS
├── TCP/443 → nginx stream: ssl_preread / SNI dispatcher
│   ├── REALITY SNI → Xray 127.0.0.1:8443
│   └── WEB SNI     → nginx HTTPS 127.0.0.1:7443
│       ├── /                 → нейтральный сайт с JavaScript
│       ├── секретный path    → панель 127.0.0.1:2053
│       ├── subscription path → обнаруженный backend подписок
│       ├── WS path           → Xray 127.0.0.1:10001
│       ├── XHTTP path        → Xray 127.0.0.1:10002 (HTTP/2)
│       └── gRPC service      → Xray 127.0.0.1:10003 (HTTP/2)
├── UDP/443   → Hysteria2
└── UDP/51820 → AmneziaWG
```

**TLS для сайта, панели, подписок, WS, XHTTP и gRPC завершается на nginx.**
На участке nginx → Xray для WS/XHTTP/gRPC используется loopback без TLS.
Поэтому «Безопасность: Нет» у этих входящих в панели соответствует архитектуре;
клиент подключается с TLS на внешний порт 443.

REALITY проходит через SNI dispatcher без завершения TLS в nginx stream.
Hysteria2 использует UDP/443 напрямую. AmneziaWG требует отдельного UDP/51820:
это исключение из схемы общего порта 443.

XHTTP передаётся через `grpc_pass` по HTTP/2. Название директивы не меняет
протокол входящего: это по-прежнему VLESS XHTTP. Клиенту нужен ALPN `h2`;
HTTP/3 nginx здесь не обслуживает. Режим по умолчанию — `stream-up`.

## Возможности

- Автоопределение публичного IPv4 и домены `IP.cdn-one.org` / `IP-с-дефисами.cdn-one.org`.
- Let's Encrypt через Certbot, автоматическое продление и deploy hook.
- VLESS REALITY, VLESS WS, VLESS XHTTP, Trojan gRPC, Hysteria2 и AmneziaWG.
- Имена входящих: флаг страны и протокол. Новые клиенты: `User1`–`User6`.
- Независимые подписки; название профиля — **Casper area**.
- Reverse proxy подписок с discovery актуальных настроек через API и read-only SQLite.
- INCY routing, Clash/Mihomo endpoints и статические routing-файлы.
- nftables, совместимость со штатной SSH-защитой Fail2ban, TCP BBR при поддержке ядром.
- По умолчанию клиенты без IP-лимита (`limitIp=0`); пользовательские ограничения сохраняются.
- Резервные копии, проверки конфигурации, откат при ошибке и обслуживание журналов.

## Требования и проверенные версии

Ubuntu Server 22.04, 24.04 или 26.04, systemd, root, amd64 или arm64.
Для bootstrap необходимы curl, Python 3 и CA certificates.

Адаптер шести протоколов привязан к **3x-ui 3.8.5**. Режим `latest` существует,
но неподдерживаемая версия будет отклонена; для воспроизводимой установки используйте pin ниже.

Оба автодомена должны разрешаться в IP VPS. Доступность DNS-сервиса `cdn-one.org`
зависит от его владельца. Внешний firewall провайдера должен пропускать:

| Транспорт | Порты | Назначение |
|---|---|---|
| TCP | 22, 80, 443 | SSH, ACME/HTTP, HTTPS и прокси |
| UDP | 443, 51820 | Hysteria2, AmneziaWG |

Installer управляет локальным firewall. Неизвестные активные политики приводят
к остановке установки; они не очищаются автоматически. Проверенная SSH-only
цепочка штатного Fail2ban `sshd` допускается и сохраняется.

## Чистая установка

На подготовленном Ubuntu VPS:

```bash
sudo bash -c 'set -Eeuo pipefail; export INSTALLER_REPO=saintshamanix/lazyproxy INSTALLER_REF=main; f=$(mktemp); trap '\''rm -f "$f"'\'' EXIT; curl -fLsS --retry 3 "https://raw.githubusercontent.com/$INSTALLER_REPO/$INSTALLER_REF/install.sh" -o "$f"; bash "$f" --version 3.8.5'
```

Для фиксации версии самого LazyProxy замените `INSTALLER_REF=main` на SHA коммита.
Варианты конфигурации приведены в [config.example.env](config.example.env).

После успешного завершения:

```bash
sudo cat /etc/single443/access.txt
```

Файл содержит секретные данные доступа. Не публикуйте его.

## Обновление существующей установки

Обновление обвязки без обновления версии панели:

```bash
sudo bash -c 'set -Eeuo pipefail; export INSTALLER_REPO=saintshamanix/lazyproxy INSTALLER_REF=main; f=$(mktemp); trap '\''rm -f "$f"'\'' EXIT; curl -fLsS --retry 3 "https://raw.githubusercontent.com/$INSTALLER_REPO/$INSTALLER_REF/install.sh" -o "$f"; bash "$f" --update-only'
```

Ручные имена клиентов сохраняются. Только старые installer-имена
`single443-*` мигрируют в `UserN`. Клиент определяется по сохранённому ID
входящего и `subId`; отсутствие или неоднозначность этой записи останавливает
обновление. Изменённые paths, ключи и топология не перезаписываются вслепую.
Если вручную меняли XHTTP mode, перед общим обновлением верните `stream-up`.

При ошибке возможен откат, поэтому сам запуск команды ещё не означает успех.
Ожидайте итоговое сообщение `Updated.`. После обновления обновите подписку в клиенте.

## Диагностика

```bash
sudo bash /opt/single443/diagnose.sh
sudo nginx -t
sudo nginx -T 2>/dev/null | grep -E '(grpc_pass|proxy_pass).*10002'
```

Для XHTTP ожидается `grpc_pass grpc://127.0.0.1:10002;`.
Лог установки: `/var/log/single443/install.log`.
Резервные копии: `/var/backups/single443/`.

CI на Ubuntu 24.04/26.04 amd64 проверяет Bash, ShellCheck, Python, nginx,
изолированный nftables, реальный API 3x-ui 3.8.5 и передачу по 2 МиБ в обе
стороны через VLESS XHTTP + TLS + SNI dispatcher для трёх режимов.
Эти проверки не заменяют внешние тесты конкретного VPS и приложений.
Ubuntu 22.04 и arm64 не покрыты этой CI-матрицей.

## Клиенты и ограничения

- WS и gRPC сохранены для совместимости; предупреждения Xray об устаревании не скрываются.
- Проверка UDP listener не доказывает доступность UDP извне или успешный VPN handshake.
- Совместимость экспорта AmneziaWG `vpn://` с Shadowrocket не гарантируется.
  Отдельный конфиг сохраняется в `/etc/single443/User6-AmneziaWG.conf`
  (имя файла остаётся постоянным даже после переименования клиента).
- Ненулевой IP Limit за nginx требует корректной передачи реального IP;
  одной установки Fail2ban для этого недостаточно.
- Статические placeholders Clash/Mihomo не являются готовой пользовательской политикой маршрутизации.

## Автоматическая очистка

Persistent systemd timer проверяет срок каждый час и запускает очистку через
72 часа после последнего успешного выполнения. Первый запуск — через три дня
после установки. Пропущенная очистка выполняется после включения сервера.

Очищаются активные nginx `access.log` и `error.log` (архивы сохраняются);
journal ротируется и очищается с `--vacuum-time=1d --vacuum-size=10M`;
выполняется `apt-get clean`. Активные journal-файлы могут превышать 10 МиБ:
это не непрерывный лимит диска.

Удаление пакетов выключено по умолчанию. Для `apt-get autoremove --purge -y`
задайте `AUTO_REMOVE=yes` в `/etc/single443/maintenance.env`.
Настройка сохраняется при обновлении. Неудачная очистка повторяется при
следующей часовой проверке; уже выполненную очистку откатить нельзя.

```bash
systemctl list-timers single443-maintenance.timer
journalctl -u single443-maintenance.service
sudo /usr/local/libexec/single443-maintenance --force
```

## Upstream и лицензия

- [MHSanaei/3x-ui](https://github.com/MHSanaei/3x-ui)
- [XTLS/Xray-core](https://github.com/XTLS/Xray-core)
- [Пример XHTTP reverse proxy от XTLS](https://github.com/XTLS/Xray-examples/blob/main/VLESS-XHTTP3-Nginx/nginx.conf)
- [nginx grpc module](https://nginx.org/en/docs/http/ngx_http_grpc_module.html)

[CHANGELOG](CHANGELOG.md) · [Проверки](docs/VALIDATION.md) · [Upstream](docs/UPSTREAM.md)

Лицензия LazyProxy пока не выбрана: [LICENSE](LICENSE).
Компоненты upstream сохраняют собственные лицензии.
