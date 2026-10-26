# Upgrade to 3x-ui 3.11.0

[README](../README.md) · [Русский](UPGRADE-3.11.0.ru.md)

For existing LazyProxy servers running 3.10.2, with one or two public IPs.

1. Save a current panel backup off the VPS; retain a VPS snapshot for full rollback.
2. Connect through another server or a direct SSH path. Select **3.11.0** in the panel updater and wait for completion.
3. Verify both the panel version and the running Xray version. This release bundles **Xray 26.10.21**, an upstream security update replacing withdrawn 26.10.10/26.10.17 releases.
4. Keep the existing embedded AmneziaWG mode for this upgrade. The new optional Linux kernel mode is NAT-only and requires separate routing/firewall validation; it is not covered by LazyProxy's embedded-AWG checks.
5. Refresh subscriptions, check public endpoint addresses/ports and transfer real traffic through the protocols in use. On two-IP servers, also check the secondary-IP AWG endpoint. If INCY/Happ routing is enabled, check each app's intended profile.

Do not rerun the installer, reattach IP2 or rerun `add-masque.sh` for this panel update. A LazyProxy component update is a separate operation.

The release improves embedded AmneziaWG uploads and synchronizes imported Hosts when External Proxy changes. This release does not establish Shadowrocket interoperability: Xray 26.10.21 still authenticates inbound MASQUE through HTTP Basic credentials. Keep client compatibility separate from successful inbound creation.

For rollback, restore a matching panel/database/core snapshot. Do not treat withdrawn Xray builds as a recommended steady-state fallback. Older LazyProxy backups represent the state before their respective script runs.

[Panel release](https://github.com/MHSanaei/3x-ui/releases/tag/v3.11.0) · [Changes](https://github.com/MHSanaei/3x-ui/compare/v3.10.2...v3.11.0) · [Xray security release](https://github.com/XTLS/Xray-core/releases/tag/v26.10.21) · [MASQUE authentication](https://github.com/XTLS/Xray-core/blob/v26.10.21/proxy/masque/server.go)
