import base64
import importlib.util
import json
from pathlib import Path
import sqlite3
import tempfile
import unittest
from unittest.mock import patch

spec=importlib.util.spec_from_file_location('engine',Path(__file__).resolve().parents[1]/'lib/engine.py')
e=importlib.util.module_from_spec(spec);spec.loader.exec_module(e)

def state():
    return dict(domain='1.2.3.4.cdn-one.org', reality_domain='1-2-3-4.cdn-one.org',panel_path='/admin123/',
                ws_path='/ws123',xhttp_path='/xh123/',grpc_service='grpc123', sub_ids={name: name+'-test' for name in e.CLIENT_NAMES},private_key='a'*43,
                public_key='b'*43,short_id='abcdef0123456789',trojan_password='secret',hysteria_auth='auth',
                uuids=dict(reality='a',ws='b',xhttp='c'))

def settings():
    return dict(subEnable=True,subListen='127.0.0.1',subPort=32123,subPath='/random123/',subDomain='sub.example.com',
                subCertFile='',subKeyFile='',subJsonEnable=True,subJsonPath='/json123/',subClashEnable=True,subClashPath='/clash123/')

class DiscoveryTests(unittest.TestCase):
    def test_nonstandard_table_and_column_order(self):
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp)/'db'
            c=sqlite3.connect(p)
            c.execute('CREATE TABLE "preferences strange" (value TEXT, extra TEXT, key TEXT)')
            c.execute('INSERT INTO "preferences strange" VALUES (?, ?, ?)',('45678','ignore','subPort'))
            c.commit();c.close()
            before=p.read_bytes()
            data=e.read_database(p,' "subPath": "/fresh/",\n "subCertFile": "",\n')
            self.assertEqual(data['subPort'],'45678'); self.assertEqual(data['subPath'],'/fresh/')
            self.assertEqual(p.read_bytes(),before)
    def test_ambiguous_tables_fail(self):
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp)/'db';c=sqlite3.connect(p)
            for table in ('one','two'):
                c.execute(f'CREATE TABLE {table} (key TEXT,value TEXT)'); c.execute(f'INSERT INTO {table} VALUES ("subPort","1234")')
            c.commit();c.close()
            with self.assertRaises(RuntimeError): e.read_database(p)
    def test_random_path_and_host(self):
        d=e.discover_settings(settings(),state());text=e.sub_locations(d)
        self.assertIn('127.0.0.1:32123',text);self.assertIn('Host sub.example.com',text)
        self.assertIn('location ^~ /random123/',text);self.assertNotIn('/sub/',text)
        self.assertIn('proxy_pass http://127.0.0.1:32123/clash123/;',text)
    def test_tls_sni_and_verify(self):
        x=settings();x.update(subCertFile='/cert',subKeyFile='/key')
        with patch.object(Path,'is_file',return_value=True): d=e.discover_settings(x,state())
        text=e.sub_locations(d)
        self.assertIn('proxy_ssl_name sub.example.com;',text);self.assertIn('proxy_ssl_verify on;',text)
    def test_incomplete_tls_fails(self):
        x=settings();x['subCertFile']='/cert'
        with self.assertRaises(RuntimeError):e.discover_settings(x,state())
    def test_missing_port_fails(self):
        x=settings();del x['subPort']
        with self.assertRaises(RuntimeError):e.discover_settings(x,state())
    def test_injection_and_collision_fail(self):
        for bad in ['/x/;\ninclude /evil;','/admin123/','/','/xh123/nested/']:
            x=settings();x['subPath']=bad
            with self.assertRaises(RuntimeError):e.discover_settings(x,state())
    def test_unknown_schema_fails(self):
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp)/'db';sqlite3.connect(p).close()
            with self.assertRaises(RuntimeError):e.read_database(p)

class PayloadTests(unittest.TestCase):
    def test_topology_and_external_ports(self):
        rows=e.inbound_payloads(state())
        self.assertEqual(len(rows),5)
        self.assertEqual([r['port'] for r in rows],[8443,10001,10002,10003,443])
        for row in rows:
            stream=json.loads(row['streamSettings']);self.assertEqual(stream['externalProxy'][0]['port'],443)
            self.assertEqual(row['listen'],'0.0.0.0' if row['protocol']=='hysteria' else '127.0.0.1')
        self.assertEqual(json.loads(rows[2]['streamSettings'])['xhttpSettings']['mode'],'stream-up')
        self.assertEqual(json.loads(rows[4]['settings'])['version'],2)
        self.assertEqual(json.loads(rows[4]['streamSettings'])['hysteriaSettings']['version'],2)
    def test_profile_html_is_not_subscription(self):
        with self.assertRaises(RuntimeError):e.validate_links(b'<html>profile</html>',state())
    def test_internal_ports_rejected(self):
        body=('vless://id@1.2.3.4.cdn-one.org:8443?type=tcp&security=reality\n'*5).encode()
        with self.assertRaises(RuntimeError):e.validate_links(body,state())
    def test_valid_subscription(self):
        urls=['vless://id@1.2.3.4.cdn-one.org:443?type='+t+'&security='+sec for t,sec in [('tcp','reality'),('ws','tls'),('xhttp','tls')]]
        urls+=['trojan://secret@1.2.3.4.cdn-one.org:443?type=grpc&security=tls','hysteria2://auth@1.2.3.4.cdn-one.org:443?sni=1.2.3.4.cdn-one.org']
        e.validate_links(base64.b64encode('\n'.join(urls).encode()),state())

if __name__=='__main__':unittest.main()

class MigrationTests(unittest.TestCase):
    def legacy(self):
        s=state()
        rows=e.inbound_payloads(s)
        for i,row in enumerate(rows):
            row['id']=i+1
            settings=json.loads(row['settings'])
            settings['clients'][0].update(subId='legacy',totalGB=123456,expiryTime=1900000000000,comment='keep')
            row['settings']=json.dumps(settings)
        s.pop('sub_ids');s['sub_id']='legacy'
        return s,rows

    def test_split_preserves_clients_and_is_idempotent(self):
        s,rows=self.legacy()
        original=json.loads(json.dumps(rows))
        class API:
            def __init__(self): self.writes=0
            def call(self,endpoint,data=None):
                if endpoint=='inbounds/list': return rows
                self.writes+=1
                rows[int(endpoint.rsplit('/',1)[1])-1]=data
        api=API()
        with patch.object(e,'save'):
            e.split_subscriptions(s,api,rows)
            e.split_subscriptions(s,api,rows)
        self.assertEqual(api.writes,5)
        self.assertEqual(len(set(s['sub_ids'].values())),5)
        for before,after in zip(original,rows):
            old=json.loads(before['settings'])['clients'][0]
            new=json.loads(after['settings'])['clients'][0]
            old.pop('subId');new.pop('subId')
            self.assertEqual(old,new)

    def test_changed_client_refuses_before_first_write(self):
        s,rows=self.legacy()
        settings=json.loads(rows[-1]['settings']);settings['clients'][0]['subId']='custom'
        rows[-1]['settings']=json.dumps(settings)
        from unittest.mock import Mock
        api=Mock()
        with self.assertRaises(RuntimeError): e.split_subscriptions(s,api,rows)
        api.call.assert_not_called()

    def test_independent_subscription_rejects_combined_response(self):
        body=b'vless://id@1.2.3.4.cdn-one.org:443?type=ws&security=tls'
        e.validate_links(body,state(),'ws')
        with self.assertRaises(RuntimeError): e.validate_links(body+b'\n'+body,state(),'ws')
        with self.assertRaises(RuntimeError): e.validate_links(body,state(),'reality')
