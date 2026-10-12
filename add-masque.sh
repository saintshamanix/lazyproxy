#!/usr/bin/env bash
# Add MASQUE to a managed installation after upgrading upstream through its panel.
set -Eeuo pipefail
umask 077
ROOT=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
source "$ROOT/lib/common.sh"
source "$ROOT/lib/nginx.sh"
source "$ROOT/lib/masque.sh"
[[ $EUID == 0 ]] || die 'Run as root'
[[ -f $STATE/state.json ]] || die 'No managed installation'
MASQUE_DOMAIN=''
if [[ $# == 2 && $1 == --masque-domain ]]; then MASQUE_DOMAIN=$2; elif [[ $# != 0 ]]; then die 'Usage: add-masque.sh [--masque-domain DNS_NAME]'; fi
export MASQUE_DOMAIN
exec 9>/run/lock/single443.lock
flock -n 9 || die 'Another installer operation is running'
mkdir -p /var/log/single443
exec > >(tee -a /var/log/single443/install.log) 2>&1
helper has-masque "$(helper panel-version)"
helper discover
nginx -t
trap 'on_error "$?" "$LINENO"' ERR
trap 'on_error 130 "$LINENO"' INT TERM
backup_begin
systemctl start x-ui
helper wait-panel
helper sync-panel-version
helper masque-prepare
obtain_masque_cert
helper masque-add
render_nginx
activate_nginx
helper masque-check
# Keep existing installed adapters intact until all checks succeed.
mkdir -p /opt/single443
if [[ $(realpath "$ROOT") != /opt/single443 ]]; then cp -a "$ROOT/." /opt/single443/; fi
TX_ACTIVE=no
trap - ERR INT TERM
log 'MASQUE added on TCP/443 (HTTP/2). Add/attach clients in the panel; use JSON subscriptions.'
log 'Authenticated client traffic still requires an external acceptance test.'
log "Backup: $BACKUP"
