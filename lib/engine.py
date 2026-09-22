#!/usr/bin/env python3
"""Version-bounded 3x-ui API adapter; SQLite is opened read-only for discovery."""
import base64
import hashlib
import http.cookiejar
import ipaddress
import json
import os
from pathlib import Path
import re
import secrets
import socket
import sqlite3
import subprocess
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
import uuid

STATE = Path('/etc/single443')
CERT = '/etc/letsencrypt/live/single443/'
CLIENT_NAMES = ('reality', 'ws', 'xhttp', 'grpc', 'hysteria')

def require(ok, message):
    if not ok:
        raise RuntimeError(message)

def write_json(path, data):
    path = Path(path)
    tmp = path.with_suffix(path.suffix + '.tmp')
    tmp.write_text(json.dumps(data, indent=2) + '\n')
    tmp.chmod(0o600)
    tmp.replace(path)

def load():
    return json.loads((STATE / 'state.json').read_text())

def save(s):
    write_json(STATE / 'state.json', s)

def run(args, **kwargs):
    return subprocess.run(args, check=True, **kwargs)

def domain(value):
    require(isinstance(value, str) and len(value) < 254 and re.fullmatch(r'[a-zA-Z0-9](?:[a-zA-Z0-9.-]*[a-zA-Z0-9])?', value), 'Unsafe domain')
    require(all(label and len(label) <= 63 and not label.startswith('-') and not label.endswith('-') for label in value.split('.')), 'Invalid domain labels')
    return value

def path_value(value):
    require(isinstance(value, str) and re.fullmatch(r'/(?:[A-Za-z0-9_-]+/)+', value), 'Unsupported or unsafe subscription path; nginx unchanged')
    return value

def init():
    ip = os.environ.get('PUBLIC_IPV4', '')
    if not ip:
        probes = []
        for url in ('https://api.ipify.org', 'https://ipv4.icanhazip.com'):
            probes.append(subprocess.check_output(['curl', '-4', '-fLsS', '--max-time', '15', url], text=True).strip())
        require(len(set(probes)) == 1, 'IPv4 discovery sources disagree; set PUBLIC_IPV4 explicitly')
        ip = probes[0]
    require(ipaddress.IPv4Address(ip).is_global, 'A globally routable IPv4 is required')
    suffix = domain(os.environ['AUTO_DOMAIN_SUFFIX'])
    names = [domain(ip + '.' + suffix), domain(ip.replace('.', '-') + '.' + suffix)]
    for name in names:
        addresses = {x[4][0] for x in socket.getaddrinfo(name, None, socket.AF_INET)}
        require(addresses == {ip}, f'DNS A for {name} does not exclusively resolve to this VPS')
        # AAAA pointing elsewhere breaks ACME HTTP-01 validation.
        aaaa = subprocess.check_output(['dig', '+short', 'AAAA', name], text=True).strip()
        require(not aaaa, f'{name} has AAAA/CNAME records; this IPv4-only adapter requires unambiguous DNS')
    if (STATE / 'state.json').exists():
        s = load()
        require(s['ip'] == ip and s['domain'] == names[0], 'IP/domain changed; automatic migration is intentionally refused')
        return
    s = dict(ip=ip, domain=names[0], reality_domain=names[1], username='admin_' + secrets.token_hex(5),
             password=secrets.token_urlsafe(32), sub_ids={name: secrets.token_hex(16) for name in CLIENT_NAMES}, configured=False,
             installed_version='', short_id=secrets.token_hex(8), trojan_password=secrets.token_urlsafe(32),
             hysteria_auth=secrets.token_urlsafe(32), grpc_service='g' + secrets.token_hex(12))
    for key in ('panel_path', 'ws_path', 'xhttp_path', 'sub_path', 'json_path', 'clash_path'):
        s[key] = '/' + secrets.token_hex(16) + '/'
    # Exact WS location and a slash-ending XHTTP prefix.
    s['ws_path'] = s['ws_path'].rstrip('/')
    s['uuids'] = {name: str(uuid.uuid4()) for name in ('reality', 'ws', 'xhttp')}
    save(s)

