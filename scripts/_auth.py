#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Shared LAN auth helper for Bambu A1 scripts.

Resolution order:
  IP:     $A1_IP (required, or pass as CLI arg in each script)
  code:   $A1_ACCESS_CODE, else parsed from BambuStudio.conf
  serial: $A1_SERIAL, else parsed from BambuStudio.conf
"""
import os, re, sys, glob


def _conf_paths():
    home = os.path.expanduser('~')
    paths = [os.path.join(os.environ.get('APPDATA', ''), 'BambuStudio', 'BambuStudio.conf'),
             os.path.join(home, '.config', 'BambuStudio', 'BambuStudio.conf'),
             os.path.join(home, 'Library', 'Application Support', 'BambuStudio', 'BambuStudio.conf')]
    return [p for p in paths if p and os.path.exists(p)]


def _parse_conf():
    for p in _conf_paths():
        txt = open(p, encoding='utf-8', errors='replace').read()
        m = re.search(r'"access_code"\s*:\s*\{\s*"([0-9A-Fa-f]+)"\s*:\s*"([^"]+)"', txt)
        if m:
            return m.group(1), m.group(2)  # serial, code
    return None, None


def auth(ip=None):
    serial, code = None, None
    if not ip or not (os.environ.get('A1_ACCESS_CODE') and os.environ.get('A1_SERIAL')):
        serial, code = _parse_conf()
    ip = ip or os.environ.get('A1_IP')
    code = os.environ.get('A1_ACCESS_CODE') or code
    serial = os.environ.get('A1_SERIAL') or serial
    if not ip:
        sys.exit('A1_IP not set (export A1_IP=192.168.x.x or pass as arg)')
    if not code or not serial:
        sys.exit('access code / serial not found: set A1_ACCESS_CODE/A1_SERIAL or install BambuStudio once')
    return ip, code, serial
