# MASQUE

[Русский](MASQUE.ru.md) · [README](../README.md)

Fresh installs create an empty MASQUE inbound on 3x-ui 3.10.0+. No extra public IP is required.

```text
IP1:443/TCP → nginx ssl_preread → SNI masque.IP.cdn-one.org → 127.0.0.1:10004 → Xray MASQUE/TLS/h2
```

Xray terminates TLS. A separate `single443-masque` certificate renews through Certbot, with an x-ui restart after renewal. HTTP/3 is disabled because Hysteria2 occupies UDP/443. Two-IP installations retain AmneziaWG on IP2:443/UDP. MASQUE carries UDP too, but this HTTP/2 transport uses TCP and is subject to head-of-line blocking.

## Add after upgrading

For LazyProxy-managed servers only. Upgrade 3x-ui through the panel to 3.10.0 or newer first. Keep TCP/80 reachable for ACME, then run:

```bash
sudo bash <<'BASH'
set -Eeuo pipefail
ref=main
repo=saintshamanix/lazyproxy
d=$(mktemp -d)
trap 'rm -rf -- "$d"' EXIT
curl -fLsS --retry 3 "https://api.github.com/repos/$repo/commits/$ref" -o "$d/ref.json"
sha=$(python3 -c 'import json,sys; print(json.load(open(sys.argv[1]))["sha"])' "$d/ref.json")
[[ $sha =~ ^[a-f0-9]{40}$ ]]
curl -fLsS --retry 3 "https://codeload.github.com/$repo/tar.gz/$sha" -o "$d/src.tgz"
mkdir "$d/src"
tar -xzf "$d/src.tgz" -C "$d/src" --strip-components=1
bash "$d/src/add-masque.sh"
BASH
```

For your own hostname, replace the final command with `bash "$d/src/add-masque.sh" --masque-domain masque.example.com`. Use a distinct direct A record to IP1, without AAAA/CNAME/CDN. Automatic DNS depends on cdn-one.org. Replace `ref=main` with a LazyProxy commit SHA for reproducibility.

The script backs up the stopped panel, adds the inbound through its API, validates Xray and TLS/SNI/h2, then saves the adapter. Expect a brief interruption. Failures restore panel/nginx/state; a separately issued certificate remains. Existing clients and IP2 bindings are retained. Reruns do not duplicate the inbound; conflicting manual changes stop the operation.

## Clients and acceptance

1. Attach an existing client to MASQUE or create one in the panel, with a password.
2. Import the **Xray JSON subscription** into a MASQUE-capable app. URI and Clash subscriptions omit this inbound; Shadowrocket compatibility is not established here.
3. Test download, upload and UDP from another network. The script's TLS check is not an authenticated client acceptance test.

Log: `/var/log/single443/install.log`. Backups: `/var/backups/single443/`.

[Upstream 3.10.0](https://github.com/MHSanaei/3x-ui/releases/tag/v3.10.0) · [Validation](VALIDATION.md)

## Shadowrocket

Shadowrocket 2.2.90 release notes list MASQUE over H2/H3 with custom SNI/URI. This does not establish support for importing Xray JSON subscriptions. 3x-ui 3.10.0 does not generate a MASQUE share link or individual QR entry, so refreshing a standard URI subscription will not add it.

Manual connection parameters, if exposed by the installed app: server/SNI = saved `masque_domain`, port 443, transport HTTP/2 (`h2`), URI `/.well-known/masque/ip/*/*/`, username = panel client Email, password = that client's password. Keep TLS verification enabled. Client interoperability requires an actual connection test.

[Shadowrocket release history](https://apps.apple.com/us/app/shadowrocket/id932747118).
