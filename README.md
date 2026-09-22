# single443 — собственная обвязка upstream 3x-ui

Автоматический installer для **чистого Ubuntu Server 22.04/24.04, amd64 или arm64**, с systemd и публичным IPv4. Панель не форкается: используется оригинальный бинарный GitHub Release MHSanaei/3x-ui. Настройки панели и inbound’ы создаются через upstream CLI/API, без SQL-записей installer’ом.

**Статус: кандидат для тестовой установки на VPS.** На машине разработки прошли Bash syntax, Python regression tests и проверка generated inbound config настоящим Xray 26.9.9 для macOS. Полная установка Ubuntu, выпуск ACME-сертификата и клиентские соединения здесь не выполнялись. См. [docs/VALIDATION.md](docs/VALIDATION.md).

## Быстрый запуск

Репозиторий: https://github.com/saintshamanix/lazyproxy . Выполните на чистом VPS:

```bash
sudo bash -c 'set -Eeuo pipefail; export INSTALLER_REPO="saintshamanix/lazyproxy" INSTALLER_REF="main"; command -v curl >/dev/null && command -v python3 >/dev/null || { apt-get update -q; DEBIAN_FRONTEND=noninteractive apt-get install -y curl python3 ca-certificates; }; f=$(mktemp); trap '\''rm -f "$f"'\'' EXIT; curl -fLsS --retry 3 "https://raw.githubusercontent.com/$INSTALLER_REPO/$INSTALLER_REF/install.sh" -o "$f"; bash "$f" --version latest'
```

Bootstrap скачивает весь репозиторий, разрешая ref в конкретный commit SHA через GitHub API. `install.sh` в одиночку недостаточен: ему нужны `lib/` и `templates/`. GitHub raw/архив/API должны быть доступны без токена; приватные репозитории этим bootstrap не поддерживаются. Для pin замените `--version latest` на `--version 3.8.5`. Разрешён обычный ref без `/`; для веток с `/` используйте commit SHA.

Если каталог уже скопирован на VPS:

```bash
sudo bash install.sh --version 3.8.5
# Необязательный доверенный root-owned конфиг:
sudo bash install.sh --config /root/config.env
```

`config.env` — исполняемый Bash-файл; значения из него имеют приоритет над `--version`. По умолчанию вопросов installer не задаёт. Email ACME необязателен. Случайные значения генерируются автоматически.

После завершения:

```bash
sudo cat /etc/single443/access.txt
sudo bash /opt/single443/diagnose.sh
```

## Архитектура

| Внешний вход | Диспетчеризация | Backend |
|---|---|---|
| TCP/443 | nginx stream, SNI `IP-с-дефисами.cdn-one.org` | VLESS TCP REALITY, `127.0.0.1:8443` |
| TCP/443 | nginx stream, остальные SNI | nginx TLS/HTTP2, `127.0.0.1:7443` |
| HTTPS, случайный panel path | nginx reverse proxy | 3x-ui, `127.0.0.1:2053` |
| HTTPS, случайный WS path | TLS termination в nginx | VLESS WS, `127.0.0.1:10001` |
| HTTPS, случайный XHTTP path | TLS termination, buffering off | VLESS XHTTP **stream-up**, `127.0.0.1:10002` |
| HTTPS, случайный gRPC service | HTTP2 → grpc_pass | Trojan gRPC, `127.0.0.1:10003` |
| UDP/443 | непосредственно Xray панели | Hysteria2, TLS, `0.0.0.0:443` |
| HTTPS, актуальные subscription paths | reverse proxy с Host/SNI | обнаруженный порт и схема subscription service |
| HTTPS `/` | статический нейтральный сайт | `/var/www/single443/index.html` |

