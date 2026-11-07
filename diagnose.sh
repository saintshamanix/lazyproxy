#!/usr/bin/env bash
set -Eeuo pipefail
ROOT=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
[[ $EUID == 0 ]] || { echo 'Run as root'; exit 1; }
source "$ROOT/lib/common.sh"
source "$ROOT/lib/firewall.sh"
firewall_verify
if [[ -f /etc/fail2ban/jail.d/single443-ipl.local ]]; then
  fail2ban-client status 3x-ipl
fi
sysctl net.ipv4.tcp_congestion_control net.core.default_qdisc
log "IP Limit: installer defaults to unlimited; real-IP forwarding is required before enabling limits behind nginx"
python3 "$ROOT/lib/engine.py" diagnose
