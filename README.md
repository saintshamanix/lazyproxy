# LazyProxy

**English** · [Русский](README.ru.md)

Automatic deployment of **upstream 3x-ui behind an nginx reverse proxy** on Ubuntu VPS.
No panel fork: LazyProxy installs and configures the components; client management
stays in the original 3x-ui panel.

## Architecture

```text
Internet
├── TCP/80  → nginx: ACME HTTP-01 and HTTPS redirect
├── TCP/443 → nginx stream: ssl_preread / SNI dispatcher
│   ├── REALITY SNI → Xray 127.0.0.1:8443
│   └── WEB SNI     → nginx HTTPS 127.0.0.1:7443
│       ├── /                 → neutral website with JavaScript
│       ├── secret path       → panel 127.0.0.1:2053
│       ├── subscription path → discovered subscription backend
│       ├── WS path           → Xray 127.0.0.1:10001
│       ├── XHTTP path        → Xray 127.0.0.1:10002 (HTTP/2)
│       └── gRPC service      → Xray 127.0.0.1:10003 (HTTP/2)
├── UDP/443   → Hysteria2
└── UDP/51820 → AmneziaWG
```

**nginx terminates TLS for the website, panel, subscriptions, WS, XHTTP and gRPC.**
The nginx → Xray connection for WS/XHTTP/gRPC uses loopback without TLS.
“Security: None” for these panel inbounds is therefore expected; clients connect
using TLS on external port 443.

REALITY passes through the SNI dispatcher without TLS termination in nginx stream.
Hysteria2 uses UDP/443 directly. AmneziaWG requires a separate UDP/51820 port,
which is an exception to the shared port 443 architecture.

XHTTP uses `grpc_pass` over HTTP/2. The directive name does not change the inbound
protocol: it remains VLESS XHTTP. Clients need ALPN `h2`; nginx does not serve
HTTP/3 in this setup. The default mode is `stream-up`.

## Features

- Public IPv4 detection and automatic `IP.cdn-one.org` / `hyphenated-IP.cdn-one.org` domains.
- Let's Encrypt through Certbot, automatic renewal and a deploy hook.
- VLESS REALITY, VLESS WS, VLESS XHTTP, Trojan gRPC, Hysteria2 and AmneziaWG.
- Inbound names: country flag and protocol. New clients: `User1`–`User6`.
- Independent subscriptions with the profile title **Casper area**.
- Subscription reverse proxy with current settings discovered through the API and read-only SQLite.
- INCY routing, Clash/Mihomo endpoints and static routing files.
- nftables, compatibility with stock Fail2ban SSH protection and kernel TCP BBR when supported.
- Unlimited client IPs by default (`limitIp=0`); existing custom limits are preserved.
- Backups, configuration validation, rollback on failure and log maintenance.

## Requirements and verified versions

Ubuntu Server 22.04, 24.04 or 26.04, systemd, root access, amd64 or arm64.
Bootstrap requires curl, Python 3 and CA certificates.

The six-protocol adapter is pinned to **3x-ui 3.8.5**. A `latest` mode exists,
but unsupported versions are rejected; use the version pin below for reproducible installation.

Both automatic domain names must resolve to the VPS IP. Availability of
`cdn-one.org` depends on its operator. The provider's external firewall must allow:

| Transport | Ports | Purpose |
|---|---|---|
| TCP | 22, 80, 443 | SSH, ACME/HTTP, HTTPS and proxy traffic |
| UDP | 443, 51820 | Hysteria2, AmneziaWG |

The installer manages the local firewall. Unknown active policies stop installation;
they are not flushed automatically. A verified SSH-only chain from the stock
Fail2ban `sshd` jail is accepted and preserved.

## Fresh installation

On a prepared Ubuntu VPS:

```bash
sudo bash -c 'set -Eeuo pipefail; export INSTALLER_REPO=saintshamanix/lazyproxy INSTALLER_REF=main; f=$(mktemp); trap '\''rm -f "$f"'\'' EXIT; curl -fLsS --retry 3 "https://raw.githubusercontent.com/$INSTALLER_REPO/$INSTALLER_REF/install.sh" -o "$f"; bash "$f" --version 3.8.5'
```

