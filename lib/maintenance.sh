#!/usr/bin/env bash
set -Eeuo pipefail
install_maintenance() {
  MAINTENANCE_CHANGED=yes
  systemctl stop single443-maintenance.timer 2>/dev/null || true
  install -D -m 700 "$ROOT/maintenance.sh" /usr/local/libexec/single443-maintenance
  install -m 644 "$ROOT/templates/systemd/single443-maintenance.service" /etc/systemd/system/single443-maintenance.service
  install -m 644 "$ROOT/templates/systemd/single443-maintenance.timer" /etc/systemd/system/single443-maintenance.timer
  if [[ ! -f /etc/single443/maintenance.env ]]; then
    printf 'AUTO_REMOVE=no\n' > /etc/single443/maintenance.env
    chmod 600 /etc/single443/maintenance.env
  fi
  mkdir -p /var/lib/single443-maintenance
  if [[ ! -f /var/lib/single443-maintenance/last-success ]]; then
    date +%s > /var/lib/single443-maintenance/last-success
  fi
  systemd-analyze verify /etc/systemd/system/single443-maintenance.service /etc/systemd/system/single443-maintenance.timer
  systemctl daemon-reload
  systemctl enable --now single443-maintenance.timer
  systemctl is-active --quiet single443-maintenance.timer
  log 'Maintenance timer enabled: cleanup every 72 hours, first cleanup in three days'
}
restore_maintenance() {
  if [[ ${MAINTENANCE_CHANGED:-no} == yes ]]; then
    systemctl daemon-reload
    if [[ $MAINTENANCE_WAS_ENABLED == yes ]]; then systemctl enable single443-maintenance.timer; else systemctl disable single443-maintenance.timer 2>/dev/null || true; fi
    if [[ $MAINTENANCE_WAS_ACTIVE == yes ]]; then systemctl start single443-maintenance.timer; fi
  fi
}