Обычный домен: `IP.cdn-one.org`; REALITY SNI: `IP-с-дефисами.cdn-one.org`. REALITY target — собственный nginx `127.0.0.1:7443`, с сертификатом для обоих имён и TLS 1.3. Это локальный decoy, не имитация независимого стороннего сайта. Подписки рекламируют обычный домен и **порт 443** через `externalProxy`; для REALITY сохраняется отдельный SNI. Внутренние WS/XHTTP/gRPC работают без TLS, клиентская сторона — с TLS nginx.

nginx stream не передаёт PROXY protocol в Xray: так исключается подмена/несовпадение формата между backend’ами. Следствие: backend видит loopback вместо исходного IP; ограничения клиентов по IP и source-IP аудит не следует считать корректными в этой топологии. По умолчанию `limitIp=0`.

## Сеть, DNS и сертификат

* Нужны входящие **TCP/443 и UDP/443**, а также **TCP/80 для Let's Encrypt HTTP-01 и продления**. Installer настраивает nftables: разрешены новые входящие **22/TCP, 80/TCP, 443/TCP и 443/UDP** для IPv4 и IPv6; остальные входящие TCP/UDP и forwarding блокируются. Правила провайдера не изменяются.
* Два независимых HTTPS-сервиса определяют IPv4; при расхождении установка прекращается. Можно явно задать `PUBLIC_IPV4`.
* Оба A-имени должны разрешаться только в IPv4 VPS. Неоднозначные ответы и AAAA отвергаются этим IPv4-only адаптером. Installer не управляет зоной `cdn-one.org`, не гарантирует её работоспособность или доступность лимитов Let's Encrypt. При недоступности DNS автоматического обхода нет.
* Certbot использует webroot и один сертификат `single443` на два имени. Продление — штатный `certbot.timer`, затем `nginx -t`, reload nginx и restart x-ui для сертификата Hysteria2. Во время restart соединения Xray могут прерваться.
* Certbot staging доступен для отладки, но итоговая диагностика намеренно отвергает недоверенную цепочку; staging не считается успешной установкой.
* На первой загрузке панели, до API-настройки, действует upstream subscription default. Пока ACME получается, панель ещё не запускается; секретные клиенты создаются только после привязки subscription к loopback.

## Версии и совместимость

На 22.09.2026 GitHub Releases API вернул **v3.8.5** как latest. Прочитаны исходники тегов **v3.7.0 и v3.8.5**, а также текущий main. Адаптер ограничен семействами `3.7.x`/`3.8.x`, но не заявляет runtime-проверку каждого patch-релиза. Новое семейство завершает установку до изменений панели; нужен новый аудит API.

Используются:

* CLI `migrate`, `setting -port -listenIP -webBasePath -username -password` для первичной настройки.
* Session API: публичный `csrf-token`, `login`, обновление `panel/csrf-token` после входа.
* `/panel/api/setting/all`, `/setting/update` — чтение эффективных настроек и первичная настройка подписок.
* `/panel/api/inbounds/list`, `/inbounds/add` — inbound’ы. Существующие управляемые inbound’ы не пересоздаются и клиенты не затираются.
* `/panel/api/server/getNewX25519Cert`, `/server/getConfigJson` — ключи и построенный панелью Xray config. Перед явным restart он проверяется бинарником установленного Xray.

Xray 26.9.9 принимает WS, gRPC и Trojan, но предупреждает об их устаревании. Они включены по запросу. Источники и точные границы совместимости: [docs/UPSTREAM.md](docs/UPSTREAM.md).

Загрузка релиза проверяется по SHA-256 из GitHub Releases API, либо по опубликованному `.sha256`. У v3.7.0 отдельного checksum asset нет, но API публикует digest. При отсутствии обоих installer прекращает установку. Digest из того же GitHub-источника — контроль целостности загрузки, не независимая подпись автора.

## Subscription discovery и profile pages

Основной источник — API эффективных настроек. При его недоступности открывается `/etc/x-ui/x-ui.db` с `mode=ro` и `PRAGMA query_only=ON`. Таблицы перечисляются через `sqlite_master`, колонки — через `PRAGMA table_info`; фиксированных позиции колонок и имени таблицы нет. Распознаются семантические пары key/name/setting_key и value/setting_value. Дефолты отсутствующих записей берутся из `setting.go` **выбранного тега**, а не из догадки `/sub/` или порта 2096.

