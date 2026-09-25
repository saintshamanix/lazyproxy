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

class DomainSelectionTests(unittest.TestCase):
    def select(self, env, saved=None):
        with patch.dict(e.os.environ, env, clear=True):
            return e.installation_domains('8.8.8.8', saved)

    def test_auto_and_custom(self):
        self.assertEqual(self.select({}), ['8.8.8.8.cdn-one.org','8-8-8-8.cdn-one.org'])
        self.assertEqual(self.select(dict(WEB_DOMAIN='VPN.Example.com', REALITY_DOMAIN='reality.example.com')),
                         ['vpn.example.com','reality.example.com'])

    def test_incomplete_colliding_and_unsafe_names(self):
        cases=[dict(WEB_DOMAIN='vpn.example.com'),dict(REALITY_DOMAIN='r.example.com')]
        for bad in ('https://vpn.example.com','*.example.com','localhost','8.8.8.8',
                    'vpn.example.com:443','vpn.example.com/','vpn.example.com;','example.com.'):
            cases.append(dict(WEB_DOMAIN=bad,REALITY_DOMAIN='r.example.com'))
        cases.append(dict(WEB_DOMAIN='VPN.example.com',REALITY_DOMAIN='vpn.example.com'))
        for env in cases:
            with self.subTest(env=env), self.assertRaises(RuntimeError): self.select(env)

    def test_rerun_keeps_both_saved_domains_and_refuses_migration(self):
        saved=dict(ip='8.8.8.8',domain='vpn.example.com',reality_domain='r.example.com')
        self.assertEqual(self.select({},saved),['vpn.example.com','r.example.com'])
        for web,reality in [('other.example.com','r.example.com'),('vpn.example.com','other.example.com')]:
            with self.assertRaises(RuntimeError):
                self.select(dict(WEB_DOMAIN=web,REALITY_DOMAIN=reality),saved)

    def test_custom_dns_failure_never_saves_state(self):
        import socket
        with tempfile.TemporaryDirectory() as tmp, patch.object(e,'STATE',Path(tmp)), \
             patch.dict(e.os.environ,dict(PUBLIC_IPV4='8.8.8.8',WEB_DOMAIN='vpn.example.com',
                        REALITY_DOMAIN='r.example.com'),clear=True), \
             patch.object(e.socket,'getaddrinfo',return_value=[(None,None,None,None,('1.1.1.1',0))]), \
             patch.object(e,'save') as save:
            with self.assertRaises(RuntimeError): e.init()
            save.assert_not_called()

    def test_custom_init_and_rerun_preserve_credentials(self):
        with tempfile.TemporaryDirectory() as tmp, patch.object(e,'STATE',Path(tmp)), \
             patch.dict(e.os.environ,dict(PUBLIC_IPV4='8.8.8.8',WEB_DOMAIN='vpn.example.com',
                        REALITY_DOMAIN='r.example.com'),clear=True), \
             patch.object(e.socket,'getaddrinfo',return_value=[(None,None,None,None,('8.8.8.8',0))]), \
             patch.object(e.subprocess,'check_output',return_value=''):
            e.init()
            before=(Path(tmp)/'state.json').read_bytes()
            e.os.environ.pop('WEB_DOMAIN');e.os.environ.pop('REALITY_DOMAIN')
            e.init()
            self.assertEqual((Path(tmp)/'state.json').read_bytes(),before)

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


class MigrationTests(unittest.TestCase):
    def legacy(self):
        s=state()
        rows=e.inbound_payloads(s)
        for i,row in enumerate(rows):
            row['id']=i+1
            row['remark']='single443-'+e.CLIENT_NAMES[i]
            settings=json.loads(row['settings'])
            settings['clients'][0].update(email='single443-'+e.CLIENT_NAMES[i],subId='legacy',totalGB=123456,expiryTime=1900000000000,comment='keep')
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


