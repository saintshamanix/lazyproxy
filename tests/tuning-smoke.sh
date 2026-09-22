#!/usr/bin/env bash
set -Eeuo pipefail
ROOT=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)
source "$ROOT/lib/common.sh"
source "$ROOT/lib/tuning.sh"
source "$ROOT/lib/iplimit.sh"
BACKUP=$(mktemp -d)
trap 'rm -rf "$BACKUP"' EXIT
configure_bbr
configure_iplimit
fail2ban-client set 3x-ipl banip 192.0.2.123
nft list table inet single443_f2b_tcp > "$BACKUP/tcp"
nft list table inet single443_f2b_udp > "$BACKUP/udp"
grep -q '192.0.2.123' "$BACKUP/tcp"
grep -q '192.0.2.123' "$BACKUP/udp"
grep -Eq 'tcp dport.*443' "$BACKUP/tcp"
grep -Eq 'udp dport.*443.*51820' "$BACKUP/udp"
# Verify idempotent configuration and restart, then remove synthetic ban.
configure_iplimit
fail2ban-client set 3x-ipl unbanip 192.0.2.123
restore_bbr
echo 'PASS BBR capability handling and fail2ban real TCP/UDP nftables actions'
