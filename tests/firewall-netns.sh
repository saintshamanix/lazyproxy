#!/usr/bin/env bash
# Run only inside an isolated namespace: sudo unshare --net bash tests/firewall-netns.sh
set -Eeuo pipefail
ROOT=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)
[[ $(readlink /proc/self/ns/net) != "$(readlink /proc/1/ns/net)" ]] || { echo 'Refusing host network namespace'; exit 1; }
nft --check --file "$ROOT/templates/firewall.nft"
nft --file "$ROOT/templates/firewall.nft"
before=$(nft -s list table inet single443)
nft --file "$ROOT/templates/firewall.nft"
[[ $(nft -s list table inet single443) == "$before" ]]
tmp=$(mktemp)
trap 'rm -f "$tmp"' EXIT
nft -j list table inet single443 > "$tmp"
python3 - "$tmp" <<'PY'
import json,sys
items=json.load(open(sys.argv[1]))['nftables']
chains={x['chain']['name']:x['chain'] for x in items if 'chain' in x}
assert chains['input']['policy']=='drop'
assert chains['forward']['policy']=='drop'
assert chains['output']['policy']=='accept'
ports={}
for x in items:
    if 'rule' not in x or x['rule']['chain']!='input':continue
    for expression in x['rule']['expr']:
        match=expression.get('match',{})
        payload=match.get('left',{}).get('payload',{})
        if payload.get('field')=='dport':
            right=match['right']
            ports[payload['protocol']]=set(right['set'] if isinstance(right,dict) else [right])
assert ports=={'tcp':{22,80,443},'udp':{443,51820}},ports
print('PASS: nft syntax, atomic repeated apply, policies and exact allowed port sets')
PY
# Reproduce the stock sshd jail seen on the user's VPS, using real nft JSON.
nft -f - <<'NFT'
table inet f2b-table {
    set addr-set-sshd {
        type ipv4_addr
        elements = { 192.0.2.123 }
    }
    chain f2b-chain {
        type filter hook input priority -1; policy accept;
        tcp dport 22 ip saddr @addr-set-sshd reject with icmp port-unreachable
    }
}
NFT
nft -j list ruleset > "$tmp"
python3 "$ROOT/lib/firewall_check.py" "$tmp" --allow-sshd
if python3 "$ROOT/lib/firewall_check.py" "$tmp"; then
    echo 'ERROR: accepted unverified SSH jail'; exit 1
fi
ssh_before=$(nft -s list table inet f2b-table)
nft --file "$ROOT/templates/firewall.nft"
[[ $(nft -s list table inet f2b-table) == "$ssh_before" ]]
nft 'add chain inet f2b-table foreign { type filter hook forward priority 0; policy accept; }'
nft -j list ruleset > "$tmp"
if python3 "$ROOT/lib/firewall_check.py" "$tmp" --allow-sshd; then
    echo 'ERROR: accepted unrelated base chain'; exit 1
fi
echo 'PASS: real nft SSH-jail JSON, preserved bans, fail-closed unknown chains'
