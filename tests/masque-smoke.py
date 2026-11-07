"""Real MASQUE API/export plus authenticated TCP/UDP through the SNI dispatcher.
Run in a disposable Linux network namespace; never against a user's services.
"""
import hashlib
import importlib.util
import shutil
import urllib.request
import http.server
import json
import os
from pathlib import Path
import socket
import subprocess
import sys
import tempfile
import threading
import time

ROOT = Path(__file__).resolve().parents[1]
assert os.readlink('/proc/self/ns/net') != os.readlink('/proc/1/ns/net')
subprocess.run(['ip', 'link', 'set', 'lo', 'up'], check=True)
# Public address exists only on loopback in this isolated namespace.
# Current Xray intentionally blocks proxy destinations in loopback/private ranges.
subprocess.run(['ip', 'addr', 'add', '93.184.216.34/32', 'dev', 'lo'], check=True)
TLS_HOST = 'masque.example.test'
spec = importlib.util.spec_from_file_location('engine', ROOT/'lib/engine.py')
e = importlib.util.module_from_spec(spec)
spec.loader.exec_module(e)
XRAY = str(next(Path('/tmp/single443-api/x-ui/bin').glob('xray-linux-*')))
PAYLOAD = os.urandom(2 * 1024 * 1024)


class Echo(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        print('Echo received GET', flush=True)
        self.send_response(200)
        self.send_header('Content-Length', str(len(PAYLOAD)))
        self.end_headers()
        self.wfile.write(PAYLOAD)

    def do_POST(self):
        body = self.rfile.read(int(self.headers['Content-Length']))
        result = hashlib.sha256(body).hexdigest().encode()
        self.send_response(200)
        self.send_header('Content-Length', str(len(result)))
        self.end_headers()
        self.wfile.write(result)

    def log_message(self, *_):
        pass


def wait_port(port):
    for _ in range(100):
        try:
            with socket.create_connection(('127.0.0.1', port), .1):
                return
        except OSError:
            time.sleep(.1)
    raise RuntimeError(f'Listener {port} did not start')


server = http.server.ThreadingHTTPServer(('93.184.216.34', 18081), Echo)
threading.Thread(target=server.serve_forever, daemon=True).start()
with tempfile.TemporaryDirectory(prefix='masque-test-') as directory:
    tmp = Path(directory)
    processes = []
    logs = []
    def launch(args, name, env=None):
        log = (tmp / (name + '.log')).open('w')
        logs.append(log)
        process = subprocess.Popen(args, stdout=log, stderr=subprocess.STDOUT, env=env)
        processes.append(process)
        return process

    try:
        subprocess.run(['openssl', 'req', '-x509', '-newkey', 'rsa:2048', '-nodes',
                        '-days', '1', '-subj', '/CN='+TLS_HOST,
                        '-addext', 'subjectAltName=DNS:'+TLS_HOST,
                        '-keyout', str(tmp/'privkey.pem'), '-out', str(tmp/'fullchain.pem')],
                       check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        binary = '/tmp/single443-api/x-ui/x-ui'
        shutil.copytree('/tmp/single443-api/x-ui/bin', tmp/'bin')
        env = dict(os.environ, XUI_DB_FOLDER=str(tmp/'db'), XUI_BIN_FOLDER=str(tmp/'bin'),
                   XUI_LOG_FOLDER=str(tmp/'logs'))
        for folder in ('db', 'logs'): (tmp/folder).mkdir()
        subprocess.run([binary, 'migrate'], env=env, check=True, stdout=subprocess.DEVNULL)
        subprocess.run([binary, 'setting', '-port', '2053', '-listenIP', '127.0.0.1',
                        '-webBasePath', '/ci-test/', '-username', 'ci-user',
                        '-password', 'ci-password-only'], env=env, check=True, stdout=subprocess.DEVNULL)
        panel = launch([binary], 'panel', env)
        wait_port(2053)
        state = dict(panel_path='/ci-test/', username='ci-user', password='ci-password-only',
                     masque_domain=TLS_HOST, inbound_ids={})
        e.MASQUE_CERT = str(tmp)+'/'
        api = e.API(state)
        settings = api.call('setting/all', {})
        settings.update(subEnable=True, subListen='127.0.0.1', subPort=2096,
                        subDomain=TLS_HOST, subCertFile='', subKeyFile='',
                        subJsonEnable=True, subJsonPath='/json/')
        api.call('setting/update', settings)
        panel.terminate(); panel.wait(timeout=10)
        panel = launch([binary], 'panel-restarted', env)
        wait_port(2053); wait_port(2096)
        api = e.API(state)
        e.STATE = tmp/'state'; e.STATE.mkdir()
        e.XRAY_DIR = tmp
        e.panel_version = lambda: 'v3.10.0'
        # Preserve a pre-existing inbound and its credentials during migration.
        api.call('inbounds/add', dict(remark='existing', enable=True, listen='127.0.0.1',
            port=10005, protocol='vless', settings=json.dumps(dict(decryption='none', clients=[
                dict(id='b6f091c7-53aa-4ff7-a8c4-4a0f98c78e01',email='existing',enable=True,subId='existing')])),
            streamSettings=json.dumps(dict(network='tcp',security='none')),
            sniffing='{}',allocate='{}',total=0,expiryTime=0))
        before = api.call('inbounds/list')
        state['secondary_ip'] = '203.0.113.8'
        e.save(state)
        e.configure_masque()
        state = e.load()
        e.configure_masque()
        assert e.load() == state and state['secondary_ip'] == '203.0.113.8'
        existing = next(r for r in api.call('inbounds/list') if r['id']==before[0]['id'])
        assert existing['settings'] == before[0]['settings']
        assert len(api.call('inbounds/list')) == 2
        row = next(r for r in api.call('inbounds/list') if r['protocol']=='masque')
        e.check_masque_row(row, state)
        assert e.json_object(row['settings'])['clients'] == []
        state['inbound_ids']['masque'] = row['id']
        api.call('clients/add', dict(client=dict(email='masque-test', password='only-ci-password',
            enable=True, subId='masque-ci-sub', totalGB=0, expiryTime=0, limitIp=0), inboundIds=[row['id']]))
        legacy = next(r for r in api.call('inbounds/list') if r['protocol']=='masque')
        legacy['remark'] = 'MASQUE'
        stream = e.json_object(legacy['streamSettings'])
        stream['externalProxy'][0]['remark'] = 'MASQUE'
        legacy['streamSettings'] = json.dumps(stream)
        api.call('inbounds/update/'+str(legacy['id']), legacy)
        state['country_code'] = 'US'; e.save(state)
        e.configure_masque()
        renamed = next(r for r in api.call('inbounds/list') if r['id']==legacy['id'])
        assert renamed['remark'] == '🇺🇸 MASQUE'
        assert renamed['settings'] == legacy['settings']
        e.configure_masque()
        config = api.call('server/getConfigJson')
        inbound = next(r for r in config['inbounds'] if r['protocol']=='masque')
        assert inbound['settings']['clients'][0]['pass'] == 'only-ci-password'
        # The panel runs its generated core: exercise the real listener directly.
        wait_port(e.MASQUE_PORT)
        opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
        with opener.open(urllib.request.Request('http://127.0.0.1:2096/json/masque-ci-sub', headers={'Host': TLS_HOST}), timeout=10) as response:
            exported = json.load(response)
        if isinstance(exported, dict): exported = [exported]
        out = next(o for c in exported for o in c['outbounds'] if o['protocol']=='masque')
        assert out['settings']['address'] == TLS_HOST and out['settings']['port'] == 443
        assert out['streamSettings']['tlsSettings']['alpn'] == ['h2']
        assert out['streamSettings']['tlsSettings']['serverName'] == TLS_HOST
        assert out['streamSettings']['masqueSettings']['pass'] == 'only-ci-password'
        stream = (ROOT/'templates/nginx-stream.conf.tpl').read_text()
        stream = stream.replace('@REALITY_DOMAIN@','reality.example.test').replace('@MASQUE_ROUTE@', e.masque_route(state))
        (tmp/'nginx.conf').write_text('include /etc/nginx/modules-enabled/*.conf;\n'
            + f'pid {tmp}/nginx.pid; error_log {tmp}/nginx-error.log info;\nevents {{}}\n'+stream)
        launch(['nginx', '-c', str(tmp/'nginx.conf'), '-g', 'daemon off;'], 'nginx')
        wait_port(443)
        out['settings']['address'] = '127.0.0.1'
        out['streamSettings']['tlsSettings']['certificates'] = [dict(certificateFile=str(tmp/'fullchain.pem'), usage='verify')]
        client = dict(log=dict(loglevel='debug'), inbounds=[
            dict(listen='127.0.0.1', port=18080, protocol='socks', settings={}),
            dict(listen='127.0.0.1', port=18082, protocol='dokodemo-door',
                 settings=dict(address='93.184.216.34', port=18083, network='udp'))], outbounds=[out])
        (tmp/'client.json').write_text(json.dumps(client))
        launch([XRAY, 'run', '-c', str(tmp/'client.json')], 'client')
        wait_port(18080)
        curl = ['curl', '-fsS', '--max-time', '25', '--noproxy', '',
                '--socks5-hostname', '127.0.0.1:18080', 'http://93.184.216.34:18081/']
        download = subprocess.run(curl, check=True, capture_output=True).stdout
        assert download == PAYLOAD, 'Download corrupted'
        upload = subprocess.run(curl + ['--data-binary', '@-'], input=PAYLOAD,
                                check=True, capture_output=True).stdout
        assert upload == hashlib.sha256(PAYLOAD).hexdigest().encode(), 'Upload corrupted'
        udp_echo = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        udp_echo.bind(('93.184.216.34', 18083))
        udp_echo.settimeout(15)
        def echo_udp():
            data, peer = udp_echo.recvfrom(65535)
            udp_echo.sendto(data, peer)
        threading.Thread(target=echo_udp, daemon=True).start()
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as udp:
            udp.settimeout(15)
            message = os.urandom(1000)
            udp.sendto(message, ('127.0.0.1', 18082))
            assert udp.recv(65535) == message, 'UDP corrupted'
        udp_echo.close()
        print('PASS MASQUE: empty API inbound, JSON endpoint/credentials, TLS/SNI/h2, 2 MiB upload/download, UDP echo')
    except Exception as error:
        if isinstance(error, subprocess.CalledProcessError):
            print('curl stderr:', error.stderr, 'output bytes:', len(error.stdout or b''))
        for path in tmp.glob('*.log'):
            print(path.name, path.read_text())
        raise
    finally:
        for process in reversed(processes):
            process.terminate()
        for process in reversed(processes):
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait()
        for log in logs:
            log.close()
server.shutdown()
