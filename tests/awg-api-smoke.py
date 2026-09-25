"""Run against an isolated CI 3x-ui 3.8.5 instance, never a user panel."""
import importlib.util
import json
import io
from pathlib import Path
import tempfile
import time

root=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('engine',root/'lib/engine.py')
e=importlib.util.module_from_spec(spec);spec.loader.exec_module(e)
s=dict(installed_version='v3.8.5',panel_path='/ci-test/',username='ci-user',password='ci-password-only',
       country_code='US',domain='web.example.com',ip='127.0.0.1',sub_ids={},inbound_ids={})
for attempt in range(30):
    try:
        api=e.API(s)
        break
    except Exception:
        time.sleep(1)
else:
    raise RuntimeError('CI panel did not start')
original_open=api.opener.open
def inspected_open(*args, **kwargs):
    with original_open(*args, **kwargs) as response:
        raw=response.read()
    payload=json.loads(raw)
    if payload.get('success') is False:
        print('CI API rejection:', payload.get('msg',''))
    return io.BytesIO(raw)
api.opener.open=inspected_open
with tempfile.TemporaryDirectory() as tmp:
    e.STATE=Path(tmp)
    e.configure_amnezia(s,api)
    row=api.call('inbounds/list')[0]
    client=e.json_object(row['settings'])['clients'][0]
    api.call('clients/update/User6',dict(client,email='single443-amneziawg'))
    original_names=e.MANAGED_NAMES
    # Keep stable User6 numbering while restricting migration to this CI inbound.
    original_label=e.client_label
    e.client_label=lambda name: 'User6'
    e.MANAGED_NAMES=('amneziawg',)
    e.rename_clients(s,api)
    e.rename_clients(s,api)
    e.MANAGED_NAMES=original_names
    e.client_label=original_label
    renamed=e.json_object(api.call('inbounds/list')[0]['settings'])['clients'][0]
    for key in ('privateKey','publicKey','allowedIPs','subId'):
        assert renamed[key]==client[key]
    assert renamed['email']=='User6'
    before=api.call('inbounds/list')
    e.configure_amnezia(s,api)
    after=api.call('inbounds/list')
    assert len(before)==len(after)==1
    assert e.json_object(before[0]['settings'])==e.json_object(after[0]['settings'])
    assert before[0]['id']==after[0]['id']
    e.export_amnezia(s,api)
    assert (e.STATE/'User6-AmneziaWG.conf').stat().st_mode & 0o777 == 0o600
    links=api.call('clients/links/User6')
    assert isinstance(links,list) and len(links)==1
    e.validate_links(links[0].encode(),s,'amneziawg')
    # A user rename must survive reruns and export through the native API.
    custom = dict(renamed, email='Custom-AWG')
    api.call('clients/update/User6', custom)
    before_custom = e.json_object(api.call('inbounds/list')[0]['settings'])
    e.configure_amnezia(s, api)
    e.MANAGED_NAMES=('amneziawg',)
    e.rename_clients(s, api)
    e.rename_clients(s, api)
    e.MANAGED_NAMES=original_names
    e.export_amnezia(s, api)
    after_custom = e.json_object(api.call('inbounds/list')[0]['settings'])
    assert before_custom == after_custom
    assert after_custom['clients'][0]['email'] == 'Custom-AWG'
    for attempt in range(20):
        text=e.subprocess.check_output(['ss','-H','-lnup','sport = :51820'],text=True)
        if 'x-ui' in text: break
        time.sleep(1)
    else: raise RuntimeError('Embedded AWG did not bind UDP/51820')
print('PASS real upstream AmneziaWG creation, generated credentials, idempotence, client export and UDP listener')
