# Changelog

## 0.2.4

- Set the upstream subscription title to Casper area during installation and updates; preserve inbound and client names.

### Archived README notes

> **0.2.4:** subscription title is `Casper area`, configured through the upstream API for both fresh installs and updates. Clients receive the upstream `Profile-Title` header. Existing app profiles may need a subscription refresh or reimport.

## 0.2.3

- Automatic supported kernel TCP BBR and persistent default fq, with rollback.
- Automatic fail2ban 3x-ipl jail and separate TCP/UDP nftables actions; no SSH bans from this jail.
- Client IP limits remain unlimited by default; diagnostics document nginx real-IP prerequisite.
- CI exercises jail startup, repeated configuration and synthetic nftables ban/unban.

### Archived README notes

> **0.2.3:** automatic kernel TCP BBR + default fq when supported; unavailable BBR is explicitly skipped. Existing interface qdiscs are preserved. Fail2ban and the `3x-ipl` jail are installed automatically, with nftables actions for TCP/443 and UDP/443,51820. New clients remain unlimited (`limitIp=0`); existing manual limits are preserved. Enforcing IP limits behind nginx still requires real-IP forwarding. Kernel TCP BBR does not configure Hysteria2/AmneziaWG UDP congestion control.

## 0.2.2

- Separate inbound names (country flag + protocol) from client names (User1–User6).
- Migrate managed client names via native API, preserving credentials/subIds/limits; reject collisions and extra attachments.
- Export upstream AmneziaWG configuration to root-only User6-AmneziaWG.conf without rewriting protocol parameters; include it in rollback.
- Exercise real API rename and export in Ubuntu 24.04/26.04 CI.

### Archived README notes

