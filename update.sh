#!/usr/bin/env bash
# Update managed clients/site/routing without upgrading upstream 3x-ui.
set -Eeuo pipefail
umask 077
ROOT=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
source "$ROOT/lib/common.sh"
source "$ROOT/lib/nginx.sh"
[[ $EUID == 0 ]] || die 'Run as root'
[[ -f $STATE/state.json ]] || die 'No managed installation found'
exec 9>/run/lock/single443.lock
flock -n 9 || die 'Installer/refresh is running'
mkdir -p /var/log/single443
exec > >(tee -a /var/log/single443/install.log) 2>&1
version=$(helper value installed_version)
[[ $version =~ ^v?3\.(7|8)\.[0-9]+$ ]] || die 'Unsupported installed panel version'
helper discover
trap 'on_error "$?" "$LINENO"' ERR
trap 'on_error 130 "$LINENO"' INT TERM
backup_begin
systemctl start x-ui
helper wait-panel
helper inbounds
install_acme_web
render_nginx
activate_nginx
bash "$ROOT/diagnose.sh"
mkdir -p /opt/single443
if [[ $(realpath "$ROOT") != /opt/single443 ]]; then cp -a "$ROOT/." /opt/single443/; fi
TX_ACTIVE=no
trap - ERR INT TERM
log "Updated. Import the five independent subscriptions from $STATE/access.txt"
log "Backup: $BACKUP"
