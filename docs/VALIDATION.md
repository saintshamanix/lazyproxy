# Validation

[CI workflow](../.github/workflows/checks.yml) · [Run history](https://github.com/saintshamanix/lazyproxy/actions/workflows/checks.yml)

At revision [7aef75c](https://github.com/saintshamanix/lazyproxy/commit/7aef75cece34c00bb0f187d5d562db38ce3bbe4a), [all ten jobs passed](https://github.com/saintshamanix/lazyproxy/actions/runs/42373131643): Ubuntu 24.04 and 26.04 amd64, each with 3x-ui 3.8.5, 3.9.0, 3.10.0, 3.10.2 and 3.11.0.

The matrix exercises configuration generation, panel APIs, firewall rules and selected proxy transports. Fixture certificates and local test addresses do not validate public ACME issuance, provider firewall rules, or an iPhone connection. Ubuntu 22.04 and arm64 are outside this matrix.

For two IPv4 addresses, verify Hysteria2 traffic through IP1:443/UDP and an exported AmneziaWG peer through IP2:443/UDP. A listening socket alone does not establish authenticated connectivity. See [operations](OPERATIONS.md#second-ipv4).
