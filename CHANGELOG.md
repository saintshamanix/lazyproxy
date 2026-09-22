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
