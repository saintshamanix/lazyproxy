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
    before=api.call('inbounds/list')
    e.configure_amnezia(s,api)
    after=api.call('inbounds/list')
    assert len(before)==len(after)==1
    assert e.json_object(before[0]['settings'])==e.json_object(after[0]['settings'])
    assert before[0]['id']==after[0]['id']
    links=api.call('clients/links/single443-amneziawg')
    assert isinstance(links,list) and len(links)==1
    e.validate_links(links[0].encode(),s,'amneziawg')
    for attempt in range(20):
        text=e.subprocess.check_output(['ss','-H','-lnup','sport = :51820'],text=True)
        if 'x-ui' in text: break
        time.sleep(1)
    else: raise RuntimeError('Embedded AWG did not bind UDP/51820')
print('PASS real upstream AmneziaWG creation, generated credentials, idempotence, client export and UDP listener')