class API:
    def __init__(self, s):
        self.base = 'http://127.0.0.1:2053' + s['panel_path']
        self.opener = urllib.request.build_opener(urllib.request.ProxyHandler({}), urllib.request.HTTPCookieProcessor(http.cookiejar.CookieJar()))
        self.csrf = ''
        self.csrf = self.request('csrf-token')['obj']
        self.request('login', dict(username=s['username'], password=s['password']), form=True)
        self.csrf = self.request('panel/csrf-token')['obj']

    def request(self, endpoint, data=None, form=False):
        headers = {'X-CSRF-Token': self.csrf, 'Accept': 'application/json'}
        body = None
        if data is not None:
            headers['Content-Type'] = 'application/x-www-form-urlencoded' if form else 'application/json'
            body = (urllib.parse.urlencode(data) if form else json.dumps(data)).encode()
        req = urllib.request.Request(self.base + endpoint, data=body, headers=headers)
        try:
            with self.opener.open(req, timeout=25) as response:
                obj = json.load(response)
        except (urllib.error.HTTPError, urllib.error.URLError, ValueError) as e:
            # Do not print response bodies: they may contain credentials/configs.
            raise RuntimeError(f'API {endpoint.split("/")[0]} failed ({type(e).__name__})') from None
        require(isinstance(obj, dict) and obj.get('success') is True, f'API rejected {endpoint}; see panel journal')
        return obj

    def call(self, endpoint, data=None):
        return self.request('panel/api/' + endpoint, data).get('obj')

def wait_panel():
    for _ in range(40):
        try:
            return API(load())
        except (RuntimeError, OSError):
            time.sleep(1)
    raise RuntimeError('Panel API did not become ready within 40s')

def bootstrap_cli():
    s = load()
    run(['/usr/local/x-ui/x-ui', 'setting', '-port', '2053', '-listenIP', '127.0.0.1',
         '-webBasePath', s['panel_path'], '-username', s['username'], '-password', s['password']], stdout=subprocess.DEVNULL)

def configure_panel():
    s = load()
    api = API(s)
    settings = api.call('setting/all', {})
    require(isinstance(settings, dict), 'Settings API returned unexpected shape')
    if not s['configured']:
        changes = dict(subEnable=True, subListen='127.0.0.1', subPort=2096, subDomain=s['domain'],
                       subPath=s['sub_path'], subCertFile=CERT+'fullchain.pem', subKeyFile=CERT+'privkey.pem',
                       subJsonEnable=True, subJsonPath=s['json_path'], subClashEnable=True, subClashPath=s['clash_path'],
                       subURI='https://'+s['domain']+s['sub_path'], subJsonURI='https://'+s['domain']+s['json_path'],
                       subClashURI='https://'+s['domain']+s['clash_path'])
        require(set(changes) <= set(settings), 'Selected release lacks required settings API capabilities')
        settings.update(changes)
        if 'trustedProxyCIDRs' in settings:
            settings['trustedProxyCIDRs'] = '127.0.0.1/32'
        api.call('setting/update', settings)
        run(['systemctl', 'restart', 'x-ui'])
        wait_panel()
    s['installed_version'] = os.environ['TAG']
    save(s)