Названия смысловых настроек (`subPort`, `subPath`, `subDomain`, `subCertFile`, `subKeyFile`, `subListen` и флаги форматов) неизбежно относятся к версии API: неизвестная схема, неоднозначные таблицы, неполная TLS-пара, опасный/конфликтующий path приводят к отказу **до замены nginx**. Здесь graceful failure означает сохранение рабочей конфигурации и ненулевой exit code, а не тихое отключение подписок.

TLS backend проверяется с актуальными Host и SNI, CA verification включена. nginx сохраняет полный path, query, User-Agent, заголовки и содержимое ответа. Profile page и вложенный `/:subid/hwid-status` проходят через тот же prefix; HTML не переписывается. В диагностике используется клиентский User-Agent и проверяется состав ссылок, поэтому HTTP 200 с HTML не считается рабочей подпиской. Если вы вручную меняете публичный домен или пути, также проверьте соответствие `subURI/subJsonURI/subClashURI` в панели: installer сохраняет ваши изменения при rerun.

После изменения subPort/subPath/subDomain/TLS в панели примените её настройки, затем:

```bash
sudo bash /opt/single443/refresh.sh
```

Refresh повторяет discovery, сохраняет backup, перезапускает x-ui для применения настроек, пересобирает nginx, проверяет его и выполняет диагностику. `diagnose.sh` сам nginx не изменяет. Автоматического слежения за изменениями панели не устанавливается.

## Routing endpoints

Автоматически создаются каталоги и статические endpoints:

* `/routing/incy.json` — **placeholder**, пустые списки; импорт в INCY не проверен, это не заявленный готовый routing profile.
* `/routing/clash.yaml`, `/routing/mihomo.yaml` — пустые `payload: []` для rule-provider. Укажите нужные правила и соответствующий `behavior` в клиенте.
* `/mihomo/<subId>` и `/clash/<subId>` — aliases на **обнаруженный** Clash subscription path панели; это полноценная серверная подписка, в отличие от пустых статических rule-provider files.

Готовые пользовательские routing files при rerun сохраняются. Автоматического разнесения RU/Google, геофайлов или неизвестных правил приоритета нет.

## Идемпотентность, backup и восстановление

`/etc/single443/state.json` хранит пароль, UUID, paths, Reality keys/shortId и subId с правами root-only. Не удаляйте его между запусками. Для всех пяти inbound’ов общий subId и отдельные клиентские учётные данные. Повторная установка сохраняет их, не плодит nginx-блоки или timer’ы. Параллельные install/refresh защищены `flock`. Изменённые вручную managed transport/порт/listen или дубли приводят к отказу, а не перезаписи клиентов.

`--version latest` при новом релизе означает обновление; для воспроизводимого rerun pin обязателен. При потере state автоматического захвата чужой панели нет. Неуправляемые существующие панель/сайты отвергаются: сценарий предназначен для чистого VPS.

Перед изменением панели останавливается x-ui, сохраняются `/etc/nginx`, `/etc/x-ui` (включая SQLite WAL), `/usr/local/x-ui`, unit и статический сайт в `/var/backups/single443/<timestamp-pid>/`. На ошибке nginx/Xray/API/диагностики восстанавливаются эти файлы и прежнее активное состояние сервисов. Откат **не удаляет** установленные apt-пакеты, выпущенные ACME-сертификаты, журналы и backup. После аварии питания/kill -9 Bash trap не действует: требуется ручное восстановление из backup.

Проверяйте свободное место: архив релиза включает геофайлы, каждый backup может быть большим. Секреты в backup сохраняются root-only. Лог installer: `/var/log/single443/install.log`, проверка Xray: `/etc/single443/xray-validation.log`. Ошибки HTTP диагностируются без вывода секретных URLs. nginx access log для сайта отключён; upstream/error logs могут содержать чувствительные данные, не публикуйте их без проверки.

