#!/usr/bin/env bash
set -Eeuo pipefail
FIREWALL_SNAPSHOT=no
firewall_preflight() {
  local peer client_port server server_port
  if [[ -n ${SSH_CONNECTION:-} ]]; then
    read -r peer client_port server server_port <<< "$SSH_CONNECTION"
    [[ $server_port == 22 ]] || die 'Current SSH connection uses a port other than 22; refusing to lock out access'
  fi
  [[ -n $(ss -H -lnt 'sport = :22') ]] || die 'No SSH listener on TCP/22; configure SSH before applying the firewall'
  # This clean-VPS installer must not silently override another firewall manager.
  if command -v ufw >/dev/null && LC_ALL=C ufw status | grep -q '^Status: active'; then
    die 'UFW is active; resolve the existing policy before installing'
  fi
  if systemctl is-active --quiet firewalld; then
    die 'firewalld is active; resolve the existing policy before installing'
  fi
  nft -j list ruleset > "$STATE/firewall-before-check.json"
  python3 - "$STATE/firewall-before-check.json" <<'PY'
import json, sys
from pathlib import Path
owned={"single443"}
if Path("/etc/fail2ban/jail.d/single443-ipl.local").is_file():
    owned.update(("single443_f2b_tcp", "single443_f2b_udp"))
items=json.load(open(sys.argv[1]))['nftables']
foreign=[x['chain'] for x in items if 'chain' in x and 'hook' in x['chain'] and not (x['chain']['family']=='inet' and x['chain']['table'] in owned)]
if foreign:
    sys.exit('Existing unmanaged firewall base chains detected; refusing mixed firewall policies')
PY
  # Reject legacy rules too: they are not represented by nft list ruleset.
  for saver in iptables-legacy-save ip6tables-legacy-save; do
    if command -v "$saver" >/dev/null; then
      "$saver" > "$STATE/$saver.txt"
      if grep -Eq '^-A |^:[^ ]+ (DROP|REJECT) ' "$STATE/$saver.txt"; then
        die 'Existing legacy iptables policy detected; clean VPS required'
      fi
    fi
  done
}
firewall_snapshot() {
  nft -j list ruleset > "$BACKUP/firewall-all-before.json"
  if nft list table inet single443 > "$BACKUP/firewall-table.nft" 2>/dev/null; then
    :
  else
    : > "$BACKUP/firewall-table.nft"
  fi
  FIREWALL_WAS_ACTIVE=no; FIREWALL_WAS_ENABLED=no
  systemctl is-active --quiet single443-firewall && FIREWALL_WAS_ACTIVE=yes
  systemctl is-enabled --quiet single443-firewall && FIREWALL_WAS_ENABLED=yes
  FIREWALL_SNAPSHOT=yes
}
configure_firewall() {
  log 'Applying inbound firewall: TCP 22/80/443, UDP 443/51820; IPv4 and IPv6'
  mkdir -p /etc/single443
  install -m 600 "$ROOT/templates/firewall.nft" /etc/single443/firewall.nft
  nft --check --file /etc/single443/firewall.nft
  cat > /etc/systemd/system/single443-firewall.service <<'UNIT'
[Unit]
Description=single443 inbound firewall (IPv4 and IPv6)
DefaultDependencies=no
After=systemd-modules-load.service nftables.service ufw.service firewalld.service
Before=network-pre.target nginx.service x-ui.service
Wants=network-pre.target
[Service]
Type=oneshot
RemainAfterExit=yes
ExecStart=/usr/sbin/nft -f /etc/single443/firewall.nft
ExecReload=/usr/sbin/nft -f /etc/single443/firewall.nft
# Intentionally no ExecStop: stopping the unit must not expose services.
[Install]
WantedBy=multi-user.target
UNIT
  systemctl daemon-reload
  # Apply the checked batch atomically, even if the unit is already active.
  nft --file /etc/single443/firewall.nft
  systemctl enable single443-firewall
  systemctl start single443-firewall
}
firewall_restore() {
  [[ $FIREWALL_SNAPSHOT == yes ]] || return 0
  log 'Restoring prior firewall table and unit state'
  systemctl stop single443-firewall || true
  {
    echo 'add table inet single443'
    echo 'delete table inet single443'
    cat "$BACKUP/firewall-table.nft"
  } > "$BACKUP/firewall-restore.nft"
  nft --check --file "$BACKUP/firewall-restore.nft" || return 1
  nft --file "$BACKUP/firewall-restore.nft" || return 1
  if [[ $FIREWALL_WAS_ENABLED == yes ]]; then
    systemctl enable single443-firewall
  else
    systemctl disable single443-firewall 2>/dev/null || true
  fi
  if [[ $FIREWALL_WAS_ACTIVE == yes ]]; then systemctl start single443-firewall; fi
}
firewall_verify() {
  nft --check --file /etc/single443/firewall.nft
  local actual expected
  actual=$(mktemp); expected=$(mktemp)
  # -s omits stateful counters; compare the complete live table with a baseline
  # saved immediately after the validated configuration was applied.
  nft -s list table inet single443 > "$actual"
  cp /etc/single443/firewall-expected.txt "$expected"
  if ! cmp -s "$actual" "$expected"; then
    rm -f "$actual" "$expected"
    die 'Live firewall differs from the installed policy'
  fi
  rm -f "$actual" "$expected"
  systemctl is-enabled --quiet single443-firewall
  systemctl is-active --quiet single443-firewall
  log 'PASS firewall: TCP 22/80/443, UDP 443/51820; persistent IPv4/IPv6 policy'
}
