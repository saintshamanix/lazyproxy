#!/usr/bin/env bash
# Serialize issuance and reload with installer/refresh; retry failed reloads even
# when a subsequent Certbot check does not issue another certificate.
set -Eeuo pipefail
umask 077
exec 9>/run/lock/single443.lock
flock -w 300 9
/opt/single443-certbot-5.8.0/bin/certbot renew --non-interactive \
  --config-dir /etc/single443/acme --work-dir /var/lib/single443-acme \
  --logs-dir /var/log/single443-acme --no-random-sleep-on-renew --no-directory-hooks
export RENEWED_LINEAGE=/etc/single443/acme/live/single443
fingerprint=$(sha256sum "$RENEWED_LINEAGE/fullchain.pem" | cut -d ' ' -f 1)
marker=/etc/single443/acme/last-deployed-sha256
if [[ ! -f $marker || $(cat "$marker") != "$fingerprint" ]]; then
  SINGLE443_ACME_LOCK_HELD=yes /etc/single443/acme/renewal-hooks/deploy/single443
  printf '%s\n' "$fingerprint" > "$marker"
fi
