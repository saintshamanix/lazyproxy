# LazyProxy

[English](README.md) · **Русский**

Установка **3x-ui за обратным прокси nginx** на Ubuntu VPS.
LazyProxy настраивает TLS, входящие, подписки и nftables; управление клиентами остаётся в оригинальной панели.

**Протоколы:** VLESS REALITY, VLESS WS, VLESS XHTTP, Trojan gRPC, Hysteria2 и AmneziaWG.
Чистая установка создаёт **одного клиента — User1 на REALITY**. Остальных добавляйте или привязывайте в панели.

## Архитектура

```text
TCP/80  → nginx: проверка ACME и перенаправление на HTTPS
TCP/443 → SNI-диспетчер nginx
          ├─ REALITY → Xray
          └─ HTTPS  → завершение TLS на nginx
                      ├─ сайт, панель и подписки
                      └─ WS, XHTTP и gRPC → Xray через loopback
```

| Схема UDP | Hysteria2 | AmneziaWG |
|---|---|---|
| Один публичный IP — по умолчанию | IP1:443 | IP1:51820 |
| Два публичных IPv4 — опционально | IP1:443 | IP2:443 |

При втором IP схема TCP сохраняется; UDP/51820 закрывается, оба UDP-входящих работают только по IPv4.
[Настройка и ограничения](docs/OPERATIONS.ru.md).

TLS для веб-сервисов и WS/XHTTP/gRPC завершается на nginx; `security: none` у внутренних входящих соответствует этой схеме.
REALITY проходит через nginx без завершения TLS. XHTTP использует HTTP/2 (`grpc_pass`, ALPN `h2`), режим по умолчанию — `stream-up`.

## Требования

- Ubuntu 22.04 / 24.04 / 26.04, systemd, root, amd64 или arm64.
- Публичный IPv4; firewall провайдера пропускает TCP **22, 80, 443** и UDP **443, 51820**.
- UFW выключен: LazyProxy управляет nftables. Неизвестные политики останавливают установку; проверенные штатные SSH-правила Fail2ban сохраняются.
- Автодомены должны разрешаться в IP VPS; их доступность зависит от `cdn-one.org`.

Поддерживаемые версии панели: **3.9.0** (по умолчанию) и **3.8.5**.
CI покрывает Ubuntu 24.04/26.04 amd64. [Результаты проверок](docs/VALIDATION.md).

## Установка

Выполните на чистом VPS:

```bash
sudo bash <<'BASH'
set -Eeuo pipefail
export INSTALLER_REPO=saintshamanix/lazyproxy
export INSTALLER_REF=main
apt-get update -q
DEBIAN_FRONTEND=noninteractive apt-get install -y curl python3 ca-certificates
f=$(mktemp)
trap 'rm -f "$f"' EXIT
curl -fLsS --retry 3 \
  "https://raw.githubusercontent.com/$INSTALLER_REPO/$INSTALLER_REF/install.sh" -o "$f"
bash "$f" --version 3.9.0
BASH
```

Для фиксации версии LazyProxy замените `INSTALLER_REF=main` на SHA коммита.
После установки получите адрес панели и учётные данные:

```bash
sudo cat /etc/single443/access.txt
```

Не публикуйте этот файл. Сертификаты TLS продлеваются автоматически.

## Варианты установки

Добавьте параметры в строку `bash "$f" --version 3.9.0` выше.

| Вариант | Настройка |
|---|---|
| Автодомены | По умолчанию, без дополнительных параметров |
| Собственные домены | `--domain vpn.example.com --reality-domain reality.example.com`; две прямые A-записи, без CDN-прокси и AAAA/CNAME |
| Публичный IP + TLS | `--ip-tls`; только чистая установка, автодомен REALITY всё ещё необходим |
| Второй публичный IPv4 | Обычная установка, затем [перенос AmneziaWG на IP2:443](docs/OPERATIONS.ru.md#second-ipv4) |

Повторный запуск установщика не меняет сохранённые домены и режим TLS.
[Подробности настройки](docs/OPERATIONS.ru.md) · [Файл конфигурации](config.example.env)

## Обновление

**3x-ui:** используйте штатное обновление в панели.
[Инструкция для 3.9.0](docs/UPGRADE-3.9.0.ru.md) учитывает обе схемы IP; повторная установка и привязка IP2 не нужны.

**Компоненты LazyProxy:** отдельная необязательная операция `--update-only`.
Она не меняет версию панели. [Порядок обновления](docs/OPERATIONS.ru.md#lazyproxy-update).

## Диагностика

```bash
sudo bash /opt/single443/diagnose.sh
```

Журнал: `/var/log/single443/install.log` · Резервные копии: `/var/backups/single443/`.
После изменений проверяйте подписки и реальный трафик клиентов; открытый порт сам по себе не подтверждает соединение.

## Справка

[Эксплуатация](docs/OPERATIONS.ru.md) · [Проверки](docs/VALIDATION.md) · [Изменения](CHANGELOG.md) · [Upstream](docs/UPSTREAM.md)

LazyProxy — [MIT](LICENSE). Скачиваемые компоненты сохраняют свои лицензии: [сторонние компоненты](THIRD_PARTY.md).
