"""Real VLESS/XHTTP upload/download through rendered SNI dispatcher and nginx.
Run in a disposable Linux network namespace; never against a user's services.
"""
import hashlib
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
with tempfile.TemporaryDirectory(prefix='xhttp-test-') as directory:
    tmp = Path(directory)
    processes = []
    logs = []
    def launch(args, name):
        log = (tmp / (name + '.log')).open('w')
        logs.append(log)
        process = subprocess.Popen(args, stdout=log, stderr=subprocess.STDOUT)
        processes.append(process)
        return process

    try:
        subprocess.run(['openssl', 'req', '-x509', '-newkey', 'rsa:2048', '-nodes',
                        '-days', '1', '-subj', '/CN=web.example.com',
                        '-addext', 'subjectAltName=DNS:web.example.com',
                        '-keyout', str(tmp/'privkey.pem'), '-out', str(tmp/'fullchain.pem')],
                       check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        subprocess.run([sys.executable, str(ROOT/'tests/render_fixtures.py'), str(tmp),
                        'A'*43, 'B'*43], check=True)
        fixture = json.loads((tmp/'xray.json').read_text())
        inbound = next(r for r in fixture['inbounds'] if r['port'] == 10002)
        mode = sys.argv[sys.argv.index('--mode') + 1] if '--mode' in sys.argv else 'stream-up'
        assert mode in ('stream-up', 'packet-up', 'stream-one')
        inbound['streamSettings']['xhttpSettings']['mode'] = mode
        config = dict(log=dict(loglevel='debug'), inbounds=[inbound],
                      outbounds=[dict(protocol='freedom')])
        (tmp/'server.json').write_text(json.dumps(config))
        launch([XRAY, 'run', '-c', str(tmp/'server.json')], 'server')
        wait_port(10002)
        if '--legacy' in sys.argv:
            web = (tmp/'web.conf').read_text()
            start = web.index('        # Preserve HTTP/2 streaming')
            end = web.index('\n    }', start)
            web = web[:start] + '''        proxy_pass http://127.0.0.1:10002;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header Connection "";
        proxy_request_buffering off;
        proxy_buffering off;
        proxy_read_timeout 1h;
        proxy_send_timeout 1h;''' + web[end:]
            (tmp/'web.conf').write_text(web)
        nginx_config = ('include /etc/nginx/modules-enabled/*.conf;\n'
                        f'pid {tmp}/nginx.pid; error_log {tmp}/nginx-error.log info;\n'
                        'events {}\n' + f'http {{ include {tmp}/web.conf; }}\n'
                        f'include {tmp}/stream.conf;\n')
        (tmp/'nginx.conf').write_text(nginx_config)
        launch(['nginx', '-c', str(tmp/'nginx.conf'), '-g', 'daemon off;'], 'nginx')
        wait_port(443)
        client = dict(
            log=dict(loglevel='debug'),
            inbounds=[dict(listen='127.0.0.1', port=18080, protocol='socks', settings={})],
            outbounds=[dict(protocol='vless', settings=dict(vnext=[
                dict(address='127.0.0.1', port=443, users=[
                    dict(id=inbound['settings']['clients'][0]['id'], encryption='none')])]),
                streamSettings=dict(network='xhttp', security='tls',
                    tlsSettings=dict(serverName='web.example.com', alpn=['h2'],
                        certificates=[dict(certificateFile=str(tmp/'fullchain.pem'), usage='verify')]),
                    xhttpSettings=inbound['streamSettings']['xhttpSettings']))])
        # Trust only the generated test certificate for this isolated client.
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
        if '--legacy' in sys.argv:
            raise AssertionError('Legacy defect no longer reproduced; review baseline')
        print(f'PASS: authenticated XHTTP {mode} via TLS/SNI/nginx, 2 MiB download and upload')
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
