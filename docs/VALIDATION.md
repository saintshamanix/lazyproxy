# Validation

Results apply to the stated revision and environment, not every VPS or client.

## Current automated baseline — 2026-10-03

[CI run 37122851068](https://github.com/saintshamanix/lazyproxy/actions/runs/37122851068)
at `b001c1814b9ad0cd3674dbca546eb62d0ed41b6d`: **all four jobs passed**.

| Dimension | Coverage |
|---|---|
| OS / architecture | Ubuntu 24.04 and 26.04, amd64 |
| Panel | 3x-ui 3.8.5 and 3.9.0 |
| Static/configuration | Bash, ShellCheck, Python, nginx, Xray |
| Firewall | Isolated nftables policies and repeated application |
| Panel API | Fresh creation, reruns, single REALITY client, AWG export/key preservation |
| Two IPs | Hysteria2/AWG UDP bindings and export preservation after migration |
| XHTTP | Authenticated TLS/SNI transfers, 2 MiB each direction, all three modes |

Local regression: 51 tests, one platform-conditional skip.
Tests also cover version detection, installer-state synchronization after a panel upgrade and legacy migration through the client API.

## Not established by these checks

- Full fresh-install lifecycle, recovery under every failure and public ACME issuance/renewal.
- Universal external UDP reachability, throughput or compatibility with every client application.
- Ubuntu 22.04 or arm64 qualification in this CI matrix.
- Live IP-certificate issuance and Shadowrocket/INCY imports in IP-TLS mode; CI uses trusted test certificates.

A socket or latency indicator is not a protocol handshake.
Validate subscriptions, routing and real traffic on the target VPS after changes.

## Earlier evidence

[Run 35711410182](https://github.com/saintshamanix/lazyproxy/actions/runs/35711410182)
at `49ed4aa39c2e8c6f4cb15eaad78ff86b43f0855b` passed on Ubuntu 24.04/26.04.
Detailed historical results remain in [the previous validation record](https://github.com/saintshamanix/lazyproxy/blob/4141c5e988fec816de2cfe7545a3fe873a9556c3/docs/VALIDATION.md).

[Upstream references](UPSTREAM.md) · [Upgrade procedure](UPGRADE-3.9.0.md)
