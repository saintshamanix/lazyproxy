import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch, Mock

spec = importlib.util.spec_from_file_location('engine', Path(__file__).resolve().parents[1]/'lib/engine.py')
e = importlib.util.module_from_spec(spec)
spec.loader.exec_module(e)

class MasqueTests(unittest.TestCase):
    def test_rerun_preserves_existing_clients_and_two_ip_state(self):
        for secondary in (None, '203.0.113.8'):
            with tempfile.TemporaryDirectory() as tmp, patch.object(e, 'STATE', Path(tmp)), patch.object(e, 'panel_version', return_value='v3.10.0'):
                state = dict(masque_domain='masque.example.test', inbound_ids={'masque':7}, secondary_ip=secondary)
                e.save(state)
                row=e.masque_payload(state); row['id']=7
                row['settings']=json.dumps(dict(clients=[dict(email='existing',password='unchanged')],address=['10.14.0.1/24']))
                api=Mock(); api.call.return_value=[row]
                with patch.object(e, 'API', return_value=api): e.configure_masque()
                api.call.assert_called_once_with('inbounds/list')
                self.assertEqual(e.load(),state)

    def test_conflicting_listener_is_not_overwritten(self):
        with patch.object(e,'load',return_value=dict(masque_domain='masque.example.test')), patch.object(e,'panel_version',return_value='v3.10.0'):
            api=Mock();api.call.return_value=[dict(id=1,port=10004,protocol='vless')]
            with patch.object(e,'API',return_value=api), self.assertRaises(RuntimeError): e.configure_masque()
            api.call.assert_called_once_with('inbounds/list')

    def test_changed_transport_is_rejected(self):
        state=dict(masque_domain='masque.example.test')
        row=e.masque_payload(state)
        stream=json.loads(row['streamSettings']);stream['tlsSettings']['alpn']=['h3']
        row['streamSettings']=json.dumps(stream)
        with self.assertRaises(RuntimeError):e.check_masque_row(row,state)

    def test_no_new_default_client_or_udp_listener(self):
        row=e.masque_payload(dict(masque_domain='masque.example.test'))
        self.assertEqual(json.loads(row['settings'])['clients'],[])
        self.assertEqual(json.loads(row['streamSettings'])['tlsSettings']['alpn'],['h2'])
        self.assertEqual(e.masque_route({}),'')
        self.assertEqual(e.masque_route(dict(masque_domain='masque.example.test',inbound_ids={'masque':7})),
                         '        masque.example.test 127.0.0.1:10004;')

    def test_dns_failure_does_not_save_or_create_inbound(self):
        state=dict(ip='203.0.113.9',domain='web.example.test',reality_domain='reality.example.test')
        with patch.object(e,'load',return_value=state), patch.object(e,'panel_version',return_value='v3.10.0'), patch.object(e.socket,'getaddrinfo',return_value=[(None,None,None,None,('203.0.113.10',0))]), patch.object(e,'save') as save, patch.object(e,'API') as api:
            with self.assertRaises(RuntimeError):e.masque_prepare()
            save.assert_not_called();api.assert_not_called()

    def test_stream_patch_preserves_other_routes_and_reruns(self):
        original='stream {\n    map $ssl_preread_server_name $backend {\n        reality.example.test 127.0.0.1:8443;\n        custom.example.test 127.0.0.1:5555;\n        default 127.0.0.1:7443;\n    }\n}\n'
        state=dict(reality_domain='reality.example.test',masque_domain='masque.example.test',inbound_ids={'masque':7})
        changed=e.masque_stream_text(original,state)
        self.assertEqual(changed.replace(e.masque_route(state)+'\n',''),original)
        self.assertEqual(e.masque_stream_text(changed,state),changed)
        with self.assertRaises(RuntimeError): e.masque_stream_text(original.replace('custom.example.test','masque.example.test'),state)
