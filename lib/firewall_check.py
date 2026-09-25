"""Read-only nftables preflight. Admit only known managed tables or SSH-only f2b."""
import argparse
import json
from pathlib import Path


def ssh_only_fail2ban(items):
    chains = []
    rules = []
    sets = {}
    for item in items:
        for kind, obj in item.items():
            if not isinstance(obj, dict):
                continue
            if obj.get('family') != 'inet':
                continue
            table = obj.get('name') if kind == 'table' else obj.get('table')
            if table != 'f2b-table':
                continue
            if kind == 'table':
                continue
            if kind == 'chain':
                chains.append(obj)
            elif kind == 'rule':
                rules.append(obj)
            elif kind == 'set':
                sets[obj['name']] = obj
            else:
                return False
    if len(chains) != 1:
        return False
    chain = chains[0]
    expected = dict(name='f2b-chain', type='filter', hook='input', prio=-1, policy='accept')
    if any(chain.get(k) != v for k, v in expected.items()):
        return False
    allowed_sets = {'addr-set-sshd': 'ipv4_addr', 'addr6-set-sshd': 'ipv6_addr'}
    if any(name not in allowed_sets or obj.get('type') != allowed_sets[name]
           for name, obj in sets.items()):
        return False
    for rule in rules:
        if rule.get('chain') != 'f2b-chain':
            return False
        expressions = [x for x in rule.get('expr', []) if set(x) != {'counter'}]
        if len(expressions) != 3:
            return False
        port, source, verdict = expressions
        match = port.get('match', {})
        if match.get('op') not in ('==', 'in') or match.get('left') != {'payload': {'protocol': 'tcp', 'field': 'dport'}}:
            return False
        if match.get('right') not in (22, {'set': [22]}):
            return False
        match = source.get('match', {})
        payload = match.get('left', {}).get('payload', {})
        protocol = payload.get('protocol')
        set_name = 'addr-set-sshd' if protocol == 'ip' else 'addr6-set-sshd' if protocol == 'ip6' else None
        if (set_name not in sets or match.get('op') not in ('==', 'in')
                or payload.get('field') != 'saddr' or match.get('right') != '@'+set_name):
            return False
        if set(verdict) not in ({'reject'}, {'drop'}):
            return False
    return True


def validate(data, allow_sshd=False, managed_iplimit=False):
    items = data['nftables']
    owned = {'single443'}
    if managed_iplimit:
        owned.update(('single443_f2b_tcp', 'single443_f2b_udp'))
    if allow_sshd and ssh_only_fail2ban(items):
        owned.add('f2b-table')
    foreign = [x['chain'] for x in items if 'chain' in x and 'hook' in x['chain']
               and not (x['chain']['family'] == 'inet' and x['chain']['table'] in owned)]
    if foreign:
        names = ', '.join('/'.join(str(c.get(k, '?')) for k in ('family', 'table', 'name')) for c in foreign)
        raise ValueError('Unmanaged firewall base chains: '+names+'; refusing mixed policies')
    return 'f2b-table' in owned


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('ruleset')
    parser.add_argument('--allow-sshd', action='store_true')
    args = parser.parse_args()
    try:
        accepted = validate(json.loads(Path(args.ruleset).read_text()), args.allow_sshd,
                            Path('/etc/fail2ban/jail.d/single443-ipl.local').is_file())
    except (ValueError, KeyError, TypeError) as error:
        parser.exit(1, str(error)+'\n')
    if accepted:
        print('Preserving verified SSH-only fail2ban rules on TCP/22')
