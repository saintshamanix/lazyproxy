# Changelog

## 2026-11-07

- Fresh installs now include Trojan over WebSocket on TCP/443 through nginx. Existing inbounds are unchanged.
- A second IPv4 address can now be attached before the first AmneziaWG peer is added. Hysteria2 stays on the primary address and AmneziaWG uses UDP/443 on the second.
