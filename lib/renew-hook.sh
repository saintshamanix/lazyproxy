#!/usr/bin/env bash
set -Eeuo pipefail
[[ ${RENEWED_LINEAGE:-} == /etc/letsencrypt/live/single443 || ${RENEWED_LINEAGE:-} == /etc/single443/acme/live/single443 ]] || exit 0
if [[ ${SINGLE443_ACME_LOCK_HELD:-no} != yes ]]; then
  exec 9>/run/lock/single443.lock
  flock -w 120 9
fi
nginx -t
systemctl reload nginx
# Xray's Hysteria certificate must also be reloaded.
systemctl restart x-ui