class IncySubscriptionTests(unittest.TestCase):
    def test_routing_metadata_not_counted_as_connection(self):
        links = {
            'reality': 'vless://id@1.2.3.4.cdn-one.org:443?type=tcp&security=reality',
            'ws': 'vless://id@1.2.3.4.cdn-one.org:443?type=ws&security=tls',
            'xhttp': 'vless://id@1.2.3.4.cdn-one.org:443?type=xhttp&security=tls',
            'grpc': 'trojan://password@1.2.3.4.cdn-one.org:443?type=grpc&security=tls',
            'hysteria': 'hysteria2://password@1.2.3.4.cdn-one.org:443',
        }
        routes = ['incy://autorouting/onadd/https://example.com/routing/incy.json',
                  'incy://routing/onadd/eyJOYW1lIjoiVGVzdCJ9']
        for name, link in links.items():
            for route in routes:
                for encode in (lambda x:x, base64.b64encode):
                    with self.subTest(name=name,route=route,encoded=encode is base64.b64encode):
                        e.validate_links(encode((link+'\n'+route+'\n').encode()),state(),name)
                        with self.assertRaises(RuntimeError):
                            e.validate_links(encode((link+'\n'+link+'\n'+route).encode()),state(),name)

    def test_metadata_alone_and_unknown_entries_fail(self):
        route=b'incy://autorouting/onadd/https://example.com/routing.json'
        for body in (route, base64.b64encode(route),
                     b'vless://id@1.2.3.4.cdn-one.org:443?type=ws&security=tls\nhttps://example.com/unknown'):
            with self.assertRaises(RuntimeError): e.validate_links(body,state(),'ws')


