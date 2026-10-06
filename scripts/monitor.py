#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""One-line A1 status probe (MQTT pushall), suitable for cron/watchdog use.

Usage:  A1_IP=192.168.x.x python monitor.py
Output: [A1] state=RUNNING pct=42% layer=87/210 remaining=63min nozzle=220C bed=65C err=0 job=foo
Note: pushall replies intermittently come back all-None — just re-ask.
"""
import json, ssl, time, warnings
warnings.filterwarnings('ignore')
import paho.mqtt.client as mqtt
from _auth import auth

IP, CODE, SERIAL = auth()

msgs = []


def on_msg(c, u, msg):
    try:
        msgs.append(json.loads(msg.payload.decode(errors='replace')).get('print', {}))
    except Exception:
        pass


c = mqtt.Client(client_id='a1-lan-monitor')
c.username_pw_set('bblp', CODE)
c.tls_set(cert_reqs=ssl.CERT_NONE)
c.tls_insecure_set(True)
c.on_message = on_msg
c.connect(IP, 8883, keepalive=20)
c.subscribe(f'device/{SERIAL}/report')
c.loop_start()
c.publish(f'device/{SERIAL}/request', json.dumps({'pushing': {'sequence_id': '9', 'command': 'pushall'}}))
time.sleep(6)
c.loop_stop()
c.disconnect()

pr = {}
for d in msgs:
    pr.update(d)
state = pr.get('gcode_state', '?')
pct = pr.get('mc_percent', '?')
lay = pr.get('layer_num', '?')
tot = pr.get('total_layer_num', '?')
rem = pr.get('mc_remaining_time', '?')
err = pr.get('print_error', 0)
nz = pr.get('nozzle_temper', '?')
bed = pr.get('bed_temper', '?')
sub = pr.get('subtask_name', '')
print(f'[A1] state={state} pct={pct}% layer={lay}/{tot} remaining={rem}min nozzle={nz}C bed={bed}C err={err} job={sub}')
