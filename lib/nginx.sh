#!/usr/bin/env bash
set -Eeuo pipefail
install_acme_web() {
  mkdir -p /var/www/single443/.well-known/acme-challenge /var/www/single443/routing
  chmod 755 /var/www/single443 /var/www/single443/.well-known /var/www/single443/.well-known/acme-challenge /var/www/single443/routing
  install -m 644 "$ROOT/templates/decoy/index.html" /var/www/single443/index.html
  if [[ ! -f /etc/nginx/conf.d/single443-web.conf ]]; then
    rm -f /etc/nginx/sites-enabled/default
    cat > /etc/nginx/conf.d/single443-acme.conf <<'EOF'
server {
    listen 80;
    server_name _;
    location ^~ /.well-known/acme-challenge/ { root /var/www/single443; }
    location / { return 404; }
}
EOF
    activate_nginx
  fi
}
render_nginx() { helper render "$ROOT/templates"; }
activate_nginx() {
  nginx -t
  if systemctl is-active --quiet nginx; then systemctl reload nginx; else systemctl start nginx; fi
  systemctl enable nginx
}
