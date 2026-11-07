#!/usr/bin/env bash
set -Eeuo pipefail
configure_iplimit() {
  IPLIMIT_CHANGED=yes
  mkdir -p /etc/fail2ban/jail.d /etc/fail2ban/filter.d /var/log/x-ui
  touch /var/log/x-ui/3xipl.log
  cat > /etc/fail2ban/filter.d/single443-ipl.conf <<'CONF'
[Definition]
datepattern = ^%%Y/%%m/%%d %%H:%%M:%%S
failregex = \[LIMIT_IP\]\s*Email\s*=\s*<F-USER>.+</F-USER>\s*\|\|\s*Disconnecting OLD IP\s*=\s*<ADDR>\s*\|\|\s*Timestamp\s*=\s*\d+
ignoreregex =
CONF
  cat > /etc/fail2ban/jail.d/single443-ipl.local <<'CONF'
# Managed by single443. Client limits default to zero (unlimited).
[sshd]
backend = systemd

[3x-ipl]
enabled = true
backend = polling
filter = single443-ipl
logpath = /var/log/x-ui/3xipl.log
maxretry = 1
findtime = 32
bantime = 30m
ignoreip = 127.0.0.0/8 ::1
action = nftables[type=multiport, name=single443-tcp, actname=single443-tcp, port="443", protocol=tcp, table=single443_f2b_tcp]
         nftables[type=multiport, name=single443-udp, actname=single443-udp, port="443,51820", protocol=udp, table=single443_f2b_udp]
CONF
  fail2ban-client -t
  systemctl enable fail2ban
  systemctl restart fail2ban
  local attempt
  for attempt in {1..20}; do
    if fail2ban-client status 3x-ipl >/dev/null 2>&1; then
      log 'IP Limit infrastructure ready; default client limit is 0 (unlimited)'
      return 0
    fi
    sleep 1
  done
  die 'Fail2ban 3x-ipl jail did not start'
}
restore_iplimit() {
  if [[ ${IPLIMIT_CHANGED:-no} == yes ]]; then
    if [[ $FAIL2BAN_WAS_ENABLED == yes ]]; then systemctl enable fail2ban; else systemctl disable fail2ban; fi
    if [[ $FAIL2BAN_WAS_ACTIVE == yes ]]; then systemctl restart fail2ban; fi
  fi
}
