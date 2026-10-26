# Validation

Results apply to the stated revision and environment, not every VPS or client.

## Deployment check — 2026-10-26

The panel-driven upgrade to 3.11.0 completed with existing connectivity preserved. This operational result does not establish a clean-install test, kernel AmneziaWG support, independently measured Xray version or MASQUE client interoperability.

## Current automated baseline — 2026-10-26

[CI run 40263754685](https://github.com/saintshamanix/lazyproxy/actions/runs/40263754685) at `ab52c5933df99bfd2248003e28d73e0374d331c0`: **all ten jobs passed**.

The matrix covers 3.8.5, 3.9.0, 3.10.0, 3.10.2 and 3.11.0 on Ubuntu 24.04/26.04. Both 3.11.0 jobs passed embedded AmneziaWG API/listener checks, MASQUE API/JSON export and authenticated TCP/UDP through nginx/SNI, and authenticated XHTTP transfers. Local regression: 58 tests, one platform-conditional skip. These checks do not establish a full public-VPS clean installation, kernel AmneziaWG operation or Shadowrocket interoperability.

## Earlier deployment check — 2026-10-14

Panel-driven upgrades to 3.10.2 completed on all deployed servers; existing connections remained operational across one- and two-IP deployments. This does not establish MASQUE client interoperability or a clean-install test of 3.10.2.

## Earlier automated baseline — 2026-10-14

[CI run 38625797749](https://github.com/saintshamanix/lazyproxy/actions/runs/38625797749) at `5c284645b5210784186359072d247b69190dd7d0`: **all eight jobs passed**.

The matrix covers 3.8.5, 3.9.0, 3.10.0 and 3.10.2 on Ubuntu 24.04/26.04. Both 3.10.x versions run the MASQUE API, JSON export and authenticated TCP/UDP test through nginx/SNI. Local regression: 58 tests, one platform-conditional skip. These checks do not validate Shadowrocket interoperability.

## Earlier automated baseline — 2026-10-12

[CI run 38295056533](https://github.com/saintshamanix/lazyproxy/actions/runs/38295056533)
at `66c78b325b77671ad21424252f0f64f19b77675d`: **all six jobs passed**.

| Dimension | Coverage |
|---|---|
| OS / architecture | Ubuntu 24.04 and 26.04, amd64 |
| Panel | 3x-ui 3.8.5, 3.9.0 and 3.10.0 |
| Static/configuration | Bash, ShellCheck, Python, nginx, Xray |
| Firewall | Isolated nftables policies and repeated application |
| Panel API | Fresh creation, reruns, single REALITY client, AWG export/key preservation |
| Two IPs | Hysteria2/AWG UDP bindings and export preservation after migration |
| MASQUE (3.10.0) | Real migration API and rerun, existing credentials retained, JSON export, authenticated TLS/SNI/h2 with 2 MiB each direction and UDP echo |
| XHTTP | Authenticated TLS/SNI transfers, 2 MiB each direction, all three modes |

Local regression: 57 tests, one platform-conditional skip.
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

[Upstream references](UPSTREAM.md) · [Upgrade procedure](UPGRADE-3.11.0.md)
