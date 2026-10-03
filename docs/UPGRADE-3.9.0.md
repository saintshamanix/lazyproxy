# Upgrade to 3x-ui 3.9.0

[README](../README.md) · [Русский](UPGRADE-3.9.0.ru.md)

**Use the panel's update control.** No LazyProxy reinstall or second-IP reattachment is needed.
[Validation scope](VALIDATION.md).

## Procedure

1. Take a VPS snapshot and download a panel database backup. A database backup alone does not include nginx, certificates, Netplan or systemd settings.
2. Select **3.9.0** in the panel updater and wait for completion. Do not run LazyProxy concurrently. Connections pause during the restart.
3. Open the original HTTPS URL. Verify the panel version, subscriptions and real traffic through each used protocol and custom outbound.
4. On a two-IP VPS, verify both UDP endpoints below. Keep existing Netplan and the x-ui address dependency.

| Topology | Hysteria2 | AmneziaWG |
|---|---|---|
| One IP | IP1:443/UDP | IP1:51820/UDP |
| Two IPv4s | IP1:443/UDP | IP2:443/UDP |

In the two-IP topology neither UDP/443 listener may bind to all addresses.
An empty AWG inbound may have no socket until a peer is added.

## If the update needs attention

- If asked about panel SSL, choose **Skip SSL / behind reverse proxy**. Keep `127.0.0.1:2053`, the existing base path and TLS on nginx.
- If an interactive prompt blocks the web updater, inspect logs over SSH before retrying.
- 3.9.0 migrates the database and WireGuard outbound settings. Roll back with the snapshot or matching old binaries **and** database.
- With WARP on an IPv4-only host, verify `streamSettings.sockopt.domainStrategy` after migration and test real traffic.
- Overlapping AWG peer ranges can prevent edits; correct peer assignments, not outbound WireGuard default routes.
- Update all cluster nodes before enabling weekly renewals.

```bash
sudo /usr/local/x-ui/x-ui -v
sudo systemctl is-active x-ui nginx single443-firewall
sudo ss -lnup
sudo nginx -t
sudo journalctl -u x-ui --since "10 minutes ago" --no-pager
```

Updating the panel leaves `/opt/single443` unchanged.
A later [LazyProxy refresh](OPERATIONS.md#lazyproxy-update) is optional and must use the current repository.

Sources: [release](https://github.com/MHSanaei/3x-ui/releases/tag/v3.9.0),
[updater](https://github.com/MHSanaei/3x-ui/blob/v3.9.0/update.sh).
