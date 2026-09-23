#!/usr/bin/env bash
set -Eeuo pipefail
STATE=/etc/single443
TX_ACTIVE=no
BACKUP_IN_PROGRESS=no
log() { printf '[%s] %s\n' "$(date -Is)" "$*"; }
die() { log "ERROR: $*" >&2; return 1; }
helper() { python3 "$ROOT/lib/engine.py" "$@"; }
preflight() {
  if [[ ! -f $STATE/state.json ]]; then
    [[ ! -e /etc/x-ui/x-ui.db && ! -e /usr/local/x-ui/x-ui ]] || die 'Existing unmanaged 3x-ui: use a clean VPS'
    [[ -z $(ss -H -lntup '( sport = :443 or sport = :7443 or sport = :8443 or sport = :10001 or sport = :10002 or sport = :10003 or sport = :2053 or sport = :2096 )') ]] || die 'Required ports already occupied'
    [[ ! -e /etc/nginx/sites-enabled/default || -L /etc/nginx/sites-enabled/default ]] || die 'Unexpected nginx default file'
    if find /etc/nginx/sites-enabled /etc/nginx/conf.d -type f -o -type l | grep -v '/sites-enabled/default$' | grep -q .; then
      die 'Non-default nginx sites found; clean VPS required'
    fi
  fi
}
init_state() { helper init; }
backup_begin() {
  BACKUP=/var/backups/single443/$(date +%Y%m%dT%H%M%S)-$$
  mkdir -p "$BACKUP/root"
  XUI_WAS_ACTIVE=no; NGINX_WAS_ACTIVE=no
  systemctl is-active --quiet x-ui && XUI_WAS_ACTIVE=yes
  systemctl is-active --quiet nginx && NGINX_WAS_ACTIVE=yes
  FAIL2BAN_WAS_ACTIVE=no; FAIL2BAN_WAS_ENABLED=no
  systemctl is-active --quiet fail2ban && FAIL2BAN_WAS_ACTIVE=yes
  systemctl is-enabled --quiet fail2ban && FAIL2BAN_WAS_ENABLED=yes
  MAINTENANCE_WAS_ACTIVE=no; MAINTENANCE_WAS_ENABLED=no
  systemctl is-active --quiet single443-maintenance.timer && MAINTENANCE_WAS_ACTIVE=yes
  systemctl is-enabled --quiet single443-maintenance.timer && MAINTENANCE_WAS_ENABLED=yes
  BACKUP_IN_PROGRESS=yes
  systemctl stop x-ui 2>/dev/null || true
  # SQLite and WAL are copied with the owning service stopped.
  for path in /usr/local/libexec/single443-maintenance /etc/systemd/system/single443-maintenance.service /etc/systemd/system/single443-maintenance.timer /etc/single443/maintenance.env /var/lib/single443-maintenance /etc/fail2ban /etc/sysctl.d/99-single443-bbr.conf /etc/nginx /etc/x-ui /usr/local/x-ui /etc/systemd/system/x-ui.service /var/www/single443 /etc/single443/access.txt /etc/single443/User6-AmneziaWG.conf /etc/single443/subscription.json /etc/single443/firewall.nft /etc/single443/firewall-expected.txt /etc/systemd/system/single443-firewall.service; do
    if [[ -e $path ]]; then
      mkdir -p "$BACKUP/root$(dirname "$path")"
      cp -a "$path" "$BACKUP/root$path"
    fi
  done
  if declare -F firewall_snapshot >/dev/null; then firewall_snapshot; fi
  cp "$STATE/state.json" "$BACKUP/state.json"
  TX_ACTIVE=yes
  BACKUP_IN_PROGRESS=no
}
rollback() {
  log "Rolling back panel/nginx from $BACKUP"
  if [[ ${MAINTENANCE_CHANGED:-no} == yes ]]; then systemctl stop single443-maintenance.timer; fi
  systemctl stop x-ui nginx 2>/dev/null || true
  if [[ ${IPLIMIT_CHANGED:-no} == yes ]]; then systemctl stop fail2ban; fi
  for path in /usr/local/libexec/single443-maintenance /etc/systemd/system/single443-maintenance.service /etc/systemd/system/single443-maintenance.timer /etc/single443/maintenance.env /var/lib/single443-maintenance /etc/fail2ban /etc/sysctl.d/99-single443-bbr.conf /etc/nginx /etc/x-ui /usr/local/x-ui /etc/systemd/system/x-ui.service /var/www/single443 /etc/single443/access.txt /etc/single443/User6-AmneziaWG.conf /etc/single443/subscription.json /etc/single443/firewall.nft /etc/single443/firewall-expected.txt /etc/systemd/system/single443-firewall.service; do
    rm -rf -- "$path"
    if [[ -e $BACKUP/root$path ]]; then cp -a "$BACKUP/root$path" "$path"; fi
  done
  cp "$BACKUP/state.json" "$STATE/state.json"
  if declare -F restore_maintenance >/dev/null; then restore_maintenance; fi
  if declare -F restore_iplimit >/dev/null; then restore_iplimit; fi
  if declare -F restore_bbr >/dev/null; then restore_bbr; fi
  systemctl daemon-reload
  if declare -F firewall_restore >/dev/null; then firewall_restore; fi
  if [[ $XUI_WAS_ACTIVE == yes ]]; then systemctl start x-ui; fi
  # enable/disable during firewall restoration can change unit links.
  systemctl daemon-reload
  if [[ $NGINX_WAS_ACTIVE == yes ]]; then nginx -t && systemctl start nginx; fi
}
on_error() {
  local status=$1 line=$2
  trap - ERR INT TERM
  set +e
  log "Failed at line $line (status $status); see /var/log/single443/install.log"
  if [[ $TX_ACTIVE == yes ]]; then
    rollback
  elif [[ $BACKUP_IN_PROGRESS == yes && ${XUI_WAS_ACTIVE:-no} == yes ]]; then
    systemctl start x-ui
  fi
  exit "$status"
}
