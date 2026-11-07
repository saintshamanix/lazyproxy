#!/usr/bin/env python3
"""Local LazyProxy / 3x-ui SQLite to Surge export. No third-party modules."""
import argparse, base64, http.client, ipaddress, json, os, re, socket, sqlite3, ssl, sys, tempfile, time, zlib
from pathlib import Path
from urllib.parse import parse_qs, quote, unquote, urlsplit

class Stop(Exception): pass

def need(ok, msg):
    if not ok: raise Stop(msg)

def host(value):
    need(isinstance(value, str) and re.fullmatch(r'[A-Za-z0-9.-]+',value)
         and all(re.fullmatch(r'[A-Za-z0-9](?:[A-Za-z0-9-]{0,61}[A-Za-z0-9])?', part)
                 for part in value.split('.')), 'Неподдерживаемое имя сервера.')
    return value

def subscription(d, token):
    addr=d['address']
    need(addr in ('127.0.0.1','::1') and isinstance(d['tls'],bool), 'Некорректный локальный адрес подписок.')
    name=host(d['host']); port=int(d['port'])
    path=d['main_path']
    need(isinstance(path,str) and re.fullmatch(r'/(?:[a-zA-Z0-9_.~-]+/)*',path)
         and re.fullmatch(r'[a-zA-Z0-9_.~-]+',token) and token not in ('.','..'), 'Неожиданный путь или ID подписки.')
    c=http.client.HTTPConnection(addr,port,timeout=12)
    try:
        c.connect()
        if d['tls']:
            c.sock=ssl.create_default_context().wrap_socket(c.sock,server_hostname=name)
        c.request('GET',path+quote(token,safe=''),headers={'Host':name+':'+str(port),'User-Agent':'v2rayN/7.0'})
        resp=c.getresponse()
        need(resp.status==200, 'Локальный сервис подписок вернул HTTP '+str(resp.status))
        data=resp.read(2097153)
        need(len(data)<=2097152,'Слишком большой ответ подписки.')
        return data
    finally: c.close()

def extract(data,auth):
    lines=data.strip().splitlines()
    if not any(b'://' in x for x in lines):
        b=b''.join(lines)
        lines=base64.b64decode(b+b'='*(-len(b)%4),altchars=b'-_',validate=True).splitlines()
    found=set()
    for line in lines:
        if not line.strip().lower().startswith((b'hysteria2://',b'hy2://')): continue
        u=urlsplit(line.strip().decode())
        if unquote(u.netloc.rpartition('@')[0])!=auth: continue
        addr=host(u.hostname)
        try: ip=ipaddress.ip_address(addr)
        except ValueError: ip=None
        need(not (ip and (ip.is_loopback or ip.is_unspecified)) and addr!='localhost','В подписке локальный адрес.')
        q=parse_qs(u.query,keep_blank_values=True)
        need(set(q)<={'sni','alpn','security','fp','insecure','allowInsecure'}
             and q.get('security',['tls'])==['tls'] and q.get('alpn',['h3'])==['h3']
             and all(q.get(k,['0']) in (['0'],['false']) for k in ('insecure','allowInsecure')),
             'Нестандартные параметры Hysteria2; экспорт стандартного профиля остановлен.')
        sni=q.get('sni') or [addr]
        need(len(sni)==1,'Неоднозначный SNI.')
        found.add((addr,u.port or 443,host(sni[0] or addr)))
    need(len(found)==1,'Нет единственного адреса Hysteria2 с auth выбранного клиента в его подписке.')
    need(re.fullmatch(r'[A-Za-z0-9._~+/=:@%-]+',auth),'Пароль содержит символы, требующие специального экранирования в Surge.')
    return found.pop()

def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--client', help='точный email/идентификатор клиента 3x-ui')
    ap.add_argument('--db',type=Path,default=Path('/etc/x-ui/x-ui.db'))
    a=ap.parse_args()
    os.umask(0o077)
    with sqlite3.connect(a.db.resolve().as_uri()+'?mode=ro',uri=True) as db:
        db.execute('PRAGMA query_only=ON')
        db.execute('BEGIN')
        rows=db.execute("""SELECT DISTINCT c.id,c.email FROM clients c
             JOIN client_inbounds ci ON ci.client_id=c.id JOIN inbounds i ON i.id=ci.inbound_id
             WHERE c.enable=1 AND i.enable=1 AND i.protocol='hysteria'
             AND COALESCE(i.node_id,0)=0 AND COALESCE(c.auth,'')<>'' AND COALESCE(c.sub_id,'')<>''
             AND (COALESCE(c.expiry_time,0)<=0 OR c.expiry_time>?) ORDER BY c.email""",
             (int(time.time()*1000),)).fetchall()
        need(rows,'Нет активных локальных клиентов Hysteria с подпиской.')
        if a.client is None:
            for n,(_,email) in enumerate(rows,1): print(n,ascii(email))
            s=input('Номер клиента: ').strip()
            need(s.isascii() and s.isdigit() and 1<=int(s)<=len(rows),'Неверный номер.')
            cid=rows[int(s)-1][0]
        else:
            matches=[i for i,email in rows if email==a.client]
            need(len(matches)==1,'Активный клиент с таким идентификатором не найден.')
            cid=matches[0]
        token,auth=db.execute('SELECT sub_id,auth FROM clients WHERE id=?',(cid,)).fetchone()
        need(db.execute('SELECT count(*) FROM clients WHERE sub_id=?',(token,)).fetchone()[0]==1,
             'Один ID подписки назначен нескольким клиентам.')
    d=json.loads(Path('/etc/single443/subscription.json').read_text())
    addr,port,sni=extract(subscription(d,token),auth)
    template=zlib.decompress(base64.b64decode(RULES)).decode()
    profile=('[General]\ndns-server = system\nipv6 = true\n\n[Proxy]\n'
             f'VPS-HY2 = hysteria2, {addr}, {port}, password={auth}, sni={sni}\n\n'
             '[Proxy Group]\nLazyProxy = select, VPS-HY2\n\n'+template)
    out=tempfile.NamedTemporaryFile(prefix='Surge-HY2-',suffix='.conf',dir='/root',delete=False)
    try:
        with out: out.write(profile.encode())
    except BaseException:
        os.unlink(out.name); raise
    print('Готовый профиль:',out.name)

RULES='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'
if __name__=='__main__':
    try: main()
    except Stop as err: sys.exit(str(err))
    except sqlite3.Error: sys.exit('Не удалось прочитать SQLite 3x-ui. Проверь путь, права и схему БД.')
    except (OSError,ValueError,KeyError,EOFError,http.client.HTTPException): sys.exit('Не удалось прочитать настройки LazyProxy или получить и разобрать локальную подписку. Файл не создан.')