def read_database(db, defaults_text=''):
    # Values may be absent from SQLite when upstream defaults apply.
    defaults = dict(re.findall(r'^\s*"([A-Za-z0-9]+)":\s*"([^"\n]*)",?\s*$', defaults_text, re.M))
    con = sqlite3.connect(Path(db).resolve().as_uri() + '?mode=ro', uri=True)
    con.execute('PRAGMA query_only=ON')
    candidates = []
    def ident(name):
        return '"' + name.replace('"', '""') + '"'
    try:
        tables = con.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'").fetchall()
        for (table,) in tables:
            columns = [r[1] for r in con.execute('PRAGMA table_info(' + ident(table) + ')')]
            names = {x.lower(): x for x in columns}
            # Column semantics are matched, never positional SELECT * or a fixed table name.
            key = next((names[x] for x in ('key', 'name', 'setting_key') if x in names), None)
            value = next((names[x] for x in ('value', 'setting_value') if x in names), None)
            if not key or not value:
                continue
            rows = con.execute('SELECT '+ident(key)+','+ident(value)+' FROM '+ident(table)).fetchall()
            pairs = dict(rows)
            if any(k in pairs for k in ('subPort', 'subPath', 'webPort', 'webBasePath')):
                require(len(rows) == len(pairs), 'Duplicate settings keys')
                candidates.append(pairs)
        require(len(candidates) == 1, 'Ambiguous/unknown SQLite schema; discovery stopped safely')
        defaults.update(candidates[0])
        return defaults
    finally:
        con.close()

def truth(x):
    return x is True or str(x).lower() == 'true'

def discover_settings(settings, s):
    required = {'subPort', 'subPath', 'subDomain', 'subCertFile', 'subKeyFile', 'subListen', 'subEnable'}
    require(required <= set(settings), 'Missing effective subscription settings; no guessed port/path/TLS')
    require(truth(settings['subEnable']), 'Subscription server is disabled')
    port = int(settings['subPort'])
    require(1 <= port <= 65535 and port not in (443, 7443, 8443, 2053, 10001, 10002, 10003), 'Invalid/conflicting subscription port')
    listen = settings['subListen']
    require(listen in ('127.0.0.1', '::1', '', '0.0.0.0', '::'), 'Subscription listen address is not supported')
    cert, key = settings['subCertFile'], settings['subKeyFile']
    require(bool(cert) == bool(key), 'Incomplete subscription TLS pair')
    if cert:
        require(Path(cert).is_file() and Path(key).is_file(), 'Subscription TLS files missing')
    host = domain(settings['subDomain'] or s['domain'])
    paths = [path_value(settings['subPath'])]
    for enabled, name in (('subJsonEnable', 'subJsonPath'), ('subClashEnable', 'subClashPath')):
        if truth(settings.get(enabled)):
            paths.append(path_value(settings[name]))
    paths = list(dict.fromkeys(paths))
    reserved = [s['panel_path'], s['xhttp_path'], s['ws_path']+'/', '/'+s['grpc_service']+'/', '/routing/']
    if truth(settings.get('subClashEnable')):
        require(not any(p in ('/mihomo/', '/clash/') and p != settings.get('subClashPath') for p in paths), 'Subscription format collides with a public Clash alias')
    require(not any(a.startswith(b) or b.startswith(a) for a in paths for b in reserved), 'Subscription path collides with managed routes')
    require(not any(a != b and (a.startswith(b) or b.startswith(a)) for a in paths for b in paths), 'Overlapping subscription paths')
    return dict(port=port, host=host, tls=bool(cert), cert=cert, key=key,
                address='::1' if listen == '::1' else '127.0.0.1', paths=paths, main_path=paths[0],
                clash_path=settings.get('subClashPath') if truth(settings.get('subClashEnable')) else None,
                json_path=settings.get('subJsonPath') if truth(settings.get('subJsonEnable')) else None,
                public_uri=settings.get('subURI', ''), source='effective-settings')

def discover():
    s = load()
    try:
        settings = API(s).call('setting/all', {})
        source = 'API'
    except RuntimeError:
        settings = read_database('/etc/x-ui/x-ui.db', (STATE/'upstream-setting.go').read_text())
        source = 'SQLite read-only + selected-tag defaults'
    result = discover_settings(settings, s)
    result['source'] = source
    write_json(STATE/'subscription.json', result)
    print('Subscription discovery OK ('+source+'); values kept in root-only state')
    return result

