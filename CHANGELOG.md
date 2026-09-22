## 0.2.2

- Separate inbound names (country flag + protocol) from client names (User1–User6).
- Migrate managed client names via native API, preserving credentials/subIds/limits; reject collisions and extra attachments.
- Export upstream AmneziaWG configuration to root-only User6-AmneziaWG.conf without rewriting protocol parameters; include it in rollback.
- Exercise real API rename and export in Ubuntu 24.04/26.04 CI.

## 0.2.1

- Разрешена Ubuntu 26.04 после CI на Ubuntu 26.04.1 amd64.
- CI matrix: Ubuntu 24.04 и 26.04, установка полного набора зависимостей.
- На 26.04 прошли 22 теста, Bash/ShellCheck, nginx -t, nftables namespace, реальный API/UDP/экспорт AmneziaWG upstream 3.8.5.
- ACME на реальном домене, полная установка через systemd и внешние VPN handshakes остаются VPS acceptance tests; arm64 26.04 отдельно не проверена.

## 0.2.0

- AmneziaWG как шестой управляемый inbound через API upstream 3x-ui 3.8.5.
- Разрешён UDP/51820 по запросу владельца; Hysteria2 остаётся на UDP/443.
- Страна публичного IP через HTTPS geolocation; флаг и User1…User6 в именах входящих.
- Стабильные inbound ID для идемпотентного переименования; сохранение credentials/subId.
- Проверки экспорта vpn://, UDP listener и повторного создания AWG.
- Адаптер шести входящих ограничен проверенной версией 3.8.5; другие версии отклоняются до изменения сервисов.

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

# Changelog

## 0.1.1 — 2026-09-22

* Автоматический persistent nftables firewall: входящие 22/TCP, 80/TCP, 443/TCP+UDP, IPv4/IPv6.
* SSH/конфликтующие firewall preflight, atomic apply, backup/rollback и диагностика policy drift.
* Добавлен Linux network-namespace тест в CI; локально Linux runtime не выполнялся.

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
