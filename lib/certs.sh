#!/usr/bin/env bash
set -Eeuo pipefail
# Separate configuration prevents the distribution's older certbot.timer from
# attempting to renew IP certificates with an unsupported ACME client.
prepare_ip_certbot() {
  if [[ ! -x /opt/single443-certbot-5.8.0/bin/certbot ]]; then
    DEBIAN_FRONTEND=noninteractive apt-get install -y python3-venv
    python3 -m venv /opt/single443-certbot-5.8.0
    /opt/single443-certbot-5.8.0/bin/python -m pip install --disable-pip-version-check 'certbot==5.8.0' 'acme==5.8.0'
  fi
  [[ $(/opt/single443-certbot-5.8.0/bin/certbot --version) == 'certbot 5.8.0' ]] || die 'Unexpected isolated Certbot version'
}
obtain_cert() {
  local domain reality certbot_bin=certbot config_dir=/etc/letsencrypt
  domain=$(helper value domain); reality=$(helper value reality_domain)
  local -a args=(certonly --webroot -w /var/www/single443 --non-interactive --agree-tos --cert-name single443 --keep-until-expiring --no-directory-hooks)
  if [[ $(helper value ip_tls) == yes ]]; then
    prepare_ip_certbot
    certbot_bin=/opt/single443-certbot-5.8.0/bin/certbot
    config_dir=/etc/single443/acme
    args+=(--config-dir "$config_dir" --work-dir /var/lib/single443-acme --logs-dir /var/log/single443-acme --required-profile shortlived --ip-address "$domain" -d "$reality")
  else
    args+=(-d "$domain" -d "$reality")
  fi
  if [[ -n $ACME_EMAIL ]]; then args+=(--email "$ACME_EMAIL"); else args+=(--register-unsafely-without-email); fi
  if [[ $ACME_STAGING == yes ]]; then args+=(--staging); fi
  "$certbot_bin" "${args[@]}"
  chmod 700 "$config_dir/archive" "$config_dir/live"
}
install_renew_hook() {
  local config_dir=/etc/letsencrypt
  if [[ $(helper value ip_tls) == yes ]]; then
    prepare_ip_certbot
    config_dir=/etc/single443/acme
    IP_RENEW_CHANGED=yes
    install -m 644 "$ROOT/templates/systemd/single443-acme.service" /etc/systemd/system/single443-acme.service
    install -m 644 "$ROOT/templates/systemd/single443-acme.timer" /etc/systemd/system/single443-acme.timer
    systemd-analyze verify /etc/systemd/system/single443-acme.service /etc/systemd/system/single443-acme.timer
  fi
  install -D -m 755 "$ROOT/lib/renew-hook.sh" "$config_dir/renewal-hooks/deploy/single443"
  if [[ $config_dir == /etc/single443/acme ]]; then
    systemctl daemon-reload
    systemctl enable --now single443-acme.timer
    systemctl is-active --quiet single443-acme.timer
  else
    systemctl enable --now certbot.timer
  fi
}
restore_ip_renewal() {
  if [[ ${IP_RENEW_CHANGED:-no} == yes ]]; then
    systemctl daemon-reload
    if [[ $IP_RENEW_WAS_ENABLED == yes ]]; then systemctl enable single443-acme.timer; else systemctl disable single443-acme.timer 2>/dev/null || true; fi
    if [[ $IP_RENEW_WAS_ACTIVE == yes ]]; then systemctl start single443-acme.timer; fi
  fi
}
