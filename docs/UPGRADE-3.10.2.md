# Upgrade to 3x-ui 3.10.2

[README](../README.md) · [Русский](UPGRADE-3.10.2.ru.md)

For existing LazyProxy servers running 3.10.0, with one or two public IPs.

1. Save a current panel backup off the VPS; retain a VPS snapshot for full rollback.
2. Connect through another server or a direct SSH path, then select **3.10.2** in the panel updater. Wait for completion; connections may pause during restart.
3. Check the panel and Xray status, refresh subscriptions and verify real traffic through the protocols in use. On two-IP servers, also check the AWG endpoint.
4. If INCY/Happ routing is enabled, check that each app receives its intended profile after refreshing its subscription.

Do not rerun the installer, reattach IP2 or rerun `add-masque.sh` for this panel update. A LazyProxy component update is a separate operation.

Xray remains **26.10.10**. MASQUE authentication/export limitations are unchanged; this update does not establish Shadowrocket compatibility.

For rollback, restore matching panel binaries and database, or the VPS snapshot. Older LazyProxy backups represent the state before their respective script runs.

[Release](https://github.com/MHSanaei/3x-ui/releases/tag/v3.10.2) · [Changes](https://github.com/MHSanaei/3x-ui/compare/v3.10.0...v3.10.2)
