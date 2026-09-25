"""Test native QR link exports on the disposable upstream CI panel."""
import importlib.util
import json
from pathlib import Path
from urllib.parse import urlsplit, parse_qs

root = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('engine', root/'lib/engine.py')
e = importlib.util.module_from_spec(spec)
spec.loader.exec_module(e)
s = dict(ip_tls='yes', domain='93.184.216.34', ip='93.184.216.34',
         reality_domain='93-184-216-34.cdn-one.org', panel_path='/ci-test/',
         username='ci-user', password='ci-password-only', ws_path='/ipWs',
         xhttp_path='/ipXhttp/', grpc_service='ipGrpc', private_key='A'*43,
         public_key='B'*43, short_id='abcdef0123456789', trojan_password='test-password',
         hysteria_auth='test-auth', uuids=dict(reality='b6f091c7-53aa-4ff7-a8c4-4a0f98c78e01',
         ws='b6f091c7-53aa-4ff7-a8c4-4a0f98c78e02',xhttp='b6f091c7-53aa-4ff7-a8c4-4a0f98c78e03'),
         sub_ids={name: 'ip-test-'+name for name in e.CLIENT_NAMES})
api = e.API(s)
for name, row in zip(e.CLIENT_NAMES, e.inbound_payloads(s)):
    api.call('inbounds/add', row)
    links = api.call('clients/links/'+e.client_label(name))
    assert len(links) == 1, (name, 'unexpected link count')
    e.validate_links(links[0].encode(), s, name)
    u = urlsplit(links[0]); q = parse_qs(u.query)
    assert u.hostname == s['ip'] and u.port == 443, name
    assert q.get('sni') == [s['reality_domain'] if name == 'reality' else s['ip']], name
    assert q.get('allowInsecure', ['0']) in (['0'], ['false']), name
print('PASS native upstream QR exports: IP address, external port, TLS and REALITY SNI')
