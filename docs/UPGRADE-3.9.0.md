# Upgrade to 3x-ui 3.9.0 through the panel

[Русский](UPGRADE-3.9.0.ru.md)

Update one single-IP server first. Upgrade the two-IP server after client acceptance.
LazyProxy does not perform this panel upgrade: use the upstream web panel's update
control, select stable 3.9.0 and check the offered version before confirming.
If a newer version is offered, it is outside this adapter's compatibility boundary.

## Before the update

- Take a provider snapshot (preferably with the VPS stopped) and download a panel
  database backup. Retain the old panel/core binaries and database as a matched pair.
- Include `/etc/x-ui`, `/usr/local/x-ui`, `/etc/single443`, `/opt/single443`, nginx,
  Netplan, certificates and systemd units/drop-ins in the recovery copy. A database
  export alone cannot restore the reverse proxy or the secondary-IP boot dependency.
- Record inbound IDs, client counts, public subscription URLs, custom routing and
  the exact listener addresses. Keep credentials/backups private.
- Do not run LazyProxy installation/update concurrently with the panel updater.

## During the update

Connections will be interrupted while x-ui restarts. The upstream updater may
ask about a missing panel certificate: TLS is deliberately terminated by nginx.
If offered, choose **Skip SSL / behind reverse proxy**, retaining the panel's
`127.0.0.1:2053` binding and existing base path. Do not request a new certificate
or change the panel port. If the web updater cannot complete an interactive prompt,
inspect its status/log from SSH; do not repeatedly start another update.
Continue using the original public HTTPS URL, not a printed internal HTTP URL.

3.9.0 migrates the database and WireGuard outbound configuration automatically.
A failed migration is not resolved by running an old binary against the migrated
DB: restore the pre-upgrade snapshot or the matching binary/database backup.
Do not enable weekly renewals before verifying all nodes if you use a cluster.

## One IP versus two IPs

| Topology | Hysteria2 | AmneziaWG |
|---|---|---|
| One public IP | UDP/443 | UDP/51820 |
| Two public IPv4s | primary IPv4:443/UDP | secondary IPv4:443/UDP |

Existing Netplan, nginx, nftables and `single443-addresses.conf` stay in place.
Do not rerun `attach-secondary-ip.sh` on an already migrated server. Neither
UDP/443 listener may become wildcard in the two-IP topology. An empty AWG inbound
may legitimately have no socket until a peer is added.

## After the update

```bash
sudo /usr/local/x-ui/x-ui -v
sudo systemctl is-active x-ui nginx single443-firewall
ip -br address
sudo ss -lnup
sudo nginx -t
sudo nft list table inet single443
sudo systemctl cat x-ui
sudo journalctl -u x-ui --since "10 minutes ago" --no-pager
```

Verify panel login, client identities, subscription refresh, real traffic through
all used protocols, WARP/other custom outbounds, and both UDP endpoints from an
external network. A latency indicator or a listening socket is not an authenticated
handshake test. Confirm WARP's `streamSettings.sockopt.domainStrategy` after migration
if the host has no usable IPv6 route; preserve tunnel addresses and keys.

The panel update does not update `/opt/single443`. If you later want to refresh
LazyProxy-managed components, use the **current repository's** `--update-only`
command in the README, not an old pinned copy. It reads the actual panel binary
version and synchronizes installer state inside its backup/rollback transaction.
It preserves the secondary IP and does not upgrade/downgrade panel binaries.
This refresh is optional and also refreshes the managed site/routing assets.

## Compatibility changes

`inbounds/update` now preserves stored clients and inbound enable status. LazyProxy
uses the client API for its legacy subscription migration; regular inbound updates
only adjust transport/display/address fields. Existing peer ranges that overlap
may prevent AWG edits in 3.9.0; correct individual peer ranges deliberately, without
replacing outbound WireGuard `allowedIPs` defaults with peer-assignment ranges.

Sources: [3.9.0 release](https://github.com/MHSanaei/3x-ui/releases/tag/v3.9.0),
[updater](https://github.com/MHSanaei/3x-ui/blob/v3.9.0/update.sh),
[inbound service](https://github.com/MHSanaei/3x-ui/blob/v3.9.0/internal/web/service/inbound.go).
