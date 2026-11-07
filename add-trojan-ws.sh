#!/usr/bin/env bash
set -Eeuo pipefail
umask 077
[[ $EUID == 0 && $# == 1 && $1 =~ ^(NL|RU|US)$ ]] || { echo "Usage: sudo bash add-trojan-ws.sh NL|RU|US" >&2; exit 2; }
d=$(mktemp -d)
trap 'rm -rf -- "$d"' EXIT
cat > "$d/persist.py" <<'SURGE_PY'
#!/usr/bin/python3
import fcntl, json, os, re, subprocess, sys, tempfile
from pathlib import Path

cfg = Path('/etc/nginx/conf.d/single443-web.conf')
store = Path('/etc/lazyproxy-surge-ws')
spec = store/'route.json'
state = Path('/etc/single443/state.json')
unit = 'lazyproxy-surge-ws'
marker = re.compile(r'^    # BEGIN LazyProxy Surge (NL|RU|US) WS\n    location = (/surge-ws-[a-f0-9]+) \{', re.M)

def need(condition, message):
    if not condition: raise RuntimeError(message)

def block(region, path):
    need(region in ('RU','NL','US') and re.fullmatch(r'/surge-ws-[0-9a-f]{8,64}',path),'Недопустимая метка или путь WS')
    return f'''    # BEGIN LazyProxy Surge {region} WS
    location = {path} {{
        proxy_pass http://127.0.0.1:10443;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_read_timeout 1h;
    }}
    # END LazyProxy Surge {region} WS
'''

def desired(text, data, live):
    need((live['ip'],live['domain'])==(data['ip'],data['domain']),'Изменился адрес сервера; проверьте профиль Surge')
    route=block(data['region'],data['path'])
    ws=live['ws_path'].rstrip('/')
    need(re.fullmatch(r'/[a-zA-Z0-9_/-]+',ws) and ws!=data['path'],'Нестандартный путь LazyProxy')
    anchor='    location = '+ws+' {\n        proxy_pass http://127.0.0.1:10001;'
    need(text.count(anchor)==1,'Изменился шаблон рабочего WS; запись отменена')
    clean=text.replace(route,'',1)
    need(not any(x in clean for x in ('# BEGIN LazyProxy Surge','# END LazyProxy Surge',data['path'])),'Конфликт или ручная правка WS; запись отменена')
    if clean!=text:
        need(route+anchor in text,'Блок WS перемещён; запись отменена')
        return text
    return text.replace(anchor,route+anchor,1)

def atomic(p, payload, mode):
    fd,tmp=tempfile.mkstemp(dir=p.parent)
    try:
        with os.fdopen(fd,'wb') as f:
            f.write(payload); os.fchmod(f.fileno(),mode); f.flush(); os.fsync(f.fileno())
        os.replace(tmp,p)
    finally:
        Path(tmp).unlink(missing_ok=True)

def main():
    os.umask(0o077)
    install=sys.argv[1:]==['--install']
    need(install or not sys.argv[1:],'Неизвестные аргументы')
    run=lambda *args:subprocess.run(args,check=True)
    with open('/run/lock/single443.lock','a') as guard:
        fcntl.flock(guard,fcntl.LOCK_EX | (fcntl.LOCK_NB if install else 0))
        need(not cfg.is_symlink() and cfg.is_file() and cfg.stat().st_uid==0,'Нестандартный nginx-конфиг')
        old=cfg.read_bytes(); text=old.decode(); live=json.loads(state.read_text())
        if install:
            matches=marker.findall(text)
            need(len(matches)==1,'Не найден единственный установленный Trojan WS на этом VPS')
            region,path=matches[0]
            data=dict(region=region,path=path,ip=live['ip'],domain=live['domain'])
            need(desired(text,data,live)==text,'Нет полного рабочего блока WS')
            store.mkdir(mode=0o700,exist_ok=True)
            need(not store.is_symlink() and store.stat().st_uid==0 and store.stat().st_mode & 0o077==0,'Небезопасные права каталога')
            need(not spec.exists() or json.loads(spec.read_text())==data,'Уже сохранён другой маршрут')
            run('nginx','-t')
            atomic(spec,json.dumps(data).encode(),0o600)
            print('Сохранён маршрут '+region)
            return
        data=json.loads(spec.read_text())
        new=desired(text,data,live).encode()
        if new==old:return
        run('nginx','-t')
        mode=cfg.stat().st_mode & 0o777
        need(cfg.read_bytes()==old,'Параллельная правка nginx')
        atomic(cfg,new,mode)
        try:
            run('nginx','-t')
            run('systemctl','reload','nginx')
        except BaseException:
            need(cfg.read_bytes()==new,'Параллельная правка; откат остановлен')
            atomic(cfg,old,mode)
            run('nginx','-t')
            if subprocess.run(['systemctl','is-active','--quiet','nginx']).returncode==0:run('systemctl','reload','nginx')
            raise
        print('Восстановлен маршрут '+data['region'])
if __name__=='__main__':main()
SURGE_PY
cat > "$d/setup.py" <<'SETUP_PY'
import argparse, json, os, re, runpy, secrets, socket, subprocess, sys
from pathlib import Path
import time

p=argparse.ArgumentParser(description='Add a local Trojan WS listener without changing existing inbounds.')
p.add_argument('region',choices=['RU','NL','US'])
region=p.parse_args().region
h=runpy.run_path(sys.argv[0].replace('setup.py','persist.py'))
need,desired,atomic=h['need'],h['desired'],h['atomic']
cfg,store,spec=h['cfg'],h['store'],h['spec']
run=lambda *cmd: subprocess.run(cmd,check=True)
port=10443
label=f'{region} Surge Trojan WS'

def stream(r):
    v=r.get('streamSettings')
    return json.loads(v) if isinstance(v,str) else v or {}

def match(rows):
    matches=[r for r in rows if not r.get('nodeId') and (r.get('remark')==label or r.get('port')==port)]
    if not matches: return None
    need(len(matches)==1,'Port or label conflict; refusing to change inbounds.')
    r=matches[0]; v=stream(r)
    need((r.get('remark'),r.get('protocol'),r.get('enable'),r.get('listen'),r.get('port'),
          v.get('network'),v.get('security','none'))==(label,'trojan',True,'127.0.0.1',port,'ws','none'),
         'Existing inbound differs; refusing to change it.')
    return (v.get('wsSettings') or {}).get('path') or ''

def main():
    import fcntl
    os.umask(0o077)
    with open('/run/lock/single443.lock','a') as guard:
        fcntl.flock(guard,fcntl.LOCK_EX|fcntl.LOCK_NB)
        engine=runpy.run_path('/opt/single443/lib/engine.py')
        s=engine['load'](); api=engine['API'](s)
        rows=api.call('inbounds/list'); path=match(rows)
        need(cfg.is_file() and not cfg.is_symlink(),'Unexpected nginx config.')
        old=cfg.read_bytes(); orig=old.decode()
        markers=h['marker'].findall(orig)
        store.mkdir(mode=0o700,exist_ok=True)
        need(not store.is_symlink() and store.stat().st_uid==0 and not(store.stat().st_mode & 0o077),'Unsafe state directory.')
        saved=json.loads(spec.read_text()) if spec.exists() else None
        if path is not None:
            need((region,path) in markers or (saved and saved.get('path')==path),'Unknown inbound: no matching managed nginx route.')
        elif saved:
            raise RuntimeError('Saved route has no matching inbound; check the panel before proceeding.')
        route=dict(region=region,path=path if path is not None else '/surge-ws-'+secrets.token_hex(12),ip=s['ip'],domain=s['domain'])
        need(saved is None or route==saved,'Saved route conflicts with requested region or VPS.')
        new=desired(orig,route,s).encode()
        run('nginx','-t')
        if path is None:
            with socket.socket() as sock: sock.bind(('127.0.0.1',port))
            email='surge-'+region.lower()+'-'+secrets.token_hex(5)
            pw=secrets.token_urlsafe(32)
            # Persist identity before the POST: an ambiguous API timeout must not cause duplicates.
            atomic(spec,json.dumps(route).encode(),0o600)
            api.call('inbounds/add',dict(remark=label,enable=True,listen='127.0.0.1',port=port,protocol='trojan',
                settings=json.dumps(dict(clients=[dict(email=email,password=pw,enable=True,subId=secrets.token_hex(12))])),
                streamSettings=json.dumps(dict(network='ws',security='none',wsSettings=dict(path=route['path']))),
                sniffing=json.dumps(dict(enabled=False)),excludeFromSub=True,total=0,expiryTime=0))
        need(match(api.call('inbounds/list'))==route['path'],'Inbound not confirmed by panel.')
        if saved is None and path is not None: atomic(spec,json.dumps(route).encode(),0o600)
        for _ in range(30):
            try:
                with socket.create_connection(('127.0.0.1',port),0.5): break
            except OSError: time.sleep(0.5)
        else: raise RuntimeError('Listener not ready; check Xray log. No inbound deleted.')
        changed=new!=old
        mode=cfg.stat().st_mode & 0o777
        if changed:
            need(cfg.read_bytes()==old,'Concurrent nginx edit.')
            atomic(cfg,new,mode)
        try:
            if changed: run('nginx','-t'); run('systemctl','reload','nginx')
            probe(s['ip'],s['domain'],route['path'])
        except BaseException:
            if changed and cfg.read_bytes()==new:
                atomic(cfg,old,mode); run('nginx','-t'); run('systemctl','reload','nginx')
            raise
        print(f"{label}: {s['domain']}:443, TLS, WS {route['path']}. Password: see client in 3x-ui.")

def probe(ip,domain,path):
    import ssl, base64, hashlib

    ctx=ssl.create_default_context()
    ctx.set_alpn_protocols(['http/1.1'])
    with socket.create_connection((ip,443),4) as sock, ctx.wrap_socket(sock,server_hostname=domain) as tls:
        key=base64.b64encode(os.urandom(16)).decode()
        tls.sendall((f'GET {path} HTTP/1.1\r\nHost: {domain}\r\nUpgrade: websocket\r\nConnection: Upgrade\r\nSec-WebSocket-Version: 13\r\nSec-WebSocket-Key: {key}\r\n\r\n').encode())
        f=tls.makefile('rb')
        need(f.readline(4096).split()[1:2]==[b'101'],'Внешний TLS/WS не вернул HTTP 101.')
        import http.client
        hdr=http.client.parse_headers(f)
        accept=base64.b64encode(hashlib.sha1((key+'258EAFA5-E914-47DA-95CA-C5AB0DC85B11').encode()).digest()).decode()
        need(hdr.get('Sec-WebSocket-Accept')==accept,'Неверный ответ WebSocket.')

if __name__=='__main__': main()
SETUP_PY
python3 "$d/setup.py" "$1"
install -m 0700 "$d/persist.py" /usr/local/sbin/lazyproxy-surge-ws
cat > "$d/service" <<'UNIT'
[Unit]
Description=Restore the existing Surge WebSocket route after LazyProxy render
After=nginx.service
[Service]
Type=oneshot
ExecStart=/usr/local/sbin/lazyproxy-surge-ws
TimeoutStartSec=infinity
UNIT
cat > "$d/path" <<'UNIT'
[Unit]
Description=Watch LazyProxy web configuration
[Path]
PathChanged=/etc/nginx/conf.d/single443-web.conf
[Install]
WantedBy=multi-user.target
UNIT
cat > "$d/timer" <<'UNIT'
[Unit]
Description=Recheck Surge WS at boot and after missed file events
[Timer]
OnBootSec=45s
OnUnitInactiveSec=5min
[Install]
WantedBy=timers.target
UNIT
for ext in service path timer; do
  install -m 0644 "$d/$ext" "/etc/systemd/system/lazyproxy-surge-ws.$ext"
done
systemctl daemon-reload
systemctl enable --now lazyproxy-surge-ws.path lazyproxy-surge-ws.timer
systemctl start lazyproxy-surge-ws.service
systemctl is-active --quiet lazyproxy-surge-ws.path
systemctl is-active --quiet lazyproxy-surge-ws.timer
echo 'Готово: автоматическое восстановление Trojan WS включено.'
