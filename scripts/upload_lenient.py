#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Upload a .3mf to the A1 over FTPS (implicit TLS, port 990), tolerating the
BBL server's lost-226 quirk: stream the file, hard-close, then verify the
remote size in a fresh session. If the control channel hangs, POWER-CYCLE the
printer (unplug 10s; screen sleep is NOT a reboot) — do not keep retrying.

Usage:  A1_IP=192.168.x.x python upload_lenient.py <local.3mf>
"""
import socket, ssl, ftplib, time, os, re, sys
from _auth import auth

LOCAL = sys.argv[1]
REMOTE = os.path.basename(LOCAL)
IP, CODE, _ = auth()

ctx = ssl.create_default_context(); ctx.check_hostname = False; ctx.verify_mode = ssl.CERT_NONE


def connect(timeout=12):
    raw = socket.create_connection((IP, 990), timeout=timeout)
    ss = ctx.wrap_socket(raw, server_hostname=IP); ss.settimeout(timeout)
    ftp = ftplib.FTP_TLS(context=ctx); ftp.sock = ss; ftp.af = ss.family
    ftp.file = ss.makefile('r', encoding='utf-8', errors='replace')
    ftp.getresp(); ftp.host = IP
    ftp.login('bblp', CODE); ftp.prot_p()
    return ftp, ss


size = os.path.getsize(LOCAL)
print(f'uploading {REMOTE} ({size} B)...', flush=True)
ftp, ss = connect()
resp = ftp.sendcmd('PASV')
mm = re.findall(r'(\d+),(\d+),(\d+),(\d+),(\d+),(\d+)', resp)[0]
h, p = '.'.join(mm[:4]), int(mm[4]) * 256 + int(mm[5])
dsock = ctx.wrap_socket(socket.create_connection((h, p), timeout=10), server_hostname=h)
ftp.putcmd(f'STOR {REMOTE}')
ss.settimeout(8)
try:
    r150 = ftp.getresp()
    print('control:', r150.strip(), flush=True)
except Exception as e:
    print('no 150 (continuing anyway):', e, flush=True)
sent = 0
t0 = time.time()
with open(LOCAL, 'rb') as fh:
    while True:
        chunk = fh.read(16384)
        if not chunk:
            break
        dsock.sendall(chunk)
        sent += len(chunk)
print(f'sent {sent}/{size} in {time.time() - t0:.1f}s', flush=True)
dsock.close()
try:
    ss.close()
except Exception:
    pass
assert sent == size, 'short transfer!'

time.sleep(3)
print('verifying via fresh session...', flush=True)
ftp2, ss2 = connect()
rs = ftp2.size(REMOTE)
print(f'remote size: {rs}  match: {rs == size}', flush=True)
try:
    ftp2.quit()
except Exception:
    pass
print('UPLOAD_VERIFIED' if rs == size else 'UPLOAD_MISMATCH')
