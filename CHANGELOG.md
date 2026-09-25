# Changelog

## 0.3.1

- Fresh installations create only User1 on REALITY; all other inbounds start empty.
- Access output and subscription diagnostics cover only seeded clients.
- Preserve legacy installation clients and subscriptions on updates; no automatic deletions.

## 0.3.0

- Optional fresh-install `--ip-tls`: public IPv4 URLs and IP SAN TLS; automatic REALITY DNS/SNI retained.
- Isolated Certbot 5.8.0 and ACME state, required shortlived profile, six-hour renewal checks, serialized reload with retry.
- Keep verified internal subscription TLS with DNS SAN; advertise public IP URLs.
- Mode-aware certificate lifetime check and migration refusal; default domain modes unchanged.
- Add IP SAN XHTTP transfer and renewal setup checks to Ubuntu CI.

## 0.2.9

- Add custom WEB/REALITY domain pairs via --domain/--reality-domain or WEB_DOMAIN/REALITY_DOMAIN config.
- Validate distinct DNS names and existing DNS requirements before ACME; certificates cover both names.
- Preserve saved custom domains on reruns; reject changes to either saved domain or IP.
- Keep automatic domains as the fresh-install default; document both modes in English and Russian.

## 0.2.8

- Preserve custom client names on updates; use saved inbound IDs and subIds to resolve managed identities.
- Preserve renamed AmneziaWG clients during configuration and export; keep the export filename stable.
- Retain rejection of missing/ambiguous identities and legacy-name collisions.
- Document nginx reverse proxy, TLS termination, HTTP/2 XHTTP, ports, update behavior and validation limits in the Russian README.

## 0.2.7

- Forward XHTTP from nginx to Xray over HTTP/2 using grpc_pass. The former HTTP/1.1 proxy_pass stalls stream-up traffic.
- Preserve external TLS termination, paths, credentials and default stream-up mode.
- Add authenticated VLESS/XHTTP transfer checks through the rendered TLS/SNI/nginx stack, including 2 MiB uploads/downloads and an optional legacy comparison (--legacy).

## 0.2.6

- Accept verified stock Fail2ban sshd rules restricted to TCP/22 during firewall preflight. Preserve the existing SSH ban table.
- Keep rejecting unrelated base chains, broader Fail2ban rules and unverified jails.
- Add parser unit tests and real nftables namespace coverage for SSH bans and repeated firewall application.

## 0.2.5

- Add persistent systemd maintenance, gated by 72 hours since the last successful run.
- Truncate active nginx logs, rotate/vacuum archived journal files and clean APT cache. Package autoremove/purge is opt-in.
- Preserve nginx archives and configured autoremove preference. Add shared locking, bounded APT lock wait, retry on failure and timer/config rollback.
- Test due/not-due behavior, opt-in package removal, failure handling and repeated systemd timer installation.

## 0.2.4

- Set the subscription title to `Casper area` through the upstream API on install and update; preserve inbound and client names.
- Deliver the title through `Profile-Title`. Existing profiles may require a subscription refresh or reimport.

## 0.2.3

- Enable kernel TCP BBR when available and persist the default `fq` qdisc, with rollback. Preserve existing interface qdiscs; skip unavailable BBR. UDP congestion control is unchanged.
- Configure the Fail2ban `3x-ipl` jail with nftables actions for TCP/443 and UDP/443,51820; exclude SSH.
- Default new clients to `limitIp=0`; preserve existing manual limits. IP enforcement behind nginx requires real-IP forwarding.
- Add CI coverage for jail startup, repeated configuration and synthetic ban/unban.

## 0.2.2

- Separate inbound names (country flag + protocol) from client names (`User1`–`User6`).
- Rename managed clients through the upstream API, preserving credentials, `subId` and limits. Reject naming collisions, changed identities and extra attachments.
- Save the unmodified AmneziaWG configuration to root-only `/etc/single443/User6-AmneziaWG.conf`; include it in rollback.
- Validate API rename and configuration export in Ubuntu 24.04/26.04 CI.
- Shadowrocket 2.2.92 import compatibility with upstream `vpn://` exports and AWG 3.1 parameters remains unverified; use a compatible client.

## 0.2.1

