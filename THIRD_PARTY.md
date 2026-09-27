# Third-party components and license scope

LazyProxy's own scripts, templates, tests and documentation are covered by the
[MIT License](LICENSE). This includes the owner's INCY routing selection in
`templates/routing/incy.json`, authorized for MIT publication.

MIT does not replace the licenses of software or datasets obtained from other
projects. LazyProxy integrates with separately installed programs through their
CLI, API and configuration interfaces. This repository does not bundle their
binaries or source trees.

## Separately downloaded components

| Component | Use | Upstream license reference |
|---|---|---|
| 3x-ui 3.8.5 | Panel release archive; upstream `setting.go` and systemd service downloaded by the installer | [GPLv3](https://github.com/MHSanaei/3x-ui/blob/v3.8.5/LICENSE) |
| Xray-core 26.9.9 | Core supplied by the reviewed 3x-ui release | [MPL-2.0](https://github.com/XTLS/Xray-core/blob/v26.9.9/LICENSE) |
| nginx | Ubuntu packages for HTTP/TLS reverse proxy and stream routing | [BSD 2-Clause](https://nginx.org/LICENSE) |
| Certbot and ACME | Ubuntu packages; isolated 5.8.0 packages for optional IP TLS | [Apache-2.0](https://github.com/certbot/certbot/blob/v5.8.0/LICENSE.txt) |
| Fail2ban | Ubuntu package for IP-limit enforcement | [GPLv2 with file-specific exceptions](https://github.com/fail2ban/fail2ban/blob/master/COPYING) |

These references identify the reviewed projects, not a complete dependency SBOM.
Embedded AmneziaWG and other transitive dependencies retain their upstream
notices. For the actual Ubuntu package versions, consult their installed
`/usr/share/doc/<package>/copyright` files. Python, OpenSSL, nftables and other
system dependencies likewise retain their own licenses.

The installer also saves upstream source/service files on the server. Those
downloaded files are not relicensed under MIT. Redistributing a prepared server
image, upstream archive or modified component requires reviewing that component's
license and applicable source/notice obligations separately.

## Remote routing data

The INCY profile contains URLs for remote data; the datasets are not included in
this repository:

- [Loyalsoldier/v2ray-rules-dat](https://github.com/Loyalsoldier/v2ray-rules-dat):
  [project license](https://github.com/Loyalsoldier/v2ray-rules-dat/blob/master/LICENSE).
- [runetfreedom/russia-v2ray-rules-dat](https://github.com/runetfreedom/russia-v2ray-rules-dat):
  [project license](https://github.com/runetfreedom/russia-v2ray-rules-dat/blob/main/LICENSE).

Both project license files contain GPLv3. Consult their source-data attribution
and distribution notices as well; this is not a claim that every constituent
dataset has the same license. MIT covers the owner's selection of rules, not
ownership of these remote datasets.

## References

The [upstream review](docs/UPSTREAM.md) records API and design references,
including mozaroc/x-ui-pro. The README also links the XTLS XHTTP/nginx example
and nginx documentation. These references do not grant rights to upstream code.

See the [license review record](docs/LICENSE_REVIEW.md) for scope and limitations.

## По-русски

MIT распространяется на собственные файлы LazyProxy, включая авторскую подборку
правил INCY. Скачиваемые компоненты, исходные файлы upstream и внешние геоданные
сохраняют свои лицензии. MIT этого репозитория не распространяется на весь
установленный сервер. Таблица выше содержит ссылки на первоисточники; при
распространении готового образа сервера необходимо отдельно учитывать условия
входящих в него компонентов.
