# MASQUE

[English](MASQUE.md) · [README](../README.ru.md)

На чистом VPS установщик создаёт пустой MASQUE-входящий при установке 3x-ui 3.10.0+. Дополнительный IP не нужен.

```text
IP1:443/TCP → nginx ssl_preread → SNI masque.IP.cdn-one.org → 127.0.0.1:10004 → Xray MASQUE/TLS/h2
```

TLS завершается в Xray. Сертификат `single443-masque` выпускается отдельно и продлевается Certbot; успешное продление перезапускает x-ui. HTTP/3 не включается: UDP/443 занят Hysteria2. На VPS с двумя IP AmneziaWG остаётся на IP2:443/UDP. Передача UDP внутри MASQUE возможна, но транспорт HTTP/2 использует TCP и подвержен задержкам при потере пакетов.

## Добавление после обновления

Для серверов, установленных LazyProxy. Сначала обновите 3x-ui штатной кнопкой до 3.10.0 или выше. TCP/80 должен быть доступен для ACME. Затем выполните:

```bash
sudo bash <<'BASH'
set -Eeuo pipefail
ref=main
repo=saintshamanix/lazyproxy
d=$(mktemp -d)
trap 'rm -rf -- "$d"' EXIT
curl -fLsS --retry 3 "https://api.github.com/repos/$repo/commits/$ref" -o "$d/ref.json"
sha=$(python3 -c 'import json,sys; print(json.load(open(sys.argv[1]))["sha"])' "$d/ref.json")
[[ $sha =~ ^[a-f0-9]{40}$ ]]
curl -fLsS --retry 3 "https://codeload.github.com/$repo/tar.gz/$sha" -o "$d/src.tgz"
mkdir "$d/src"
tar -xzf "$d/src.tgz" -C "$d/src" --strip-components=1
bash "$d/src/add-masque.sh"
BASH
```

Для собственного домена замените последнюю команду на `bash "$d/src/add-masque.sh" --masque-domain masque.example.com`. Требуется отдельная прямая A-запись на IP1, без AAAA/CNAME/CDN. Автодомен зависит от доступности cdn-one.org. Для воспроизводимого запуска замените `ref=main` на SHA LazyProxy.

Скрипт делает резервную копию при остановленной панели, добавляет входящий через API, проверяет конфигурацию Xray и TLS/SNI/h2, затем сохраняет адаптер. Возможен краткий перерыв соединений. При ошибке восстанавливаются панель, nginx и состояние; отдельно выпущенный сертификат сохраняется. Существующие клиенты и привязка IP2 не пересоздаются. Повторный запуск не дублирует входящий; несовместимые ручные изменения останавливают операцию.

## Клиенты и проверка

1. В панели привяжите существующего клиента к MASQUE либо создайте нового. Пароль должен быть задан.
2. Импортируйте **JSON-подписку Xray** в приложение с поддержкой MASQUE. URI и Clash-подписки этот входящий не экспортируют; совместимость Shadowrocket этим не подтверждается.
3. Проверьте реальную загрузку, отправку данных и UDP из внешней сети. Успешная TLS-проверка скрипта не заменяет этот тест.

Лог: `/var/log/single443/install.log`. Резервные копии: `/var/backups/single443/`.

[Upstream 3.10.0](https://github.com/MHSanaei/3x-ui/releases/tag/v3.10.0) · [Проверки](VALIDATION.md)
