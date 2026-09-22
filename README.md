# LazyProxy

Automate deployment. Preserve upstream.

Automated deployment and configuration of upstream 3x-ui and Xray on a clean Ubuntu VPS, without forking or modifying the panel.

## Components

* 3x-ui and Xray-core
* Nginx and Let's Encrypt (Certbot)
* VLESS REALITY, WebSocket and XHTTP (`stream-up`)
* Trojan gRPC, Hysteria2 and AmneziaWG
* nftables and Fail2ban

## Capabilities

* Automatic domains, TLS certificates and decoy website
* Inbound configuration and independent client subscriptions
* INCY routing profile and Clash/Mihomo subscription endpoints
* Firewall configuration and kernel TCP BBR when supported
* Repeatable installation, diagnostics, backups and rollback on failure

## Installation

Replace `<USER>/<REPOSITORY>` and run as root:

```bash
export INSTALLER_REPO="<USER>/<REPOSITORY>" INSTALLER_REF="main"
bash <(curl -fsSL "https://raw.githubusercontent.com/$INSTALLER_REPO/$INSTALLER_REF/install.sh") --version 3.8.5
```

## Requirements

* Clean Ubuntu Server 22.04, 24.04 or 26.04; amd64 or arm64; systemd
* Root access, curl, Python 3 and CA certificates for bootstrap
* Public IPv4 and both generated domain names resolving to the VPS
* Inbound TCP 22/80/443 and UDP 443/51820; outbound HTTPS access
* Upstream 3x-ui 3.8.5 for the six-inbound adapter

## License

Not yet specified; see [LICENSE](LICENSE). Upstream components retain their own licenses.
