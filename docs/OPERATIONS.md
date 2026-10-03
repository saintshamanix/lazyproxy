# Configuration and operations

[README](../README.md) · [Русский](OPERATIONS.ru.md)

## Domains and IP TLS

| Mode | Requirements |
|---|---|
| Automatic domains | `IP.cdn-one.org` and `hyphenated-IP.cdn-one.org` resolve to the VPS |
| Own domains | Supply both `--domain` and `--reality-domain`; distinct names, direct A records, no CDN proxy, AAAA or CNAME |
| IP TLS | `--ip-tls` on a fresh VPS; incompatible with own-domain options |

Use bare DNS names (Punycode for internationalized names). TCP/80 must remain reachable for ACME.
A root-owned `--config /root/lazyproxy.env` may supply the same settings; its values override CLI options.
See [config.example.env](../config.example.env), including its panel-version setting.

Reruns preserve saved domains and TLS mode. Changing the primary IP, domains or TLS mode requires a separate migration.

IP TLS uses the public IPv4 for web services and TLS proxy endpoints, but retains an automatic REALITY DNS name.
The certificate contains both IP and DNS SANs; verification remains enabled.
IP certificates use the `shortlived` profile (160 hours). Isolated Certbot 5.8.0 lives in
`/opt/single443-certbot-5.8.0`, with ACME state in `/etc/single443/acme`.

`single443-acme.timer` checks every six hours. Renewal validates/reloads nginx and restarts x-ui for Hysteria2;
failed reloads are retried on the next successful check. Diagnostics require at least 24 hours remaining.

```bash
sudo systemctl list-timers single443-acme.timer
sudo journalctl -u single443-acme.service --no-pager -n 50
```

Sources: [Let's Encrypt IP certificates](https://letsencrypt.org/2026/01/15/6day-and-ip-general-availability/),
[Certbot support](https://letsencrypt.org/2026/03/11/shorter-certs-certbot/).

## Second IPv4

First configure the additional public IPv4 persistently in Ubuntu and verify reachability.
Then, from an extracted current LazyProxy checkout:

```bash
sudo bash attach-secondary-ip.sh SECOND_IPV4
```

The script backs up the configuration, binds Hysteria2 to IP1:443/UDP and AmneziaWG to IP2:443/UDP,
closes UDP/51820 and restarts the panel. Clients, keys and routing are preserved; failures trigger rollback.
Both UDP listeners become IPv4-only. UFW must remain inactive.

Download fresh AWG configurations and verify both protocols externally.
IP2 changes the entry point, not outbound routing or the egress IP.
Subsequent updates retain the split; do not reattach IP2 after a panel upgrade.

## LazyProxy update

To refresh managed components, use the [README bootstrap](../README.md#install), replacing only its final invocation with:

```bash
bash "$f" --update-only
```

This uses the current repository, backs up configuration and refreshes managed components, including site/routing assets.
It detects the running panel version; it does not upgrade or downgrade 3x-ui.
For the panel itself, use the [panel upgrade procedure](UPGRADE-3.9.0.md).

Custom client names and limits are preserved. Legacy `single443-*` names migrate to `UserN`.
Missing/ambiguous managed identities or incompatible manual changes stop the update.
If XHTTP mode was changed manually, restore `stream-up` first.
Wait for `Updated.`, then refresh client subscriptions.

## Diagnostics and limits

```bash
sudo bash /opt/single443/diagnose.sh
sudo nginx -t
sudo journalctl -u x-ui --since "10 minutes ago" --no-pager
```

- Logs: `/var/log/single443/install.log`; backups: `/var/backups/single443/`.
- XHTTP upstream: `grpc_pass grpc://127.0.0.1:10002;`. No nginx HTTP/3 in this setup.
- An enabled AWG inbound without peers may have no UDP socket.
- AWG `vpn://` import in Shadowrocket is not guaranteed. Legacy native exports use `/etc/single443/User6-AmneziaWG.conf`.
- Client IP limits default to `0`. Enforcing them behind nginx requires real-IP forwarding; Fail2ban alone is insufficient.
- INCY profiles need client-side validation; Clash/Mihomo placeholders are not a complete routing policy.
- WS/gRPC remain available; upstream deprecation warnings are retained.

## Maintenance

An hourly timer runs cleanup 72 hours after the last successful run, including after downtime.
It truncates active nginx logs (preserving archives), rotates/vacuums the journal
(`--vacuum-time=1d --vacuum-size=10M`) and runs `apt-get clean`.
Active journal files may exceed 10 MiB; this is not a continuous size cap.

Package removal is off by default. `AUTO_REMOVE=yes` in `/etc/single443/maintenance.env`
enables `apt-get autoremove --purge -y`. Failed cleanup retries hourly; completed cleanup cannot be rolled back.

```bash
systemctl list-timers single443-maintenance.timer
journalctl -u single443-maintenance.service
```