To pin LazyProxy itself, replace `INSTALLER_REF=main` with a commit SHA.
See [config.example.env](config.example.env) for configuration options.

After successful installation:

```bash
sudo cat /etc/single443/access.txt
```

This file contains secret credentials. Do not publish it.

## Updating an existing installation

Update the installer-managed components without upgrading the panel version:

```bash
sudo bash -c 'set -Eeuo pipefail; export INSTALLER_REPO=saintshamanix/lazyproxy INSTALLER_REF=main; f=$(mktemp); trap '\''rm -f "$f"'\'' EXIT; curl -fLsS --retry 3 "https://raw.githubusercontent.com/$INSTALLER_REPO/$INSTALLER_REF/install.sh" -o "$f"; bash "$f" --update-only'
```

Custom client names are preserved. Only legacy installer names `single443-*`
are migrated to `UserN`. Clients are identified by their saved inbound ID and
`subId`; a missing or ambiguous identity stops the update. Modified paths, keys
and topology are not overwritten blindly. If you manually changed the XHTTP mode,
restore `stream-up` before running a full update.

Errors may trigger rollback, so starting the command does not mean it succeeded.
Wait for the final `Updated.` message, then refresh the subscription in your client.

## Diagnostics

```bash
sudo bash /opt/single443/diagnose.sh
sudo nginx -t
sudo nginx -T 2>/dev/null | grep -E '(grpc_pass|proxy_pass).*10002'
```

XHTTP should use `grpc_pass grpc://127.0.0.1:10002;`.
Installation log: `/var/log/single443/install.log`.
Backups: `/var/backups/single443/`.

CI on Ubuntu 24.04/26.04 amd64 checks Bash, ShellCheck, Python, nginx, isolated
nftables, the real 3x-ui 3.8.5 API, and 2 MiB transfers in both directions through
VLESS XHTTP + TLS + SNI dispatcher in all three modes.
These checks do not replace external tests of a particular VPS and client application.
Ubuntu 22.04 and arm64 are not covered by this CI matrix.

## Clients and limitations

- WS and gRPC remain available for compatibility; Xray deprecation warnings are not hidden.
- A UDP listener check does not prove external UDP reachability or a successful VPN handshake.
- Compatibility of AmneziaWG `vpn://` exports with Shadowrocket is not guaranteed.
  A separate configuration is saved to `/etc/single443/User6-AmneziaWG.conf`;
  the filename stays the same even after a client is renamed.
- A nonzero IP Limit behind nginx requires correct forwarding of the real client IP;
  installing Fail2ban alone is insufficient.
- Static Clash/Mihomo placeholders are not a complete user routing policy.

## Automatic cleanup

A persistent systemd timer checks hourly and runs cleanup 72 hours after the last
successful run. The first cleanup is due three days after installation.
Missed cleanup runs after the server starts.

Cleanup truncates active nginx `access.log` and `error.log` files while preserving
archives, rotates the journal, vacuums it with `--vacuum-time=1d --vacuum-size=10M`,
and runs `apt-get clean`. Active journal files can exceed 10 MiB;
this is not a continuous disk usage cap.

Package removal is disabled by default. Set `AUTO_REMOVE=yes` in
`/etc/single443/maintenance.env` to enable `apt-get autoremove --purge -y`.
Updates preserve this setting. Failed cleanup is retried on the next hourly check;
cleanup already performed cannot be rolled back.

```bash
systemctl list-timers single443-maintenance.timer
journalctl -u single443-maintenance.service
sudo /usr/local/libexec/single443-maintenance --force
```

## Upstream and license

- [MHSanaei/3x-ui](https://github.com/MHSanaei/3x-ui)
- [XTLS/Xray-core](https://github.com/XTLS/Xray-core)
- [XTLS XHTTP reverse proxy example](https://github.com/XTLS/Xray-examples/blob/main/VLESS-XHTTP3-Nginx/nginx.conf)
- [nginx gRPC module](https://nginx.org/en/docs/http/ngx_http_grpc_module.html)

[CHANGELOG](CHANGELOG.md) · [Validation](docs/VALIDATION.md) · [Upstream](docs/UPSTREAM.md)

A license for LazyProxy has not been selected yet: [LICENSE](LICENSE).
Upstream components retain their own licenses.
