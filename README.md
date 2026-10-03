# LazyProxy

**English** · [Русский](README.ru.md)

Deploy **3x-ui behind an nginx reverse proxy** on an Ubuntu VPS.
LazyProxy configures TLS, inbounds, subscriptions and nftables; clients are managed in the upstream panel.

**Protocols:** VLESS REALITY, VLESS WS, VLESS XHTTP, Trojan gRPC, Hysteria2 and AmneziaWG.
A fresh install creates **one client: User1 on REALITY**. Add or attach other clients in the panel.

## Architecture

```text
TCP/80  → nginx: ACME validation and HTTPS redirect
TCP/443 → nginx SNI dispatcher
          ├─ REALITY → Xray
          └─ HTTPS  → nginx TLS termination
                      ├─ website, panel and subscriptions
                      └─ WS, XHTTP and gRPC → Xray over loopback
```

| UDP topology | Hysteria2 | AmneziaWG |
|---|---|---|
| One public IP — default | IP1:443 | IP1:51820 |
| Two public IPv4s — optional | IP1:443 | IP2:443 |

With a second IP, TCP stays unchanged; UDP/51820 closes and both UDP listeners become IPv4-only.
[Setup and limitations](docs/OPERATIONS.md).

TLS terminates at nginx for web services and WS/XHTTP/gRPC; `security: none` on their internal inbounds is expected.
REALITY passes through nginx without TLS termination. XHTTP uses HTTP/2 (`grpc_pass`, ALPN `h2`), default mode `stream-up`.

## Requirements

- Ubuntu 22.04 / 24.04 / 26.04, systemd, root, amd64 or arm64.
- Public IPv4; provider firewall allows TCP **22, 80, 443** and UDP **443, 51820**.
- UFW inactive: LazyProxy manages nftables. Unknown firewall policies stop installation; verified stock Fail2ban SSH rules are preserved.
- Automatic DNS names must resolve to the VPS; their availability depends on `cdn-one.org`.

Supported panel versions: **3.9.0** (default) and **3.8.5**.
CI covers Ubuntu 24.04/26.04 amd64. [Validation](docs/VALIDATION.md).

## Install

Run on a fresh VPS:

```bash
sudo bash <<'BASH'
set -Eeuo pipefail
export INSTALLER_REPO=saintshamanix/lazyproxy
export INSTALLER_REF=main
apt-get update -q
DEBIAN_FRONTEND=noninteractive apt-get install -y curl python3 ca-certificates
f=$(mktemp)
trap 'rm -f "$f"' EXIT
curl -fLsS --retry 3 \
  "https://raw.githubusercontent.com/$INSTALLER_REPO/$INSTALLER_REF/install.sh" -o "$f"
bash "$f" --version 3.9.0
BASH
```

Replace `INSTALLER_REF=main` with a commit SHA to pin LazyProxy.
After installation, retrieve the panel URL and credentials:

```bash
sudo cat /etc/single443/access.txt
```

Keep this file private. TLS certificates renew automatically.

## Installation options

Append options to the `bash "$f" --version 3.9.0` line above.

| Option | Configuration |
|---|---|
| Automatic domains | Default; no extra arguments |
| Own domains | `--domain vpn.example.com --reality-domain reality.example.com`; two direct A records, no CDN proxy or AAAA/CNAME |
| Public IP + TLS | `--ip-tls`; fresh installation only, still uses an automatic REALITY DNS name |
| Second public IPv4 | Install normally, then [move AmneziaWG to IP2:443](docs/OPERATIONS.md#second-ipv4) |

Existing domains and TLS mode cannot be changed by rerunning the installer.
[Configuration details](docs/OPERATIONS.md) · [Configuration file](config.example.env)

## Update

**3x-ui:** use the panel's update control.
[Upgrade to 3.9.0](docs/UPGRADE-3.9.0.md) covers both IP topologies; rerunning the installer or reattaching IP2 is unnecessary.
The owner confirmed a successful panel-driven upgrade on a two-IP VPS.

**LazyProxy components:** a separate, optional `--update-only` operation.
It does not change the panel version. [Procedure](docs/OPERATIONS.md#lazyproxy-update).

## Diagnose

```bash
sudo bash /opt/single443/diagnose.sh
```

Log: `/var/log/single443/install.log` · Backups: `/var/backups/single443/`.
Check subscriptions and actual client traffic after changes; a listening port alone does not establish connectivity.

## Reference

[Operations](docs/OPERATIONS.md) · [Validation](docs/VALIDATION.md) · [Changelog](CHANGELOG.md) · [Upstream](docs/UPSTREAM.md)

[MIT](LICENSE) for LazyProxy. Downloaded components retain their own licenses: [third-party notices](THIRD_PARTY.md).
