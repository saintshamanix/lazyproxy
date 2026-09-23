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

## Automatic maintenance

Installation and updates enable a persistent systemd timer. It checks hourly and runs cleanup after 72 hours since the last successful run; the first cleanup is due three days after installation. Missed cleanup is picked up after boot. Installation and cleanup share a lock.

Cleanup truncates only nginx `access.log` and `error.log` (archives are preserved), rotates the journal and vacuums archived entries with `--vacuum-time=1d --vacuum-size=10M`, then runs `apt-get clean`. Active journal files may keep total disk usage above 10M. This does not impose a continuous disk-usage cap between runs.

Package removal is opt-in: set `AUTO_REMOVE=yes` in `/etc/single443/maintenance.env` to additionally run `apt-get autoremove --purge -y`. Reruns preserve this setting. Failures leave the success timestamp unchanged and retry on the next hourly tick; partial cleanup cannot be undone.

- Status: `systemctl list-timers single443-maintenance.timer`
- Logs: `journalctl -u single443-maintenance.service`
- Run now: `sudo /usr/local/libexec/single443-maintenance --force`
- Disable: `sudo systemctl disable --now single443-maintenance.timer` (installer reruns enable it again).
