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
