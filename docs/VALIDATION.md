# Validation

Recorded results as of 2026-09-22. Each result applies to the stated revision and environment.

## Ubuntu CI

[Run 35711410182](https://github.com/saintshamanix/lazyproxy/actions/runs/35711410182) completed successfully for Ubuntu 24.04 and 26.04 at commit `49ed4aa39c2e8c6f4cb15eaad78ff86b43f0855b`.

| Ubuntu 26.04.1 LTS environment | Version |
|---|---|
| Architecture | amd64 |
| Python | 3.14.4 |
| nginx | 1.28.3 |
| Certbot | 4.0.0 |
| nftables | 1.1.6 |
| systemd | 259.5 |

Passed checks:

- Installation of all installer dependencies.
- 22 unit tests, Bash syntax and ShellCheck.
- Isolated nftables policy and repeated-application checks.
- Rendered nginx configuration validation with real `nginx -t`.
- Upstream 3.8.5 AmneziaWG API creation, key preservation on rerun, client export and UDP listener checks.

This run did not validate a complete `install.sh` deployment, systemd lifecycle, live ACME issuance, arm64 support or external VPN handshakes.

## Historical local checks — candidate 0.1.1

Environment: Darwin/arm64, 2026-09-22. No Ubuntu VPS was available for this local run.

| Check | Recorded result |
|---|---|
| Bash syntax | All 12 shell scripts passed `bash -n`. |
| ShellCheck | Version 0.11.0 passed at warning severity; exclusions are listed below. |
| Python regression tests | All 12 tests passed. |
| Xray configuration | Xray 26.9.9, revision `52a412d`, reported `Configuration OK` for five generated inbounds. |
| Manual shell review | Reviewed quoting, argument rejection, checked curl calls, secret handling, locking and rollback paths. |

ShellCheck exclusions:

- `SC1090` / `SC1091`: dynamic source paths and system `os-release`.
- `SC2034`: configuration variables consumed by other modules or Python through the environment.
- No other warnings or errors were suppressed.

Regression coverage included nonstandard SQLite tables and column ordering, read-only access, ambiguous or unknown schemas, arbitrary port/path/Host rendering, TLS SNI and CA verification, incomplete TLS pairs, path injection and collisions, external-port validation, HTML profile rejection and Base64 subscription decoding.

The manual review also covered the absence of database text execution through `eval`/`source`, `umask`, root-only state, `flock`, ERR/INT/TERM rollback, `nginx -t` before reload, secret preservation on rerun and the absence of direct SQL writes.

Xray fixtures used a temporary certificate and generated X25519 keys. Fixture conversion removed panel-only `externalProxy` and client settings to match upstream configuration generation. Xray warned about REALITY listening on an internal port and deprecated WS/gRPC/Trojan transports; the external dispatcher still accepts TCP/443.

Linux nginx, nftables and systemd checks were not executed on Darwin. The firewall namespace test was added to CI for rule validation, repeated application and exact allowed-port sets. The later Ubuntu run above provides the recorded Linux nginx and nftables results.

## Acceptance checks still required

- Complete Ubuntu installation, systemd lifecycle and rollback under failure.
- Initial Let's Encrypt issuance and renewal for both generated domains on the target VPS; DNS availability depends on the zone owner.
- Authenticated external client connections, throughput, large uploads and external UDP reachability.
- Import and routing behavior in the target INCY, Clash and Mihomo versions.
- Separate Ubuntu 26.04 arm64 qualification.

The original source review covered upstream v3.7.0 and v3.8.5, not every patch release in those families. The six-inbound adapter requires 3.8.5; see [upstream references](UPSTREAM.md).

## Evidence boundaries

- TCP connectivity and UDP listeners do not establish an authenticated protocol handshake.
- Empty routing placeholders do not establish a usable routing policy. The supplied INCY profile also requires client-side import and routing checks.
- Temporary certificates and test secrets are not included in the distribution.
- CI results establish only the checks executed at the linked revision; they do not establish full VPS acceptance.
