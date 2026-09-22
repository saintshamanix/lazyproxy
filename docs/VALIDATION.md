# Проверки кандидата 0.1.1

Дата: 22.09.2026. Хост разработки: Darwin/arm64; Ubuntu VPS не предоставлен.

## Выполнено

* `bash -n` для всех 12 `.sh`: PASS.
* Настоящий ShellCheck 0.11.0, severity warning: PASS. Исключения SC1090/SC1091 — динамические source и системный os-release; SC2034 — конфигурационные переменные, читаемые из другого модуля/Python через environment. Остальные warning/error не подавлялись.
* Ручная shell-проверка: quoting, обработка неизвестных аргументов, checked curl, отсутствие исполнения DB-текста через eval/source, umask, root-only state, flock, ERR/INT/TERM rollback, nginx -t до reload, сохранение секретов на rerun, отсутствие прямых SQL writes.
* 12 Python regression tests: PASS. Нестандартная таблица/порядок колонок, read-only DB, отказ на неоднозначной/неизвестной схеме, реальные произвольные port/path/Host в рендере, TLS SNI/CA verification, неполная TLS-пара, path injection/collision, external-port validation, HTML profile rejection и декодирование subscription base64.
* Настоящий **Xray 26.9.9 darwin/arm64**, revision `52a412d`: `run -test` на пяти generated inbound’ах с временным сертификатом и сгенерированными X25519-ключами: **Configuration OK**. Преобразование fixture удаляет panel-only externalProxy/client settings аналогично upstream config generation.
* Xray выдал предупреждения: REALITY слушает внутренний порт вместо 443; WS/gRPC/Trojan deprecated. Внешний dispatcher всё равно принимает TCP/443; предупреждения об устаревании транспортов не скрываются.

## Не выполнено / не установлено этими проверками

* Настоящий nginx -t на Ubuntu: есть workflow GitHub Actions, но он ещё не запускался. Installer всегда выполняет его на целевой машине до reload.
* Установка оригинального Linux release, API с реальной SQLite-панелью, первоначальный Let's Encrypt, renew, systemd lifecycle и rollback на Ubuntu.
* Возможность получить сертификат именно для двух автодоменов конкретного VPS; состояние DNS зоны зависит от её владельца.
* Авторизованные клиентские соединения, реальная скорость и большие upload, доступность UDP/443 извне, поведение конкретной версии INCY/Clash/Mihomo.
* Совместимость каждого patch-релиза 3.7.x/3.8.x: исследованы исходники v3.7.0 и v3.8.5, функциональный runtime gate выполняется на VPS.

Пустые routing placeholders нельзя описывать как проверенный профиль INCY или готовую routing-политику. `diagnose.sh` явно различает TCP/UDP listeners и полноценный protocol handshake. Секреты и тестовые сертификаты не включены в поставку.

Firewall 0.1.1: Bash syntax и ShellCheck проверены локально. Linux nftables/systemd недоступны на Darwin; реальное применение и namespace-тест здесь не выполнялись. CI добавлен для проверки nft --check, повторного применения и точных наборов портов в отдельном network namespace.
