#!/usr/bin/env bash
set -Eeuo pipefail
umask 077
maintenance_run() {
  local now last=0 file
  now=$(date +%s)
  if [[ -f $MAINTENANCE_STATE/last-success ]]; then
    read -r last < "$MAINTENANCE_STATE/last-success"
    [[ $last =~ ^[0-9]+$ ]] || { echo 'Invalid maintenance timestamp' >&2; return 1; }
  fi
  if [[ ${1:-} != --force && $((now-last)) -lt 259200 ]]; then return 0; fi
  [[ $AUTO_REMOVE == yes || $AUTO_REMOVE == no ]] || { echo 'AUTO_REMOVE must be yes or no' >&2; return 1; }
  echo 'Maintenance started: nginx logs, journal and APT cache'
  for file in "$NGINX_LOG_DIR/access.log" "$NGINX_LOG_DIR/error.log"; do
    if [[ -f $file && ! -L $file ]]; then
      du -h -- "$file"
      truncate -c -s 0 -- "$file"
    fi
  done
  # Vacuum only removes archived journal files. Rotate first to include old
  # entries from active files. Active files may keep total usage above 10M.
  journalctl --rotate --vacuum-time=1d --vacuum-size=10M
  if [[ $AUTO_REMOVE == yes ]]; then
    DEBIAN_FRONTEND=noninteractive apt-get -o DPkg::Lock::Timeout=120 autoremove --purge -y
  fi
  apt-get -o DPkg::Lock::Timeout=120 clean
  date +%s > "$MAINTENANCE_STATE/last-success.tmp"
  mv -f -- "$MAINTENANCE_STATE/last-success.tmp" "$MAINTENANCE_STATE/last-success"
  echo 'Maintenance completed; next run after 72 hours'
}
maintenance_main() {
  [[ $EUID == 0 ]] || { echo 'Run as root'; return 1; }
  [[ $# == 0 || ( $# == 1 && $1 == --force ) ]] || { echo 'Usage: maintenance.sh [--force]'; return 2; }
  exec 9>/run/lock/single443.lock
  if ! flock -n 9; then echo 'Installer/refresh/maintenance active; retry on next timer tick'; return 0; fi
  MAINTENANCE_STATE=/var/lib/single443-maintenance
  NGINX_LOG_DIR=/var/log/nginx
  AUTO_REMOVE=no
  if [[ -f /etc/single443/maintenance.env ]]; then source /etc/single443/maintenance.env; fi
  mkdir -p "$MAINTENANCE_STATE"
  maintenance_run "$@"
}
if [[ ${BASH_SOURCE[0]} == "$0" ]]; then maintenance_main "$@"; fi