- Allow Ubuntu 26.04; extend dependency-installation CI to Ubuntu 24.04/26.04.
- Pass 22 unit tests, Bash/ShellCheck, `nginx -t`, nftables namespace checks and upstream 3.8.5 AmneziaWG API/UDP/export checks on Ubuntu 26.04.1 amd64.
- Full systemd installation, live ACME issuance and external VPN handshakes remain VPS acceptance checks. Ubuntu 26.04 arm64 was not separately tested.

## 0.2.0

- Add AmneziaWG as the sixth managed inbound through upstream 3x-ui 3.8.5, using its userspace implementation and generated keys/parameters.
- Open UDP/51820 for AmneziaWG; retain TCP/443 for VLESS/Trojan and UDP/443 for Hysteria2. Provider firewalls require a separate UDP/51820 rule.
- Require 3x-ui 3.8.5 for the six-inbound adapter; reject other versions before changing services.
- Add country flags from IP geolocation, with a generic fallback and retry. Persist inbound IDs for repeatable renaming; preserve credentials and subscriptions.
- Export AmneziaWG through its own `subId` as upstream `vpn://` configuration; omit a Mihomo URL for this inbound.
- Extend `--update-only` to update the managed firewall, rename existing inbounds and add AmneziaWG, with backup and rollback.
- Check UDP listener, export format, endpoint and repeated creation. These checks do not establish an external client handshake.

## 0.1.3

- Fix false rollback caused by treating INCY routing/autorouting URIs as proxy connections.
- Continue rejecting extra connections, unknown lines and subscriptions without a connection.
- Add raw/Base64 regression coverage for all five protocols with INCY routing.
- Reload systemd after restoring the firewall unit during rollback.

## 0.1.2

- Replace the shared subscription with five independent `subId` values; write per-client standard and Mihomo URLs to `access.txt`.
- Add `install.sh --update-only` with API migration, backup and rollback, preserving credentials. At this release, upstream, certificates and firewall remain unchanged.
- Reject migration when the original five clients or their subscriptions have been modified, or clients have been added.
- Require users to import the new subscription URLs; the old shared subscription no longer exposes these connections. Direct connection credentials remain unchanged.
- Publish the supplied Shamanix RU Direct JSON unchanged; configure INCY routing through the API when supported, otherwise retain the static endpoint.
- Add local decoy-site theme switching and note filtering without external JavaScript dependencies.
- Validate exactly one connection of the expected protocol in each subscription.

## 0.1.1 — 2026-09-22

- Add a persistent IPv4/IPv6 nftables firewall allowing inbound TCP 22/80/443 and UDP 443.
- Apply rules atomically after validation; preserve outbound, loopback, established/related and ICMP traffic. Require static addressing; no inbound DHCP exception is provided.
- Require SSH on TCP/22; reject conflicting UFW, firewalld, nftables or legacy iptables policies before applying changes.
- Add firewall backup/rollback, boot persistence and policy-drift diagnostics. Stopping the firewall unit does not remove filtering.
- Add a Linux network-namespace CI test; Linux runtime validation was not performed locally.

## 0.1.0 — 2026-09-22

- Introduce the installation candidate for Ubuntu 22.04/24.04 on amd64/arm64, using upstream 3x-ui CLI and session API with CSRF.
- Support latest or pinned upstream releases with mandatory SHA-256 verification. Checksums verify download integrity, not independent publisher authenticity.
- Initially restrict the adapter to upstream 3.7.x/3.8.x; reject unknown families. This does not establish runtime coverage of every patch release.
- Configure two automatic domains, ACME webroot certificates and five inbounds: VLESS REALITY, WebSocket, XHTTP (`stream-up`), Trojan gRPC and Hysteria2 on TCP/UDP 443.
- Discover subscriptions through the API or read-only SQLite, with Host/SNI handling and CA verification.
- Add persistent random secrets, backups, rollback, nginx/Xray validation, diagnostics, a decoy site, routing placeholders and a Mihomo alias.
- Add Bash/Python regression checks, Xray 26.9.9 configuration validation and Ubuntu nginx CI configuration. Xray reports deprecation warnings for WS, gRPC and Trojan.
- Full VPS installation and end-to-end client connections were not verified for this release.
