#!/usr/bin/env bash
# Move existing embedded AmneziaWG to a second, already configured IPv4.
set -Eeuo pipefail
umask 077
ROOT=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
source "$ROOT/lib/common.sh"
source "$ROOT/lib/firewall.sh"
[[ $EUID == 0 && $# == 1 ]] || die 'Usage: sudo bash attach-secondary-ip.sh SECOND_IPV4'
[[ -f $STATE/state.json ]] || die 'No managed installation'
exec 9>/run/lock/single443.lock
flock -n 9 || die 'Another installer operation is running'
mkdir -p /var/log/single443
exec > >(tee -a /var/log/single443/install.log) 2>&1
helper secondary-preflight "$1"
firewall_preflight
nginx -t
trap 'on_error "$?" "$LINENO"' ERR
trap 'on_error 130 "$LINENO"' INT TERM
backup_begin
systemctl start x-ui
helper wait-panel
helper attach-secondary "$1"
configure_firewall
nft -s list table inet single443 > "$STATE/firewall-expected.txt"
firewall_verify
helper secondary-verify
nginx -t
if [[ $(realpath "$ROOT") != /opt/single443 ]]; then
  cp -a "$ROOT/." /opt/single443/
fi
mkdir -p /etc/systemd/system/x-ui.service.d
cat > /etc/systemd/system/x-ui.service.d/single443-addresses.conf <<'UNIT'
[Unit]
Wants=network-online.target
After=network-online.target
[Service]
ExecStartPre=/usr/bin/python3 /opt/single443/lib/engine.py wait-addresses
UNIT
systemctl daemon-reload
systemctl restart x-ui
helper wait-panel
helper secondary-verify
TX_ACTIVE=no
trap - ERR INT TERM
log "Completed. Download fresh AmneziaWG client configurations from the panel: endpoint $1:443."
log 'External AWG/Hysteria2 handshakes must still be checked from a client.'
log "Backup: $BACKUP"
