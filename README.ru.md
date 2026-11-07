# LazyProxy

[English](README.md) · **Русский**

LazyProxy устанавливает 3x-ui на чистый Ubuntu VPS, настраивает nginx, сертификаты TLS, подписки и сетевой экран. После установки клиентами и подключениями можно управлять в панели.

Установщик создаёт подключения VLESS (REALITY, WS, XHTTP), Trojan (gRPC и WS), Hysteria2 и AmneziaWG. Начиная с 3x-ui 3.10.0 он также добавляет MASQUE. По умолчанию у клиента `User1` есть доступ только к REALITY. Чтобы использовать другое подключение, привяжите к нему клиента в панели.

## Установка

Нужны Ubuntu 22.04, 24.04 или 26.04 (amd64 или arm64), systemd и публичный IPv4. UFW должен быть выключен: правилами nftables управляет LazyProxy. В сетевом экране провайдера откройте TCP 22, 80, 443 и UDP 443, 51820 на основном адресе.

Выполните на VPS, чтобы установить последнюю стабильную версию 3x-ui:

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
bash "$f" --version latest
BASH
```

Адрес панели, логин и пароль: `sudo cat /etc/single443/access.txt`.

## Если у VPS два IPv4

Установите LazyProxy на основной адрес, затем [привяжите второй IPv4](docs/OPERATIONS.ru.md#second-ipv4). Меняются только UDP-подключения:

| | Один IPv4 | После привязки второго IPv4 |
|---|---|---|
| Hysteria2 | IP1:443 | IP1:443 |
| AmneziaWG | IP1:51820 | IP2:443 |

Разрешите UDP/443 на обоих адресах. После переноса AmneziaWG порт UDP/51820 больше не нужен. Trojan + WS по-прежнему использует TCP/443 через nginx.

3x-ui обновляется из панели. Для настройки доменов, обновления LazyProxy и диагностики см. [руководство](docs/OPERATIONS.ru.md).

[MASQUE](docs/MASQUE.ru.md) · [Проверки](docs/VALIDATION.md) · [Изменения](CHANGELOG.md) · [Лицензия MIT](LICENSE) · [Сторонние компоненты](THIRD_PARTY.md)
