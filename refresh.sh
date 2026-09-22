#!/usr/bin/env bash
set -Eeuo pipefail
ROOT=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
source "$ROOT/lib/common.sh"
source "$ROOT/lib/nginx.sh"
[[ $EUID == 0 ]] || die 'Run as root'
exec 9>/run/lock/single443.lock
flock -n 9 || die 'Installer/refresh is running'
# Discovery fails before touching nginx if effective settings are unknown.
helper discover
trap 'on_error "$?" "$LINENO"' ERR
trap 'on_error 130 "$LINENO"' INT TERM
backup_begin
systemctl start x-ui
render_nginx
activate_nginx
bash "$ROOT/diagnose.sh"
TX_ACTIVE=no
