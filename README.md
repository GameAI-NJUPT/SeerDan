# SeerDan

SeerDan 是一个掼蛋（GuanDan）决策模型。本仓库提供推理版的 SeerDan 策略网络、权重文件和启动脚本，用于配合 OpenGuanDan 引擎对局。

## 目录

```
.
├── ckpts/seerdan_policy.enc  # SeerDan 策略权重（加密归档，约 19 MB）
├── seerdan/                  # 推理代码（动作编码、规则基线、ws 客户端）
├── run_bot.py                # 启动单个座位
├── start_match.py            # 一键 4 座位演示（2 SeerDan + 2 规则）
├── start_match.sh            # start_match.py 的 shell 包装
└── requirements.txt
```

权重文件是加密归档：运行时在内存中解密并加载，仓库不包含明文模型文件、网络结构定义源码，也不能直接用 `torch.jit.load` 打开权重文件。

## 环境

- Python 3.9+
- 依赖：`pip install -r requirements.txt`（numpy、torch、websockets、cryptography）

## 启动 OpenGuanDan 引擎

SeerDan 通过 WebSocket 连接 OpenGuanDan 服务端（默认 `ws://127.0.0.1:8181`，HTTP 端口 3000）。

```bash
git clone https://github.com/GameAI-NJUPT/OpenGuanDan.git
cd OpenGuanDan
# Linux
chmod +x guandan-linux && ./guandan-linux
# Windows: .\guandan.exe
```

服务端启动后保持运行，另开终端进入本仓库。

## 一键对局（2 SeerDan + 2 规则）

```bash
python start_match.py
```

- 座位 0、2：SeerDan 策略（`ckpts/seerdan_policy.enc`）
- 座位 1、3：内置规则基线 `rule`
- 默认打 4 副牌演示（`--round 4`）；完整打到 A 请用大一点的 `--round`，例如 `--round 600`
- 每座位日志写入 `logs/seatN.log`

参数：

```bash
python start_match.py --url ws://127.0.0.1:8181 --round 4 --ckpt ckpts/seerdan_policy.enc
```

## 手动启动单个座位

```bash
# 座位 0：创建房间（打印 ROOM_ID）
python run_bot.py --seat 0

# 其他座位加入同一房间
python run_bot.py --seat 1 --room-id <ROOM_ID>
python run_bot.py --seat 2 --room-id <ROOM_ID>
python run_bot.py --seat 3 --room-id <ROOM_ID>
```