def inbound_payloads(s):
    tls = dict(serverName=s['domain'], minVersion='1.2', maxVersion='1.3', alpn=['h3'],
               certificates=[dict(certificateFile=CERT+'fullchain.pem', keyFile=CERT+'privkey.pem', usage='encipherment')],
               settings=dict(serverName=s['domain'], allowInsecure=False, fingerprint='chrome'))
    streams = {
        'reality': dict(network='tcp', security='reality', tcpSettings=dict(acceptProxyProtocol=False, header=dict(type='none')),
                        realitySettings=dict(show=False, target='127.0.0.1:7443', xver=0, serverNames=[s['reality_domain']],
                        privateKey=s['private_key'], shortIds=[s['short_id']], settings=dict(publicKey=s['public_key'], fingerprint='chrome', serverName=s['reality_domain'], spiderX='/'))),
        'ws': dict(network='ws', security='none', wsSettings=dict(path=s['ws_path'], headers={})),
        'xhttp': dict(network='xhttp', security='none', xhttpSettings=dict(path=s['xhttp_path'], mode='stream-up', host=s['domain'])),
        'grpc': dict(network='grpc', security='none', grpcSettings=dict(serviceName=s['grpc_service'], multiMode=False)),
        'hysteria': dict(network='hysteria', security='tls', tlsSettings=tls, hysteriaSettings=dict(version=2, udpIdleTimeout=60)),
    }
    result = []
    for name, port in [('reality',8443), ('ws',10001), ('xhttp',10002), ('grpc',10003), ('hysteria',443)]:
        protocol = 'hysteria' if name == 'hysteria' else 'trojan' if name == 'grpc' else 'vless'
        client = dict(email='single443-'+name, enable=True, subId=s['sub_ids'][name], limitIp=0, totalGB=0, expiryTime=0, reset=0, tgId=0)
        if protocol == 'vless':
            client.update(id=s['uuids'][name], flow='xtls-rprx-vision' if name == 'reality' else '')
        elif protocol == 'trojan':
            client['password'] = s['trojan_password']
        else:
            client['auth'] = s['hysteria_auth']
        settings = dict(clients=[client])
        if protocol == 'vless':
            settings.update(decryption='none', fallbacks=[])
        if protocol == 'hysteria':
            settings['version'] = 2
        stream = streams[name]
        stream['externalProxy'] = [dict(forceTls='same' if name in ('reality','hysteria') else 'tls',
                                        dest=s['domain'], port=443, remark='single443-'+name,
                                        sni=s['reality_domain'] if name == 'reality' else s['domain'])]
        result.append(dict(remark='single443-'+name, enable=True, listen='0.0.0.0' if name=='hysteria' else '127.0.0.1',
                           port=port, protocol=protocol, settings=json.dumps(settings), streamSettings=json.dumps(stream),
                           sniffing=json.dumps(dict(enabled=False, destOverride=['http','tls','quic'])),
                           allocate=json.dumps(dict(strategy='always', refresh=5, concurrency=3)), total=0, expiryTime=0))
    return result

def split_subscriptions(s, api, rows):
    """Migrate only the original five installer clients, preserving other fields."""
    if 'sub_ids' in s:
        return
    legacy = s.get('sub_id')
    require(bool(legacy), 'Missing subscription state')
    plans = []
    ids = {name: secrets.token_hex(16) for name in CLIENT_NAMES}
    # Validate all five before any mutation; unknown/manual layouts need review.
    for name in CLIENT_NAMES:
        matches = [row for row in rows if row.get('remark') == 'single443-'+name]
        require(len(matches) == 1, 'Migration requires exactly five original managed inbounds')
        row = dict(matches[0])
        settings = json.loads(row['settings'])
        clients = settings.get('clients', [])
        require(len(clients) == 1, 'Migration refuses inbounds with additional clients')
        client = clients[0]
        require(client.get('email') == 'single443-'+name and client.get('subId') == legacy,
                'Managed client identity/subscription changed; migration refused')
        credential = 'id' if name in ('reality','ws','xhttp') else 'password' if name == 'grpc' else 'auth'
        expected = s['uuids'][name] if credential == 'id' else s['trojan_password'] if credential == 'password' else s['hysteria_auth']
        require(client.get(credential) == expected, 'Managed credentials changed; migration refused')
        client['subId'] = ids[name]
        row['settings'] = json.dumps(settings)
        plans.append(row)
    for row in plans:
        api.call('inbounds/update/'+str(row['id']), row)
    verified = api.call('inbounds/list')
    for row in plans:
        actual = [x for x in verified if x.get('id') == row['id']]
        require(len(actual) == 1, 'Migration API verification failed')
        require(json.loads(actual[0]['settings']).get('clients') == json.loads(row['settings'])['clients'],
                'Migration did not preserve client fields; rolling back')
    s['sub_ids'] = ids
    s.pop('sub_id', None)
    save(s)


