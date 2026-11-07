# LazyProxy

**English** · [Русский](README.ru.md)

LazyProxy installs 3x-ui on a fresh Ubuntu VPS and sets up nginx, TLS certificates, subscriptions and firewall rules. Once installed, you can manage clients and connections in the panel.

The installer sets up VLESS (REALITY, WS, XHTTP), Trojan (gRPC and WS), Hysteria2 and AmneziaWG. It also adds MASQUE with 3x-ui 3.10.0 or later. The initial client, `User1`, has access to REALITY only. To use another connection, assign a client to it in the panel.

## Install

Use Ubuntu 22.04, 24.04 or 26.04 (amd64 or arm64) with systemd and a public IPv4 address. Leave UFW disabled: LazyProxy manages nftables. In your provider’s firewall, allow TCP 22, 80, 443 and UDP 443, 51820 on the primary address.

Run this on the VPS to install the latest stable release of 3x-ui:

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
bash "$f" --version latest
BASH
```

Panel URL, username and password: `sudo cat /etc/single443/access.txt`.

## Using two IPv4 addresses

Install LazyProxy on the primary address, then [attach the second IPv4 address](docs/OPERATIONS.md#second-ipv4). Only the UDP connections change:

| | One IPv4 address | After attaching a second address |
|---|---|---|
| Hysteria2 | IP1:443 | IP1:443 |
| AmneziaWG | IP1:51820 | IP2:443 |

Allow UDP/443 on both addresses. Once AmneziaWG moves to the second address, UDP/51820 is no longer needed. Trojan WS continues to use TCP/443 through nginx.

Update 3x-ui from the panel. For custom domains, LazyProxy updates and diagnostics, see the [operations guide](docs/OPERATIONS.md).

[MASQUE](docs/MASQUE.md) · [Validation](docs/VALIDATION.md) · [Changelog](CHANGELOG.md) · [MIT license](LICENSE) · [Third-party notices](THIRD_PARTY.md)
