#!/usr/bin/env bash
# Install only the cloud-themed decoy assets into an existing LazyProxy VPS.
set -Eeuo pipefail
umask 077
[[ $EUID == 0 ]] || { echo 'Run as root.' >&2; exit 1; }
ROOT=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
WEB=/var/www/single443
CONF=/etc/nginx/conf.d/single443-web.conf
BACKUPS=/var/backups/single443-cloud-us
MODE=${1:-install}
[[ $# == 0 || ( $# == 2 && $MODE == --restore ) ]] || { echo 'Usage: install-cloud-us.sh [--restore BACKUP_DIR]' >&2; exit 1; }
for cmd in python3 curl nginx flock sha256sum install; do
  command -v "$cmd" >/dev/null || { echo "Missing command: $cmd" >&2; exit 1; }
done
exec 9>/run/lock/single443.lock
flock -n 9 || { echo 'Another LazyProxy operation is running.' >&2; exit 1; }
[[ -d $WEB && ! -L $WEB && -f $CONF && ! -L $CONF ]] || { echo 'Standard LazyProxy installation not found.' >&2; exit 1; }
for name in index.html site.js; do
  [[ -f $WEB/$name && ! -L $WEB/$name ]] || { echo "Unexpected asset: $name" >&2; exit 1; }
done
DOMAIN=$(python3 - "$CONF" <<'PY'
import pathlib,re,sys
s=pathlib.Path(sys.argv[1]).read_text()
m=re.search(r'listen 127\.0\.0\.1:7443 ssl(?: http2)?;\s*server_name ([A-Za-z0-9.-]+)',s)
if not m or 'root /var/www/single443;' not in s:
    sys.exit('Unsupported nginx layout; nothing changed.')
print(m.group(1))
PY
)
nginx -t
if [[ $MODE == --restore ]]; then
  SOURCE=$(realpath -- "$2")
  [[ $SOURCE == "$BACKUPS/"* && $(dirname -- "$SOURCE") == "$BACKUPS" && ! -L $2 ]] || { echo 'Invalid backup directory.' >&2; exit 1; }
  (cd "$SOURCE" && sha256sum -c SHA256SUMS)
else
  SOURCE=$ROOT/templates/cloud-us
  (cd "$SOURCE" && sha256sum -c SHA256SUMS)
fi
for name in index.html site.js; do
  [[ -f $SOURCE/$name && ! -L $SOURCE/$name ]] || { echo "Missing source asset: $name" >&2; exit 1; }
done
[[ ! -L $BACKUPS ]] || { echo 'Backup directory must not be a symlink.' >&2; exit 1; }
install -d -m 700 "$BACKUPS"
BACKUP=$(mktemp -d "$BACKUPS/$(date -u +%Y%m%dT%H%M%SZ)-XXXXXX")
cp -p -- "$WEB/index.html" "$WEB/site.js" "$BACKUP/"
(cd "$BACKUP" && sha256sum index.html site.js > SHA256SUMS)
TMP=$(mktemp -d "$WEB/.cloud-us-XXXXXX")
CHANGED=no
cleanup() { rm -rf -- "$TMP"; }
rollback() {
  local code=$1
  trap - ERR HUP INT TERM
  if [[ $CHANGED == yes ]]; then
    cp -p -- "$BACKUP/index.html" "$WEB/index.html"
    cp -p -- "$BACKUP/site.js" "$WEB/site.js"
    echo 'Installation failed; previous assets restored.' >&2
  fi
  echo "Backup: $BACKUP" >&2
  exit "$code"
}
trap cleanup EXIT
trap 'rollback $?' ERR
trap 'rollback 129' HUP
trap 'rollback 130' INT
trap 'rollback 143' TERM
for name in index.html site.js; do install -m 644 "$SOURCE/$name" "$TMP/$name"; done
CHANGED=yes
mv -f -- "$TMP/site.js" "$WEB/site.js"
mv -f -- "$TMP/index.html" "$WEB/index.html"
for name in index.html site.js; do
  if [[ $name == index.html ]]; then URL_PATH=/; else URL_PATH=/site.js; fi
  curl -fLsS --noproxy '*' --connect-timeout 5 --max-time 15 \
    --resolve "$DOMAIN:7443:127.0.0.1" \
    "https://$DOMAIN:7443$URL_PATH?cloud-install=$(date +%s)" -o "$TMP/check"
  cmp -s -- "$SOURCE/$name" "$TMP/check"
done
CHANGED=no
trap - ERR HUP INT TERM
echo 'OK: assets installed and verified through local nginx HTTPS.'
echo 'Panel, subscriptions, nginx configuration and services were not changed.'
echo "Backup: $BACKUP"
echo "Rollback: bash $ROOT/install-cloud-us.sh --restore $BACKUP"