> **0.2.2:** входящие называются «флаг + протокол», клиенты — User1…User6. Обновление переименовывает штатных клиентов через API с сохранением subId, ключей и лимитов. При конфликте имён или ручном изменении идентичности обновление прекращается с rollback.
>
> AmneziaWG: upstream 3.8.5 экспортирует `vpn://` с Base64URL-конфигурацией. Это не доказательство поддержки импорта данного формата в Shadowrocket 2.2.92. Installer сохраняет исходный конфиг без потери параметров в `/etc/single443/User6-AmneziaWG.conf` (root-only); его можно забрать через SFTP для отдельного импорта в совместимый клиент. Публично файл не раздаётся. Поддержка AmneziaWG упоминается в [журнале Shadowrocket](https://apps.apple.com/us/app/shadowrocket/id932747118), но совместимость конкретных AWG 3.1 параметров и формата подписки требует проверки на устройстве.

## 0.2.1

- Разрешена Ubuntu 26.04 после CI на Ubuntu 26.04.1 amd64.
- CI matrix: Ubuntu 24.04 и 26.04, установка полного набора зависимостей.
- На 26.04 прошли 22 теста, Bash/ShellCheck, nginx -t, nftables namespace, реальный API/UDP/экспорт AmneziaWG upstream 3.8.5.
- ACME на реальном домене, полная установка через systemd и внешние VPN handshakes остаются VPS acceptance tests; arm64 26.04 отдельно не проверена.

### Archived README notes

> **0.2.1:** Ubuntu 26.04 разрешена. На GitHub Actions Ubuntu 26.04.1 amd64 прошли установка зависимостей, Bash/ShellCheck, 22 unit tests, nginx -t, nftables и реальный API-тест AmneziaWG 3.8.5. Полная установка с ACME и клиентскими соединениями требует проверки на VPS.

## 0.2.0

- AmneziaWG как шестой управляемый inbound через API upstream 3x-ui 3.8.5.
- Разрешён UDP/51820 по запросу владельца; Hysteria2 остаётся на UDP/443.
- Страна публичного IP через HTTPS geolocation; флаг и User1…User6 в именах входящих.
- Стабильные inbound ID для идемпотентного переименования; сохранение credentials/subId.
- Проверки экспорта vpn://, UDP listener и повторного создания AWG.
- Адаптер шести входящих ограничен проверенной версией 3.8.5; другие версии отклоняются до изменения сервисов.

### Archived README notes

> **Версия 0.2.0:** шесть независимых входящих, включая AmneziaWG на UDP/51820.
> Адаптер шести входящих проверен по исходникам upstream **3x-ui 3.8.5**; используйте `--version 3.8.5`.
> Прежнее ограничение только портом 443 для VPN расширено с разрешения владельца: UDP/51820 для AmneziaWG.

| Входящий (флаг зависит от страны IP VPS) | Протокол | Внешний порт |
|---|---|---|
| 🌐 REALITY | VLESS TCP REALITY | TCP/443 |
| 🌐 WS | VLESS WebSocket TLS | TCP/443 |
| 🌐 XHTTP | VLESS XHTTP TLS, stream-up | TCP/443 |
| 🌐 gRPC | Trojan gRPC TLS | TCP/443 |
| 🌐 Hysteria2 | Hysteria2 | UDP/443 |
| 🌐 AmneziaWG | AmneziaWG | UDP/51820 |

Страна определяется по публичному IPv4 через HTTPS API [IPWhois](https://ipwhois.io/documentation),
поле `country_code`. Это геолокация IP, не подтверждение физического размещения сервера.
Код страны сохраняется; при сбое используется 🌐 и запрос повторяется при следующем запуске.
Переименовываются входящие и названия внешних ссылок; внутренние email клиентов сохраняются для учёта трафика.
Идентификаторы входящих фиксируются в state, повторный запуск не зависит от их отображаемого имени.

AmneziaWG создаётся через штатный API 3x-ui 3.8.5: серверные/клиентские ключи и параметры обфускации генерирует upstream.
Используется встроенный в панель userspace AmneziaWG, без отдельного сервиса, DKMS и изменения FORWARD policy.
Клиент имеет отдельный subId. Стандартная подписка экспортирует upstream `vpn://` с конфигурацией AmneziaWG;
её импортируйте в совместимый AmneziaWG-клиент. Для этого входящего Mihomo URL не выводится.
Диагностика проверяет UDP/51820, формат экспорта и endpoint; успешный handshake с внешнего клиента этим не доказан.

Для существующей установки 3.8.5 применяется `install.sh --update-only`:
backup → обновление управляемого firewall → переименование пяти входящих → добавление шестого → диагностика.
Существующие UUID, пароли и индивидуальные подписки сохраняются. При ошибке применяется rollback.
Если у провайдера VPS есть отдельный firewall/security group, разрешите в нём UDP/51820.

## 0.1.3

- Исправлен ложный rollback: INCY routing/autorouting URI больше не считается proxy-подключением при диагностике подписки.
- Проверка по-прежнему отклоняет лишние подключения, неизвестные строки и подписку без подключения.
- Регрессионные тесты всех пяти протоколов с INCY в raw/base64.
- Повторный daemon-reload после восстановления состояния firewall unit при rollback.

## 0.1.2

- Пять независимых subId и подписок; API-миграция старой общей подписки с backup/rollback.
- `install.sh --update-only`: обновление без переустановки upstream.
- INCY Shamanix RU Direct из пользовательского JSON без изменений.
- Decoy: локальный JavaScript, тема и фильтрация заметок.
- Диагностика каждой независимой подписки: ровно одна ссылка ожидаемого протокола.

### Archived README notes

Пять клиентов имеют пять разных `subId`, каждый связан с одним входящим.
`access.txt` содержит отдельные стандартные и Mihomo URL для каждого клиента.
Диагностика требует ровно одну ссылку нужного протокола в каждой стандартной подписке.

Для существующей установки запустите raw-команду выше, заменив `--version latest` на `--update-only`.
Этот режим не обновляет upstream, сертификаты и firewall. Перед изменением сохраняет резервную копию,
разделяет старую общую подписку через API, сохраняет UUID/пароли/остальные поля клиентов,
обновляет decoy и routing, проверяет nginx и запускает диагностику. При ошибке восстанавливает копию.
Миграция допускает только исходные пять клиентов установщика: при изменённых реквизитах,
подписках или добавленных клиентах прекращает работу для предотвращения потери изменений.
**Старая общая подписка больше не выдаёт эти пять подключений; импортируйте новые URL.**
Повторный запуск сохраняет новые subId. Прямые ссылки подключения сохраняют прежние реквизиты.

Decoy содержит локальный `site.js`: переключение светлой/тёмной темы, фильтр заметок и текущий месяц.
Внешних библиотек и сетевых запросов из JS нет; без JavaScript все заметки остаются видны.

Если API панели поддерживает `subIncyEnableRouting/subIncyRoutingRules`, установщик включает INCY routing и задаёт HTTPS URL файла; иначе сообщает об отсутствии полей и оставляет статический endpoint.

## 0.1.1 — 2026-09-22

* Автоматический persistent nftables firewall: входящие 22/TCP, 80/TCP, 443/TCP+UDP, IPv4/IPv6.
* SSH/конфликтующие firewall preflight, atomic apply, backup/rollback и диагностика policy drift.
* Добавлен Linux network-namespace тест в CI; локально Linux runtime не выполнялся.

### Archived README notes

Правила находятся в `templates/firewall.nft`, устанавливаются до запуска backend’ов и получения сертификата. Таблица `inet single443` заменяется атомарно после `nft --check`; `single443-firewall.service` восстанавливает её при загрузке. Повторный запуск не добавляет дубликаты. Исходящие соединения, loopback, established/related и ICMP/ICMPv6 разрешены; это необходимо для ответного трафика, PMTU и IPv6 neighbour discovery. Существующие соединения не обрываются принудительно. Новые входящие TCP/UDP допускаются только на перечисленные порты. Дополнительных исключений для входящего DHCP нет: этот профиль рассчитан на VPS со статической адресацией.

Перед применением требуется слушатель TCP/22. Если переменная SSH_CONNECTION доступна и показывает другой порт, установка прекращается. Installer не меняет sshd. Доступность SSH извне всё равно зависит от провайдера и его security groups.

Активные UFW/firewalld, сторонние nft base chains и legacy iptables rules приводят к остановке до изменения firewall: смешанные политики могут заблокировать даже разрешённые порты. Это профиль для чистого VPS и повторных запусков собственного installer’а, а не автоматическая миграция произвольного чужого firewall.

Существующие правила собственной таблицы и её unit/config сохраняются в backup и восстанавливаются при ошибке установки. `diagnose.sh` сравнивает полную live-таблицу с сохранённой установленной политикой и проверяет autostart. Остановка unit специально не снимает фильтрацию.

Проверка после установки: `sudo nft list table inet single443`.
Основание семантики nft: https://netfilter.org/projects/nftables/manpage.html .

## 0.1.0 — 2026-09-22

* Первый кандидат для тестовой установки на Ubuntu 22.04/24.04 amd64/arm64.
* Upstream 3x-ui latest/pin, SHA-256, CLI bootstrap и session API с CSRF.
* Два автодомена, ACME webroot, единый внешний TCP/443 и UDP/443.
* Пять управляемых inbound’ов, XHTTP stream-up, externalProxy:443.
* API/SQLite read-only discovery подписок, Host/SNI и CA verification.
* Случайные сохранённые секреты, backup/rollback, nginx validation, диагностика.
* Нейтральный сайт, статические routing placeholders, Mihomo alias.
* Bash/Python regression checks, Xray 26.9.9 config validation, Ubuntu nginx CI definition.
* Runtime установка на VPS и end-to-end клиентские соединения пока не проверены.

## Archived compatibility notes — 2026-09-22

Historical README text; later version entries above supersede these compatibility limits.

На 22.09.2026 GitHub Releases API вернул **v3.8.5** как latest. Прочитаны исходники тегов **v3.7.0 и v3.8.5**, а также текущий main. Адаптер ограничен семействами `3.7.x`/`3.8.x`, но не заявляет runtime-проверку каждого patch-релиза. Новое семейство завершает установку до изменений панели; нужен новый аудит API.

Используются:

* CLI `migrate`, `setting -port -listenIP -webBasePath -username -password` для первичной настройки.
* Session API: публичный `csrf-token`, `login`, обновление `panel/csrf-token` после входа.
* `/panel/api/setting/all`, `/setting/update` — чтение эффективных настроек и первичная настройка подписок.
* `/panel/api/inbounds/list`, `/inbounds/add` — inbound’ы. Существующие управляемые inbound’ы не пересоздаются и клиенты не затираются.
* `/panel/api/server/getNewX25519Cert`, `/server/getConfigJson` — ключи и построенный панелью Xray config. Перед явным restart он проверяется бинарником установленного Xray.

Xray 26.9.9 принимает WS, gRPC и Trojan, но предупреждает об их устаревании. Они включены по запросу. Источники и точные границы совместимости: [docs/UPSTREAM.md](docs/UPSTREAM.md).

Загрузка релиза проверяется по SHA-256 из GitHub Releases API, либо по опубликованному `.sha256`. У v3.7.0 отдельного checksum asset нет, но API публикует digest. При отсутствии обоих installer прекращает установку. Digest из того же GitHub-источника — контроль целостности загрузки, не независимая подпись автора.
