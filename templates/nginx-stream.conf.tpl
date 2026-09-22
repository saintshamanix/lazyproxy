# Included at nginx main context, outside http {}.
stream {
    map $ssl_preread_server_name $single443_backend {
        @REALITY_DOMAIN@ 127.0.0.1:8443;
        default 127.0.0.1:7443;
    }
    server {
        listen 443;
        ssl_preread on;
        proxy_connect_timeout 10s;
        proxy_timeout 1h;
        proxy_pass $single443_backend;
    }
}
