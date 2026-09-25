server {
    listen 80;
    server_name @DOMAIN@ @REALITY_DOMAIN@;
    location ^~ /.well-known/acme-challenge/ { root /var/www/single443; }
    location / { return 301 https://@DOMAIN@$request_uri; }
}
server {
    listen 127.0.0.1:7443 ssl http2;
    server_name @DOMAIN@ @REALITY_DOMAIN@;
    ssl_certificate @CERT_DIR@fullchain.pem;
    ssl_certificate_key @CERT_DIR@privkey.pem;
    ssl_protocols TLSv1.2 TLSv1.3;
    root /var/www/single443;
    index index.html;
    server_tokens off;
    # Never log secret panel/subscription paths.
    access_log off;
    client_max_body_size 0;
    location / { try_files $uri $uri/ =404; }
    location ^~ @PANEL_PATH@ {
        proxy_pass http://127.0.0.1:2053;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Forwarded-Host $host;
        proxy_set_header X-Forwarded-Proto https;
        proxy_set_header X-Forwarded-For $remote_addr;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_read_timeout 1h;
    }
    location = @WS_PATH@ {
        proxy_pass http://127.0.0.1:10001;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_read_timeout 1h;
    }
    location ^~ @XHTTP_PATH@ {
        # Preserve HTTP/2 streaming to Xray (including stream-up uploads).
        grpc_pass grpc://127.0.0.1:10002;
        grpc_set_header Host $host;
        client_body_timeout 1h;
        grpc_read_timeout 1h;
        grpc_send_timeout 1h;
    }
    location ^~ /@GRPC_SERVICE@/ {
        grpc_pass grpc://127.0.0.1:10003;
        grpc_set_header Host $host;
        grpc_read_timeout 1h;
        grpc_send_timeout 1h;
    }
@SUB_LOCATIONS@
}
