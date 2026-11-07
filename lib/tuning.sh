#!/usr/bin/env bash
set -Eeuo pipefail
# BBR applies to kernel TCP sockets, not the UDP transport of Hysteria2/AWG.
configure_bbr() {
  local available
  available=$(sysctl -n net.ipv4.tcp_available_congestion_control)
  if [[ " $available " != *' bbr '* ]]; then
    modprobe tcp_bbr 2>/dev/null || true
    available=$(sysctl -n net.ipv4.tcp_available_congestion_control)
  fi
  if [[ " $available " != *' bbr '* ]]; then
    log 'SKIP BBR: running kernel does not provide tcp_bbr; kernel left unchanged'
    return 0
  fi
  modprobe sch_fq 2>/dev/null || true
  # Snapshot runtime settings independently from the persistent configuration.
  sysctl -n net.ipv4.tcp_congestion_control > "$BACKUP/bbr-previous-cc"
  sysctl -n net.core.default_qdisc > "$BACKUP/bbr-previous-qdisc"
  BBR_CHANGED=yes
  cat > /etc/sysctl.d/99-single443-bbr.conf <<'CONF'
net.core.default_qdisc = fq
net.ipv4.tcp_congestion_control = bbr
CONF
  sysctl -p /etc/sysctl.d/99-single443-bbr.conf
  [[ $(sysctl -n net.ipv4.tcp_congestion_control) == bbr ]] || die 'BBR activation failed'
  [[ $(sysctl -n net.core.default_qdisc) == fq ]] || die 'Default fq configuration failed'
  log 'BBR enabled; fq selected for newly created qdiscs (existing interfaces left unchanged)'
}
restore_bbr() {
  if [[ ${BBR_CHANGED:-no} == yes ]]; then
    sysctl -w "net.ipv4.tcp_congestion_control=$(cat "$BACKUP/bbr-previous-cc")"
    sysctl -w "net.core.default_qdisc=$(cat "$BACKUP/bbr-previous-qdisc")"
  fi
}
