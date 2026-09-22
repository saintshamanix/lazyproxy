#!/usr/bin/env bash
set -Eeuo pipefail
obtain_cert() {
  local domain reality
  domain=$(helper value domain); reality=$(helper value reality_domain)
  local -a args=(certonly --webroot -w /var/www/single443 --non-interactive --agree-tos --cert-name single443 --keep-until-expiring -d "$domain" -d "$reality")
  if [[ -n $ACME_EMAIL ]]; then args+=(--email "$ACME_EMAIL"); else args+=(--register-unsafely-without-email); fi
  if [[ $ACME_STAGING == yes ]]; then args+=(--staging); fi
  certbot "${args[@]}"
  chmod 700 /etc/letsencrypt/archive /etc/letsencrypt/live
}
install_renew_hook() {
  install -m 755 "$ROOT/lib/renew-hook.sh" /etc/letsencrypt/renewal-hooks/deploy/single443
  systemctl enable --now certbot.timer
}