## Приёмка на VPS

1. Дождитесь успешного завершения installer и всех PASS в `diagnose.sh`.
2. С другого подключения откройте HTTPS-корень, panel URL, загрузите подписку. Проверки «public URL» внутри diagnose выполняются **с самого VPS**, не доказывают входящую доступность из другой сети.
3. Импортируйте подписку в совместимый клиент; отдельно проверьте REALITY, WS, XHTTP stream-up, Trojan gRPC и Hysteria2. Проверьте загрузку/отправку большого файла для XHTTP, H2 для gRPC и UDP-доступность Hysteria2.
4. Повторите установку той же pinned версии: должно остаться пять управляемых inbound’ов, те же UUID/paths/subId и рабочие клиентские соединения.
5. Проверьте `certbot renew --dry-run` отдельно; успешный первоначальный сертификат не доказывает будущее продление.

Диагностика проверяет nginx, сервисы, сертификат, panel API, TCP backends, UDP listener Xray, локальный SNI dispatcher/REALITY fallback, внешний URL сайта/панели, backend подписки с Host/SNI, пять типов внешних ссылок и Mihomo YAML. **TCP connect и UDP listener не являются авторизованными proxy handshake.**

## Локальная публикация файлов

В распакованном каталоге выполните (для нового пустого GitHub-репозитория):

```bash
git init -b BRANCH && git add . && git commit -m "Add upstream 3x-ui single-port installer" && git remote add origin https://github.com/USER/REPO.git && git push -u origin BRANCH
```

Основной репозиторий: `saintshamanix/lazyproxy`, ветка `main`. Пример выше предназначен для публикации собственной копии.

## Проверки разработки

```bash
find . -name '*.sh' -exec bash -n {} \;
python3 -m unittest discover -s tests -v
shellcheck -S warning -e SC1090,SC1091,SC2034 $(find . -name '*.sh')
```

GitHub Actions также рендерит полные nginx fixtures с тестовым сертификатом и запускает настоящий `nginx -t` на Ubuntu. До первой публикации этот CI не считается выполненным. `tests/render_fixtures.py` предназначен только для тестовых файлов, не для установки.

## Firewall (0.1.1)

Правила находятся в `templates/firewall.nft`, устанавливаются до запуска backend’ов и получения сертификата. Таблица `inet single443` заменяется атомарно после `nft --check`; `single443-firewall.service` восстанавливает её при загрузке. Повторный запуск не добавляет дубликаты. Исходящие соединения, loopback, established/related и ICMP/ICMPv6 разрешены; это необходимо для ответного трафика, PMTU и IPv6 neighbour discovery. Существующие соединения не обрываются принудительно. Новые входящие TCP/UDP допускаются только на перечисленные порты. Дополнительных исключений для входящего DHCP нет: этот профиль рассчитан на VPS со статической адресацией.

Перед применением требуется слушатель TCP/22. Если переменная SSH_CONNECTION доступна и показывает другой порт, установка прекращается. Installer не меняет sshd. Доступность SSH извне всё равно зависит от провайдера и его security groups.

Активные UFW/firewalld, сторонние nft base chains и legacy iptables rules приводят к остановке до изменения firewall: смешанные политики могут заблокировать даже разрешённые порты. Это профиль для чистого VPS и повторных запусков собственного installer’а, а не автоматическая миграция произвольного чужого firewall.

Существующие правила собственной таблицы и её unit/config сохраняются в backup и восстанавливаются при ошибке установки. `diagnose.sh` сравнивает полную live-таблицу с сохранённой установленной политикой и проверяет autostart. Остановка unit специально не снимает фильтрацию.

Проверка после установки: `sudo nft list table inet single443`.
Основание семантики nft: https://netfilter.org/projects/nftables/manpage.html .