class NamingAndAmneziaTests(unittest.TestCase):
    def test_panel_json_object_and_legacy_text(self):
        value={'clients':[{'email':'keep'}]}
        for raw in (value,json.dumps(value)):
            result=e.json_object(raw)
            self.assertEqual(result,value)
            result['clients'][0]['email']='changed'
            self.assertEqual(value['clients'][0]['email'],'keep')

    def test_flags_and_stable_numbers(self):
        s=state();s['country_code']='US'
        self.assertEqual(e.inbound_label(s,'reality'),'🇺🇸 REALITY')
        self.assertEqual(e.inbound_label(s,'amneziawg'),'🇺🇸 AmneziaWG')
        s.pop('country_code')
        self.assertEqual(e.inbound_label(s,'ws'),'🌐 WS')

    def test_client_rename_preserves_fields_and_repeats(self):
        s=state();s['inbound_ids']={name:i+1 for i,name in enumerate(e.CLIENT_NAMES)}
        rows=e.inbound_payloads(s)
        for i,row in enumerate(rows):
            row['id']=i+1
            data=json.loads(row['settings'])
            data['clients'][0].update(email='single443-'+e.CLIENT_NAMES[i],comment='keep',totalGB=1234)
            row['settings']=data
        class API:
            writes=0
            def call(self,endpoint,data=None):
                if endpoint=='inbounds/list': return rows
                old=endpoint.rsplit('/',1)[1]
                row=next(r for r in rows if r['settings']['clients'][0]['email']==old)
                if endpoint.startswith('clients/get/'):
                    return dict(inboundIds=[row['id']],client=dict(limitHwid=3))
                self.writes+=1
                assert data['limitHwid']==3
                row['settings']['clients'][0]['email']=data['email']
        api=API()
        with patch.object(e,'MANAGED_NAMES',e.CLIENT_NAMES):
            e.rename_clients(s,api)
            e.rename_clients(s,api)
        self.assertEqual(api.writes,5)
        for i,row in enumerate(rows):
            client=row['settings']['clients'][0]
            self.assertEqual(client['email'],'User'+str(i+1))
            self.assertEqual(client['totalGB'],1234)
            self.assertEqual(client['subId'],s['sub_ids'][e.CLIENT_NAMES[i]])

    def test_custom_names_and_added_clients_are_preserved(self):
        from unittest.mock import Mock
        s=state();s['inbound_ids']={name:i+1 for i,name in enumerate(e.CLIENT_NAMES)}
        rows=e.inbound_payloads(s)
        for i,row in enumerate(rows):
            row['id']=i+1
            data=json.loads(row['settings'])
            data['clients'][0].update(email='My client / '+str(i),limitIp=7,comment='custom')
            data['clients'].append(dict(email='Additional '+str(i),subId='extra-'+str(i)))
            row['settings']=data
        before=json.loads(json.dumps(rows))
        api=Mock();api.call.return_value=rows
        with patch.object(e,'MANAGED_NAMES',e.CLIENT_NAMES):
            e.rename_clients(s,api)
            e.rename_clients(s,api)
        self.assertEqual(rows,before)
        self.assertTrue(all(call.args==('inbounds/list',) for call in api.call.call_args_list))

    def test_ambiguous_or_missing_identity_still_fails(self):
        s=state();s['inbound_ids']={'xhttp':3}
        row=e.inbound_payloads(s)[2];row['id']=3
        row['settings']=json.loads(row['settings'])
        row['settings']['clients'].append(dict(row['settings']['clients'][0],email='other'))
        with self.assertRaises(RuntimeError): e.managed_client(s,[row],'xhttp')
        row['settings']['clients']=[]
        with self.assertRaises(RuntimeError): e.managed_client(s,[row],'xhttp')

    def test_country_lookup_and_outage(self):
        s=state();s['ip']='1.2.3.4'
        with patch.object(e.subprocess,'check_output',return_value='{"success":true,"ip":"1.2.3.4","country_code":"DE"}'), patch.object(e,'save'):
            e.detect_country(s)
        self.assertEqual(s['country_code'],'DE')
        s.pop('country_code')
        with patch.object(e.subprocess,'check_output',return_value='{"success":false}'), patch.object(e,'save'):
            e.detect_country(s)
        self.assertNotIn('country_code',s)

    def test_awg_api_creation_and_repeat_preserves_keys(self):
        s=state();s.update(installed_version='v3.8.5',inbound_ids={})
        class API:
            def __init__(self): self.rows=[];self.adds=0
            def call(self,endpoint,data=None):
                if endpoint=='inbounds/list': return self.rows
                if endpoint=='inbounds/add':
                    self.adds+=1
                    settings=json.loads(data['settings'])
                    self.assert_empty = settings['clients'] == []
                    settings['server']={'privateKey':'server-private'}
                    self.rows=[dict(data,id=6,settings=json.dumps(settings))]
                elif endpoint=='clients/add':
                    assert self.assert_empty and data['inboundIds']==[6]
                    client=dict(data['client'],privateKey='private',publicKey='public',allowedIPs=['10.8.1.2/32'])
                    settings=json.loads(self.rows[0]['settings'])
                    settings['clients']=[client]
                    self.rows[0]['settings']=json.dumps(settings)
                else: raise AssertionError(endpoint)
        api=API()
        with patch.object(e,'save'),patch.object(e.subprocess,'check_output',return_value=''):
            e.configure_amnezia(s,api)
            before=json.loads(json.dumps(api.rows))
            e.configure_amnezia(s,api)
        self.assertEqual(api.adds,1);self.assertEqual(api.rows,before)
        self.assertEqual(s['inbound_ids']['amneziawg'],6)
        self.assertEqual(len(set(s['sub_ids'].values())),6)

    def test_awg_export_checks_endpoint(self):
        s=state();s['ip']='1.2.3.4'
        for port in (51820,443):
            conf=f'[Interface]\nPrivateKey = secret\n[Peer]\nEndpoint = {s["domain"]}:{port}\n'
            link=b'vpn://'+base64.urlsafe_b64encode(conf.encode()).rstrip(b'=')
            if port==51820:
                e.validate_links(link,s,'amneziawg')
                e.validate_links(base64.b64encode(link),s,'amneziawg')
            else:
                with self.assertRaises(RuntimeError): e.validate_links(link,s,'amneziawg')

if __name__=='__main__':unittest.main()
