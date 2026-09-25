#!/usr/bin/env bash
# Update managed clients/site/routing without upgrading upstream 3x-ui.
set -Eeuo pipefail
umask 077
ROOT=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
source "$ROOT/lib/common.sh"
source "$ROOT/lib/nginx.sh"
source "$ROOT/lib/firewall.sh"
source "$ROOT/lib/tuning.sh"
source "$ROOT/lib/iplimit.sh"
source "$ROOT/lib/maintenance.sh"
source "$ROOT/lib/certs.sh"
[[ $EUID == 0 ]] || die 'Run as root'
[[ -f $STATE/state.json ]] || die 'No managed installation found'
exec 9>/run/lock/single443.lock
flock -n 9 || die 'Installer/refresh is running'
mkdir -p /var/log/single443
exec > >(tee -a /var/log/single443/install.log) 2>&1
version=$(helper value installed_version)
[[ $version == v3.8.5 ]] || die 'AmneziaWG update requires installed v3.8.5; use full install --version 3.8.5'
helper discover
firewall_preflight
trap 'on_error "$?" "$LINENO"' ERR
trap 'on_error 130 "$LINENO"' INT TERM
DEBIAN_FRONTEND=noninteractive apt-get update -q
DEBIAN_FRONTEND=noninteractive apt-get install -y kmod fail2ban python3-systemd
backup_begin
configure_bbr
configure_iplimit
configure_firewall
nft -s list table inet single443 > /etc/single443/firewall-expected.txt
systemctl start x-ui
helper wait-panel
helper inbounds
install_acme_web
render_nginx
activate_nginx
bash "$ROOT/diagnose.sh"
mkdir -p /opt/single443
if [[ $(realpath "$ROOT") != /opt/single443 ]]; then cp -a "$ROOT/." /opt/single443/; fi
install_renew_hook
install_maintenance
TX_ACTIVE=no
trap - ERR INT TERM
log "Updated. Import the six independent subscriptions from $STATE/access.txt"
log "Backup: $BACKUP"
