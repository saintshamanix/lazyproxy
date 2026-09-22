"""Render nginx/Xray fixtures without touching the host configuration."""
import importlib.util
import json
from pathlib import Path
import sys

root=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('engine',root/'lib/engine.py')
e=importlib.util.module_from_spec(spec);spec.loader.exec_module(e)
out=Path(sys.argv[1]).resolve();out.mkdir(parents=True,exist_ok=True)
s=dict(domain='web.example.com',reality_domain='reality.example.com',panel_path='/randomPanel/',ws_path='/randomWs',
       xhttp_path='/randomXhttp/',grpc_service='randomGrpc',sub_id='subid',private_key=sys.argv[2],public_key=sys.argv[3],short_id='abcdef0123456789',
       trojan_password='not-a-real-password',hysteria_auth='not-a-real-auth',
       uuids=dict(reality='b6f091c7-53aa-4ff7-a8c4-4a0f98c78e01',ws='b6f091c7-53aa-4ff7-a8c4-4a0f98c78e02',xhttp='b6f091c7-53aa-4ff7-a8c4-4a0f98c78e03'))
e.CERT=str(out)+'/'
rows=e.inbound_payloads(s)
for r in rows:
    for k in ('settings','streamSettings','sniffing','allocate'):r[k]=json.loads(r[k])
    r['streamSettings'].pop('externalProxy',None)
    for field in ('tlsSettings','realitySettings'):
        r['streamSettings'].get(field,{}).pop('settings',None)
    for key in ('remark','enable','total','expiryTime'):r.pop(key,None)
(out/'xray.json').write_text(json.dumps(dict(inbounds=rows,outbounds=[dict(protocol='freedom',tag='direct')]),indent=2))
d=dict(port=23456,host='sub.example.com',tls=True,address='127.0.0.1',paths=['/randomSub/','/randomJson/','/randomClash/'],clash_path='/randomClash/')
values=dict(DOMAIN=s['domain'],REALITY_DOMAIN=s['reality_domain'],PANEL_PATH=s['panel_path'],WS_PATH=s['ws_path'],XHTTP_PATH=s['xhttp_path'],GRPC_SERVICE=s['grpc_service'],SUB_LOCATIONS=e.sub_locations(d))
for kind in ('stream','web'):
    text=(root/f'templates/nginx-{kind}.conf.tpl').read_text()
    for k,v in values.items():text=text.replace('@'+k+'@',v)
    text=text.replace('/etc/letsencrypt/live/single443/',str(out)+'/')
    (out/f'{kind}.conf').write_text(text)
