# bambu-a1-print-skill

Bambu Lab A1 LAN-mode print pipeline for AI coding agents (Kimi Code / Claude Code / Codex) — and for humans who just want reliable CLI-driven prints.

拓竹 A1 局域网打印全流程技能：CLI 切片（不丢原生开机序列）→ FTPS 容错上传 → MQTT 开火与监控，外加一册用多个失败锅换来的故障学。给 Kimi Code / Claude Code / Codex(astra) 等 agent 直接当 skill 用，也可以纯人肉使用脚本。

## Why / 解决什么

- **OrcaSlicer CLI slices lose the A1's native start G-code.** The stock machine profile's `machine_start_gcode` is empty; the real ~12 KB sequence (G392 / purge / wipe / bed-level compensation) lives in a `template` file that the CLI does NOT merge. First layer comes out garbage. → `configs/machine_a1_native.json` inlines the full native sequence. Verified by reading the actual `plate_1.gcode`.
- **The BBL FTPS server drops the closing 226 ACK.** Naive ftplib uploads hang forever. → `scripts/upload_lenient.py` streams, hard-closes, then verifies size in a fresh session. (If the control channel hangs, power-cycle the printer — really unplug it.)
- **MQTT fire & one-line monitor** (`scripts/fire_print.py`, `scripts/monitor.py`), plus field-learned failure lessons (nozzle blob poisoning auto-level, AI-pause at fixed Z, first-layer adhesion triage order).

## Layout

```
SKILL.md                      # the skill body (Chinese, agent-agnostic)
configs/
  machine_a1_native.json      # A1 machine profile with native start/end G-code inlined
  process_v16_qual.json       # support-free-by-design quality recipe: raft0, brim_object_gap 0.15 (recommended)
  process_raft2.json          # legacy enclosure recipe: raft2 + support gap 0.2 + no fan first 3 layers
  filament_pla228_v14.json    # PLA 228/226C (first layer / rest), smoothest run to date
  filament_pla195.json        # PLA 220/218C, textured PEI 65C
scripts/
  _auth.py                    # IP/code/serial resolution (env vars or BambuStudio.conf), no hardcoded secrets
  upload_lenient.py           # FTPS upload with lost-226 tolerance + fresh-session size verify
  fire_print.py               # MQTT project_file fire + ack watch
  monitor.py                  # one-line MQTT status probe (cron-friendly)
```

## Use as an agent skill

- **Kimi Code**: copy `SKILL.md` to `.agents/skills/bambu-a1-print/SKILL.md` (keep `configs/` and `scripts/` next to it or reference this repo path).
- **Claude Code**: copy to `.claude/skills/bambu-a1-print/SKILL.md`.
- **Codex / others**: paste `SKILL.md` into the prompt or reference it from `AGENTS.md`.

## Use by hand

```bash
export A1_IP=192.168.x.x          # access code/serial auto-read from BambuStudio.conf
orca-slicer --slice 1 part.stl \
  --load-settings "configs/machine_a1_native.json;configs/process_raft2.json" \
  --load-filaments "configs/filament_pla195.json" --export-3mf out.3mf
python scripts/upload_lenient.py out.3mf      # must end with UPLOAD_VERIFIED
python scripts/fire_print.py out.3mf          # fires Metadata/plate_1.gcode
python scripts/monitor.py                     # [A1] state=RUNNING pct=... 
```

Requires Python 3 + `paho-mqtt`. Verify the sliced artifact before firing (unzip the 3mf, check `Metadata/plate_1.gcode` for the G392 native header, raft lines, brim) — see SKILL.md §1.

## Notes

- Preset names carry a `(kimi)` suffix from the source setup; if you rename them, keep `compatible_printers` in all three JSONs mutually in sync or slicing fails with "process not compatible with printer".
- LAN mode only (printer set to LAN Only). Tested with OrcaSlicer CLI + Bambu A1 firmware 01.x.

## License

MIT — see LICENSE.
