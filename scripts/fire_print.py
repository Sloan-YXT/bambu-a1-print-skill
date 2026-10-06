#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Fire an already-uploaded .3mf on the A1 via MQTT project_file (port 8883),
then print the first ~30s of printer acknowledgements.

Usage:  A1_IP=192.168.x.x python fire_print.py <remote_file.3mf>
Other MQTT commands (pause/resume/stop) follow the same pattern — see SKILL.md.
"""
import json, ssl, time, sys, warnings
warnings.filterwarnings('ignore')
import paho.mqtt.client as mqtt
from _auth import auth

FILE_REMOTE = sys.argv[1]
IP, CODE, SERIAL = auth()

events = []


def on_msg(c, u, msg):
    try:
        d = json.loads(msg.payload.decode(errors='replace'))
        p = d.get('print', {})
        if p:
            events.append((time.strftime('%H:%M:%S'),
                           {k: p.get(k) for k in ('command', 'result', 'reason', 'gcode_state',
                                                  'gcode_file', 'mc_percent', 'print_error',
                                                  'subtask_name') if k in p}))
    except Exception:
        pass


c = mqtt.Client(client_id='a1-lan-fire')
c.username_pw_set('bblp', CODE)
c.tls_set(cert_reqs=ssl.CERT_NONE)
c.tls_insecure_set(True)
c.on_message = on_msg
c.connect(IP, 8883, keepalive=20)
c.subscribe(f'device/{SERIAL}/report')
c.loop_start()
time.sleep(2)
payload = {
    'print': {
        'command': 'project_file',
        'sequence_id': '101',
        'url': f'ftp://{IP}/{FILE_REMOTE}',
        'param': 'Metadata/plate_1.gcode',
        'subtask_name': FILE_REMOTE.rsplit('.', 1)[0],
        'use_ams': False,
        'flow_calibration': True,
        'vibration_calibration': True,
        'layer_inspect': False,
        'timelapse': False,
        'md5': '',
    }
}
c.publish(f'device/{SERIAL}/request', json.dumps(payload))
print('project_file sent', flush=True)
for i in range(6):
    time.sleep(5)
    for t, e in events:
        print(t, e, flush=True)
    events.clear()
c.loop_stop()
c.disconnect()
