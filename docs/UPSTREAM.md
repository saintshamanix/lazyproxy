# Upstream reference

Source review recorded on 2026-09-22. References describe the reviewed upstream interfaces; they do not establish runtime compatibility with every release.

## Releases and integrity

- [Latest release API](https://api.github.com/repos/MHSanaei/3x-ui/releases/latest) returned v3.8.5 at review time; release assets and digests were inspected.
- [v3.7.0 release API](https://api.github.com/repos/MHSanaei/3x-ui/releases/tags/v3.7.0) provided a SHA-256 digest but no separate checksum asset.
- The [v3.8.5 release workflow](https://github.com/MHSanaei/3x-ui/blob/v3.8.5/.github/workflows/release.yml) selected Xray v26.9.9. The [Xray v26.9.9 release](https://github.com/XTLS/Xray-core/releases/tag/v26.9.9) was used for local configuration validation.

## Panel integration

| Interface | Reviewed behavior | Source |
|---|---|---|
| CLI | `migrate` and `setting` commands | [main.go](https://github.com/MHSanaei/3x-ui/blob/v3.8.5/main.go) |
| Session API | Session authentication, CSRF, inbound list/add and settings all/update | [API routing](https://github.com/MHSanaei/3x-ui/blob/v3.8.5/internal/web/controller/api.go), [inbounds](https://github.com/MHSanaei/3x-ui/blob/v3.8.5/internal/web/controller/inbound.go), [settings](https://github.com/MHSanaei/3x-ui/blob/v3.8.5/internal/web/controller/setting.go) |
| CSRF lifecycle | Token retrieval before and after login | [Login controller](https://github.com/MHSanaei/3x-ui/blob/v3.8.5/internal/web/controller/index.go), [panel controller](https://github.com/MHSanaei/3x-ui/blob/v3.8.5/internal/web/controller/spa.go) |
| Subscription settings | `subPort`, `subPath`, `subDomain`, certificate/key fields, random paths and effective defaults | [v3.8.5 settings service](https://github.com/MHSanaei/3x-ui/blob/v3.8.5/internal/web/service/setting.go); [v3.7.0 settings API](https://github.com/MHSanaei/3x-ui/blob/v3.7.0/internal/web/controller/setting.go) uses the same API path |
| Subscription routing | `subId`, HWID status, JSON, Clash and Mihomo aliases | [Subscription controller](https://github.com/MHSanaei/3x-ui/blob/v3.8.5/internal/sub/controller.go) |
| Subscription endpoints | `externalProxy` and compatibility with the newer hosts model | [v3.8.5 endpoints](https://github.com/MHSanaei/3x-ui/blob/v3.8.5/internal/sub/endpoint.go), [v3.7.0 tests](https://github.com/MHSanaei/3x-ui/blob/v3.7.0/internal/sub/endpoint_test.go) |

## Protocol configuration

- **Hysteria2:** `protocol=hysteria`, `version=2` in both configuration blocks and `clients[].auth`. It runs inside the panel's Xray process; the installer adds no separate sidecar. Sources: [inbound schema](https://github.com/MHSanaei/3x-ui/blob/v3.8.5/frontend/src/schemas/protocols/inbound/hysteria.ts), [stream schema](https://github.com/MHSanaei/3x-ui/blob/v3.8.5/frontend/src/schemas/protocols/stream/hysteria.ts).
- **REALITY:** `target`, `serverNames`, `shortIds` and nested client settings follow the [upstream schema](https://github.com/MHSanaei/3x-ui/blob/v3.8.5/frontend/src/schemas/protocols/security/reality.ts).
- **Xray output:** upstream [configuration generation](https://github.com/MHSanaei/3x-ui/blob/v3.8.5/internal/web/service/xray.go) removes panel-only fields before passing the configuration to Xray.

## Design reference

[mozaroc/x-ui-pro.sh](https://github.com/mozaroc/x-ui-pro/blob/master/x-ui-pro.sh) was reviewed for the two automatic domain forms and nginx reverse proxy layout. Its installer code was not copied, and its behavior is not treated as the 3x-ui API contract.

## Compatibility limits

Source inspection and valid JSON do not replace Ubuntu runtime testing. Upstream owners can change tags and branches; unreviewed future APIs are not covered.

The six-inbound adapter requires 3x-ui 3.8.5; earlier source reviews of v3.7.0 do not extend that support boundary. See [release history](../CHANGELOG.md) and [validation evidence](VALIDATION.md).
