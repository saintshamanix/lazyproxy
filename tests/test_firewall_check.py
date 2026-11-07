import copy
import importlib.util
from pathlib import Path
import unittest

spec = importlib.util.spec_from_file_location('firewall_check', Path(__file__).resolve().parents[1]/'lib/firewall_check.py')
f = importlib.util.module_from_spec(spec)
spec.loader.exec_module(f)


def ruleset():
    return {'nftables': [
        {'table': dict(family='inet', name='f2b-table')},
        {'set': dict(family='inet', table='f2b-table', name='addr-set-sshd', type='ipv4_addr', elem=['192.0.2.1'])},
        {'chain': dict(family='inet', table='f2b-table', name='f2b-chain', type='filter', hook='input', prio=-1, policy='accept')},
        {'rule': dict(family='inet', table='f2b-table', chain='f2b-chain', expr=[
            {'match': dict(op='==', left={'payload': dict(protocol='tcp', field='dport')}, right=22)},
            {'match': dict(op='==', left={'payload': dict(protocol='ip', field='saddr')}, right='@addr-set-sshd')},
            {'reject': dict(type='icmp', expr='port-unreachable')}
        ])}
    ]}


class FirewallPreflightTests(unittest.TestCase):
    def test_active_ssh_jail_preserved_without_mutation(self):
        data=ruleset(); before=copy.deepcopy(data)
        self.assertTrue(f.validate(data, allow_sshd=True))
        self.assertEqual(data,before)

    def test_requires_live_fail2ban_jail(self):
        with self.assertRaises(ValueError): f.validate(ruleset())

    def test_nonssh_ports_or_broader_policy_refused(self):
        for change in ('port','policy','verdict','set','extra_chain'):
            data=ruleset()
            if change=='port': data['nftables'][3]['rule']['expr'][0]['match']['right']=443
            if change=='policy': data['nftables'][2]['chain']['policy']='drop'
            if change=='verdict': data['nftables'][3]['rule']['expr']=[{'drop':None}]
            if change=='set': data['nftables'][1]['set']['name']='unrelated'
            if change=='extra_chain': data['nftables'].append({'chain':dict(family='inet',table='other',name='input',hook='input')})
            with self.subTest(change=change), self.assertRaises(ValueError): f.validate(data,allow_sshd=True)

    def test_ipv6(self):
        data=ruleset()
        data['nftables'][1]['set'].update(name='addr6-set-sshd',type='ipv6_addr',elem=['2001:db8::1'])
        source=data['nftables'][3]['rule']['expr'][1]['match']
        source['left']['payload']['protocol']='ip6';source['right']='@addr6-set-sshd'
        self.assertTrue(f.validate(data,allow_sshd=True))
