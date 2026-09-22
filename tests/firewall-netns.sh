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
assert ports=={'tcp':{22,80,443},'udp':{443}},ports
print('PASS: nft syntax, atomic repeated apply, policies and exact allowed port sets')
PY
