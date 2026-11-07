#!/usr/bin/env bash
set -Eeuo pipefail
obtain_masque_cert() {
  local name
  name=$(helper value masque_domain)
  local -a args=(certonly --webroot -w /var/www/single443 --non-interactive --agree-tos --cert-name single443-masque --keep-until-expiring --no-directory-hooks -d "$name")
  if [[ -n ${ACME_EMAIL:-} ]]; then args+=(--email "$ACME_EMAIL"); else args+=(--register-unsafely-without-email); fi
  if [[ ${ACME_STAGING:-no} == yes ]]; then args+=(--staging); fi
  certbot "${args[@]}"
  # Separate lineage: adding MASQUE never replaces the existing TLS certificate.
  install -D -m 755 "$ROOT/lib/renew-hook.sh" /etc/letsencrypt/renewal-hooks/deploy/single443
  systemctl enable --now certbot.timer
}