def inbounds():
    s = load()
    api = API(s)
    if 'private_key' not in s:
        keys = api.call('server/getNewX25519Cert')
        for name in ('privateKey', 'publicKey'):
            require(re.fullmatch(r'[A-Za-z0-9_-]{43}', keys[name]), 'Unexpected X25519 key format')
        s.update(private_key=keys['privateKey'], public_key=keys['publicKey'])
        save(s)
    existing = api.call('inbounds/list')
    require(isinstance(existing, list), 'Unknown inbound list schema')
    split_subscriptions(s, api, existing)
    for item in inbound_payloads(s):
        matches = [x for x in existing if x.get('remark') == item['remark']]
        require(len(matches) <= 1, 'Duplicate managed inbound; refusing ambiguous update')
        if matches:
            # Preserve users, counters and manual panel changes. Verify essential topology only.
            old = matches[0]
            require(all(old.get(k) == item[k] for k in ('port', 'protocol', 'listen', 'enable')), 'Managed inbound topology changed; refusing to overwrite')
            stream = json.loads(old['streamSettings'])
            expected = json.loads(item['streamSettings'])
            require(all(stream.get(k) == expected[k] for k in ('network','security')), 'Managed transport/security changed')
            for block, keys in {'wsSettings':('path',), 'xhttpSettings':('path','mode','host'),
                                'grpcSettings':('serviceName',), 'realitySettings':('target','serverNames','privateKey','shortIds'),
                                'hysteriaSettings':('version',)}.items():
                if block in expected:
                    actual = stream.get(block,{})
                    if block == 'realitySettings' and 'target' not in actual and 'dest' in actual:
                        actual = dict(actual, target=actual['dest'])
                    require(all(actual.get(k) == expected[block][k] for k in keys), 'Managed path/key/topology changed; existing clients preserved')
            continue
        require(not any(x.get('port') == item['port'] for x in existing), 'Inbound port conflict')
        api.call('inbounds/add', item)
    settings = api.call('setting/all', {})
    routing_changes = dict(subIncyEnableRouting=True,
                           subIncyRoutingRules='https://'+s['domain']+'/routing/incy.json')
    if set(routing_changes) <= set(settings):
        if any(settings[k] != v for k, v in routing_changes.items()):
            settings.update(routing_changes)
            api.call('setting/update', settings)
    else:
        print('INCY routing settings unavailable in this panel version; static URL remains available')
    candidate = api.call('server/getConfigJson')
    require(isinstance(candidate, dict) and 'inbounds' in candidate, 'No generated Xray config from API')
    write_json(STATE/'candidate-xray.json', candidate)
    binaries = list(Path('/usr/local/x-ui/bin').glob('xray-linux-*'))
    require(len(binaries) == 1, 'Ambiguous Xray binary')
    env = dict(os.environ, XRAY_LOCATION_ASSET='/usr/local/x-ui/bin')
    result = subprocess.run([str(binaries[0]), 'run', '-test', '-config', str(STATE/'candidate-xray.json')], env=env, cwd='/usr/local/x-ui', stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    (STATE/'xray-validation.log').write_bytes(result.stdout)
    require(result.returncode == 0, 'Generated Xray config invalid; see /etc/single443/xray-validation.log')
    run(['systemctl', 'restart', 'x-ui'])
    wait_panel()
    s['configured'] = True
    save(s)

def sub_locations(d):
    proto = 'https' if d['tls'] else 'http'
    addr = '['+d['address']+']' if ':' in d['address'] else d['address']
    # Public aliases are mapped to discovered paths, never to an assumed /sub/.
    mapping = {p: None for p in d['paths']}
    if d['clash_path']:
        for alias in ('/mihomo/', '/clash/'):
            mapping.setdefault(alias, d['clash_path'])
    blocks = []
    for public, target in mapping.items():
        lines = [f'    location ^~ {public} {{', f'        proxy_pass {proto}://{addr}:{d["port"]}{target or ""};',
                 '        proxy_http_version 1.1;', f'        proxy_set_header Host {d["host"]};',
                 '        proxy_set_header X-Forwarded-Host $host;', '        proxy_set_header X-Forwarded-Proto https;',
                 '        proxy_set_header X-Forwarded-For $remote_addr;', '        proxy_buffering off;',
                 '        proxy_read_timeout 120s;', '        proxy_redirect off;']
        if d['tls']:
            lines += ['        proxy_ssl_server_name on;', f'        proxy_ssl_name {d["host"]};',
                      '        proxy_ssl_verify on;', '        proxy_ssl_trusted_certificate /etc/ssl/certs/ca-certificates.crt;',
                      '        proxy_ssl_verify_depth 5;']
        blocks.append('\n'.join(lines+['    }']))
    return '\n'.join(blocks)

def render(templates):
    s = load()
    d = json.loads((STATE/'subscription.json').read_text())
    replacements = {'DOMAIN':s['domain'], 'REALITY_DOMAIN':s['reality_domain'], 'PANEL_PATH':s['panel_path'],
                    'WS_PATH':s['ws_path'], 'XHTTP_PATH':s['xhttp_path'], 'GRPC_SERVICE':s['grpc_service'],
                    'SUB_LOCATIONS':sub_locations(d)}
    for source, target in [('nginx-stream.conf.tpl','/etc/nginx/single443-stream.conf'),
                           ('nginx-web.conf.tpl','/etc/nginx/conf.d/single443-web.conf')]:
        text = (Path(templates)/source).read_text()
        for key,value in replacements.items():
            text = text.replace('@'+key+'@', value)
        require(not re.search(r'@[A-Z_]+@',text), 'Unresolved nginx template')
        Path(target).write_text(text)
        Path(target).chmod(0o644)
    main = Path('/etc/nginx/nginx.conf')
    include = 'include /etc/nginx/single443-stream.conf;'
    text = main.read_text()
    if include not in text:
        main.write_text(text+'\n'+include+'\n')
    Path('/etc/nginx/conf.d/single443-acme.conf').unlink(missing_ok=True)
    routing = Path('/var/www/single443/routing')
    routing.mkdir(parents=True, exist_ok=True)
    # User-supplied INCY profile: publish the exact bytes, without normalization.
    profile = (Path(templates)/'routing/incy.json').read_bytes()
    require(isinstance(json.loads(profile), dict), 'Invalid INCY JSON')
    (routing/'incy.json').write_bytes(profile)
    (routing/'incy.json').chmod(0o644)
    for name in ('clash.yaml', 'mihomo.yaml'):
        f = routing/name
        if not f.exists():
            f.write_text('# Empty domain rule-provider; customize before use.\npayload: []\n')
            f.chmod(0o644)
    access = f'Panel: https://{s["domain"]}{s["panel_path"]}\nUsername: {s["username"]}\nPassword: {s["password"]}\n'
    for name, sub_id in s['sub_ids'].items():
        access += f'\n{name} subscription: https://{s["domain"]}{d["main_path"]}{sub_id}\n'
        if d['clash_path']:
            access += f'{name} Mihomo: https://{s["domain"]}{d["clash_path"]}{sub_id}\n'
    access += f'\nINCY routing: https://{s["domain"]}/routing/incy.json\n'
    (STATE/'access.txt').write_text(access)
    (STATE/'access.txt').chmod(0o600)

def curl_body(host, port, path, tls=True, address=None, user_agent='curl/single443'):
    url = f'{"https" if tls else "http"}://{host}:{port}{path}'
    args = ['curl','--noproxy','*','-fLsS','--max-time','20','--max-redirs','0','-A',user_agent]
    if address:
        args += ['--resolve', f'{host}:{port}:{"["+address+"]" if ":" in address else address}']
    result = subprocess.run(args+[url], stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)
    require(result.returncode == 0, 'HTTP/TLS request failed (details omitted to protect secret URL)')
    return result.stdout

def validate_links(body, s, name=None):
    text = body.decode().strip()
    if not re.search(r'(?:vless|trojan|hy2|hysteria2)://', text):
        try:
            text = base64.b64decode(text+'='*(-len(text)%4),validate=True).decode()
        except (ValueError, UnicodeError):
            raise RuntimeError('Subscription returned neither links nor valid base64; possible profile HTML') from None
    urls = []
    for line in text.splitlines():
        line = line.strip()
        if not line:
            continue
        # Upstream appends INCY routing instructions to raw subscriptions,
        # including before base64 encoding. They are not proxy connections.
        if line.startswith(('incy://autorouting/onadd/', 'incy://routing/onadd/')):
            continue
        require(urllib.parse.urlsplit(line).scheme in ('vless','trojan','hy2','hysteria2'),
                'Unexpected subscription entry type')
        urls.append(line)
    expected_count = 1 if name else 5
    require(len(urls) == expected_count,
            f'Unexpected subscription client count: expected {expected_count}, got {len(urls)}')
    managed = []
    for url in urls:
        u = urllib.parse.urlsplit(url)
        if u.hostname != s['domain']:
            continue
        q=urllib.parse.parse_qs(u.query)
        require(u.port == 443, 'Subscription advertises an internal port')
        managed.append((u.scheme, q.get('type',[''])[0], q.get('security',[''])[0]))
    expected = {
        'reality': {('vless','tcp','reality'), ('vless','raw','reality')},
        'ws': {('vless','ws','tls')}, 'xhttp': {('vless','xhttp','tls')},
        'grpc': {('trojan','grpc','tls')},
    }
    for key in ([name] if name else CLIENT_NAMES):
        if key == 'hysteria':
            require(any(x[0] in ('hysteria2','hy2') for x in managed), 'Hysteria2 link missing')
        else:
            require(bool(expected[key].intersection(managed)), key+' external link missing')


def diagnose():
    s=load()
    failures=[]
    def check(label, action):
        try:
            action()
            print('PASS '+label)
        except Exception as e:
            print('FAIL '+label+': '+str(e))
            failures.append(label)
    check('nginx configuration', lambda: run(['nginx','-t']))
    for service in ('x-ui','nginx'):
        check(service+' active', lambda service=service: run(['systemctl','is-active','--quiet',service]))
    check('panel API authentication', lambda: API(s))
    check('certificate valid for next 7 days', lambda: run(['openssl','x509','-checkend','604800','-noout','-in',CERT+'fullchain.pem']))
    for port in (2053,7443,8443,10001,10002,10003):
        def tcp(port=port):
            with socket.create_connection(('127.0.0.1',port),timeout=3):
                pass
        check('local TCP '+str(port),tcp)
    def udp():
        text=subprocess.check_output(['ss','-H','-lunp','sport = :443'],text=True)
        require('xray' in text.lower(), 'Xray is not listening on UDP/443')
    check('Hysteria2 UDP listener (not a protocol handshake)',udp)
    check('decoy via local SNI dispatcher',lambda: require(b'Field Notes' in curl_body(s['domain'],443,'/',address='127.0.0.1'),'Unexpected decoy'))
    check('REALITY unauthenticated TLS fallback',lambda: require(b'Field Notes' in curl_body(s['reality_domain'],443,'/',address='127.0.0.1'),'Unexpected fallback'))
    check('public decoy URL from VPS',lambda: require(b'Field Notes' in curl_body(s['domain'],443,'/'),'Unexpected decoy'))
    check('public panel URL from VPS',lambda: curl_body(s['domain'],443,s['panel_path']))
    try:
        d=discover()
        for name, sub_id in s['sub_ids'].items():
            check(name+' subscription backend with Host/SNI',lambda name=name, sub_id=sub_id: validate_links(curl_body(d['host'],d['port'],d['main_path']+sub_id,d['tls'],d['address'],'v2rayN/7.0'),s,name))
            check(name+' public subscription: exactly one client',lambda name=name, sub_id=sub_id: validate_links(curl_body(s['domain'],443,d['main_path']+sub_id,user_agent='v2rayN/7.0'),s,name))
            if d['clash_path']:
                check(name+' public Mihomo subscription',lambda sub_id=sub_id: require(b'proxies:' in curl_body(s['domain'],443,d['clash_path']+sub_id,user_agent='mihomo/1.19'),'Unexpected Mihomo body'))
    except Exception as e:
        failures.append('discovery')
        print('FAIL subscription discovery: '+str(e))
    for name in ('incy.json','clash.yaml','mihomo.yaml'):
        check('routing file '+name,lambda name=name: curl_body(s['domain'],443,'/routing/'+name))
    def bindings():
        text=subprocess.check_output(['ss','-H','-lnt'],text=True)
        ports = {2053,2096,7443,8443,10001,10002,10003}
        saved = STATE/'subscription.json'
        if saved.exists():
            ports.add(json.loads(saved.read_text())['port'])
        for line in text.splitlines():
            local=line.split()[3]
            if int(local.rsplit(':',1)[1]) in ports:
                require(local.startswith(('127.0.0.1:','[::1]:')), 'Internal backend exposed on wildcard address')
    check('internal listeners restricted to loopback',bindings)
    print('Authenticated proxy handshakes, UDP reachability from another network and large uploads require client-side VPS acceptance tests; not established here.')
    require(not failures, str(len(failures))+' diagnostic checks failed')

def main():
    command=sys.argv[1]
    if command=='init': init()
    elif command=='value': print(load().get(sys.argv[2],''))
    elif command=='bootstrap-cli': bootstrap_cli()
    elif command=='wait-panel': wait_panel()
    elif command=='configure-panel': configure_panel()
    elif command=='discover': discover()
    elif command=='inbounds': inbounds()
    elif command=='render': render(sys.argv[2])
    elif command=='diagnose': diagnose()
    elif command=='verify-release':
        artifact=Path(sys.argv[2])
        release=json.loads(Path(sys.argv[3]).read_text())
        assets=[a for a in release['assets'] if a['name']==artifact.name]
        require(len(assets)==1, 'Release asset not uniquely identified')
        digest=assets[0].get('digest','')
        if not re.fullmatch(r'sha256:[a-f0-9]{64}', digest or ''):
            sums=[a for a in release['assets'] if a['name']==artifact.name+'.sha256']
            require(len(sums)==1, 'No upstream SHA256 digest/checksum; refusing unchecked release')
            url=sums[0]['browser_download_url']
            require(url.startswith('https://github.com/MHSanaei/3x-ui/releases/download/'), 'Unexpected checksum URL')
            raw=subprocess.check_output(['curl','-fLsS','--retry','3',url],text=True)
            matches=re.findall(r'\b[a-fA-F0-9]{64}\b',raw)
            require(len(matches)==1,'Ambiguous checksum')
            digest='sha256:'+matches[0].lower()
        require(hashlib.sha256(artifact.read_bytes()).hexdigest()==digest[7:],'Release checksum mismatch')
    elif command=='verify-checksum':
        matches=re.findall(r'\b[a-fA-F0-9]{64}\b',Path(sys.argv[3]).read_text())
        require(len(matches)==1,'Ambiguous release checksum')
        require(hashlib.sha256(Path(sys.argv[2]).read_bytes()).hexdigest()==matches[0].lower(),'Release checksum mismatch')
    else: raise RuntimeError('Unknown engine command')

if __name__=='__main__':
    try: main()
    except Exception as error:
        print('ERROR: '+str(error),file=sys.stderr)
        sys.exit(1)
