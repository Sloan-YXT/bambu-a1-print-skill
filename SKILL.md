---
name: bambu-a1-print
description: Bambu A1 3D打印全流程（LAN模式）——正确的CLI切片配方、FTPS容错上传、MQTT开火监控，以及喷嘴料坨/预览镜像/CLI切片丢失原生序列等已踩过的坑。当需要在局域网内的A1上切片、上传、打印或排查打印故障时使用。
---

# Bambu A1 打印管线（LAN 模式）

约定：`<A1_IP>` = 打印机局域网 IP；访问码/序列号从本机 BambuStudio 配置读取（Windows: `%APPDATA%\BambuStudio\BambuStudio.conf`，Linux/macOS: `~/.config/BambuStudio/BambuStudio.conf`），也可用环境变量 `A1_IP` / `A1_ACCESS_CODE` / `A1_SERIAL` 显式指定。仓库脚本统一带 `_auth()`，不落任何硬编码凭据。

## 一、切片（最大的坑：CLI 会丢 A1 原生开机序列）

- Bambu 官方 machine 预设 `Bambu Lab A1 0.4 nozzle.json` 的 `machine_start_gcode` 是**空的**，真序列在 `... template machine_start_gcode.json`（约 12KB：G392/吐丝/擦拭/调平补偿/纹理板补偿）。OrcaSlicer CLI `--load-settings` **不会合并 template 文件** → 切出来的文件开机序列只剩 `G28+抬嘴`，第一层必然"乱喷"且 brim 类设置可能不生效。
- 正确做法：把 template 的 `machine_start_gcode`/`machine_end_gcode` **内联**进 machine json 再用（现成文件：`configs/machine_a1_native.json`，已内联 12KB 原生头，含 G392）。
- 切片命令（OrcaSlicer CLI）：
  `orca-slicer --slice 1 <stl> --load-settings "configs/machine_a1_native.json;configs/process_raft2.json" --load-filaments "configs/filament_pla195.json" --export-3mf out.3mf`
  - 自定义 machine/process/filament 预设名必须互相加入对方的 `compatible_printers`，否则报 "process not compatible with printer"（只给这一行，日志在输出目录 00000.log）。本仓库三个 json 的 compatible_printers 已互相对齐，改名时必须同步改。
- 机壳类大平面件配方（`configs/process_raft2.json`）：raft_layers=2、enable_support=1、support_on_build_plate_only=1、support_interface_spacing=0.2（默认0.5会在簧片起印点反复触发AI检测）、close_fan_the_first_x_layers=3、brim 依附着力 5-8mm（设了要验证真打出来）。
- **切完必须验 artifact 而不是信设置**（解 zip 读 `Metadata/plate_1.gcode`）：G392 原生头在不在、raft 走线在不在、brim 是否真有走线（`brim_type=auto` 可能一圈不打）、温度和层数。连续 6 锅失败的根因就是没做这一步。同理：任何"查看器/预览"的渲染都可能镜像或残缺，判断一律以物理产物（gcode 本体）为准。
- **支撑归零化设计 + `brim_object_gap`（2026-10-07 v1.6，最丝滑一锅）**：机壳类件优先在几何上设计成免支撑（卡扣倾角/自悬垂角收进可打印域），而不是调支撑参数去救。验证方法：解 3mf 读 `plate_1.gcode`，按 `; FEATURE: X` 标记分段统计挤出量（注意 OrcaSlicer 2.4.2 的标记是 `; FEATURE:`，不是 `;TYPE:`），Support 段必须为零——配置里 `enable_support=1` 没关系，几何不需要就一段不打（对照：同模型 v1.5 还有 233 段/308mm 支撑，v1.6 归零后全程零报错）。推荐预设 `configs/process_v16_qual.json`（raft_layers=0、brim_object_gap=0.15、wall_loops=4、infill 50%）+ `configs/filament_pla228_v14.json`（首层 228°C、其余 226°C）。**键名坑：OrcaSlicer 2.4.2 用的是 `brim_object_gap`，不是 `brim_separation`，写错键名静默不生效。**

## 二、上传（FTPS 990，隐式 TLS，BBL 服务器很脆）

- 先包 TLS 再讲话（`220 BBL-P003 FTP Server`），login bblp/访问码，`prot_p`，PASV 数据通道也走 TLS。
- **丢尾部 226 ACK 是常态**：storbinary 传完数据后等不到 226 会挂死——按"传完即硬关闭、开新会话 `size()` 核对字节数"判成功（`scripts/upload_lenient.py` 即此逻辑）。
- 卡死的会话会把打印机 FTP 服务拖垮（表现为能连 990 但数据通道不传/控制 TLS 握手超时）→ **真·断电重启打印机**（拔电源 10s，屏幕休眠不算重启）。别反复重试加重僵尸会话。

## 三、开火与监控（MQTT 8883）

- client：bblp/访问码，topic `device/<序列号>/{request,report}`。
- 命令：`project_file`（开火，url=`ftp://<A1_IP>/<file>`，param=`Metadata/plate_1.gcode`）/ `pause` / `resume` / `stop` / `pushall`（查状态）。脚本：`scripts/fire_print.py <已上传的3mf文件名>`；监控：`scripts/monitor.py`（单行状态，适合 cron）。
- `pushall`/`push_status` 间歇性返回全 None 是常态，多等几拍或重发即可；mc_percent 是进度主指标。
- 打印**完成后的"确定"只能屏幕点**，无 API。

## 四、故障学（全部实战学费）

1. **喷嘴料坨污染调平**：喷嘴挂料→自动调平（喷嘴当探头）测出假高度→全程隔空打印→料越缠越大。症状=板上一坨没有/乱喷。处理：220-240°C 镊子拔坨 → 手动挤出看出料是否笔直 → 重调平/重新打。
2. **AI 检测在同一 Z 反复自暂停+蜂鸣**：先查那个 Z 在印什么（算层段），大概率是簧片/支撑起印点的弱路径；支撑界面间距 0.5→0.2 有效，守夜式 resume 无效（同 Z 必复发）。
3. **第一层贴不上**：按 文件(gcode有没有brim/原生序列) → 喷嘴(有没有料坨) → 板(洗没洗/放没放平) → 料(受潮才轮到，多温度档位都失败过且同款料成功过就基本排除温度) 的顺序查，不要先调温度。
4. 打印机蜂鸣但报告正常：先看屏幕有无故障弹窗（会等你点"知道了"，期间每隔几分钟响一次）。

## 五、复用文件

- 切片预设：`configs/machine_a1_native.json` / `configs/process_v16_qual.json`(免支撑质检版，推荐) / `configs/process_raft2.json`(老 raft 配方，备查) / `configs/filament_pla228_v14.json`(228/226°C) / `configs/filament_pla195.json`
- 上传：`scripts/upload_lenient.py <本地3mf路径>`；开火：`scripts/fire_print.py <远端3mf文件名>`
- 状态探测：`scripts/monitor.py`
