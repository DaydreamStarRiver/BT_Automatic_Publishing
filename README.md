# 🎬 BT 自动发布系统 (BT Auto Publishing System)

> **v2.1 - Web 面板版** | 本地视频文件自动扫描、Torrent 生成、一键发布到 BT 站 + Web 管理面板

[![Python 3.10+](https://img.shields.io/badge/Python-3.10%2B-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

---

## 📖 目录

- [项目简介](#项目简介)
- [版本演进史](#版本演进史)
- [✨ 核心特性](#-核心特性)
- [🏗️ 系统架构](#️-系统架构)
- [📦 快速开始](#-快速开始)
- [⚙️ 配置说明](#️-配置说明)
- [🔄 处理流程](#-处理流程)
- [📊 任务状态机](#-任务状态机)
- [🔁 重试机制](#-重试机制)
- [💾 断点恢复](#-断点恢复)
- [🎮 使用指南](#-使用指南)
- [📁 项目结构](#-项目结构)
- [🔧 核心模块](#-核心模块)
- [📝 日志示例](#-日志示例)
- [❓ 常见问题](#-常见问题)
- [🛠️ 技术栈](#️-技术栈)

---

## 项目简介

本项目是一个 **7×24 小时无人值守的 BT 资源自动发布系统**，能够：

- 🔍 **自动监控** 指定文件夹中的新视频文件
- 📦 **自动生成** Torrent 种子文件（支持 40+ Tracker）
- 🚀 **自动发布** 到主流 BT 站点（通过 OKP 工具）
- 🔄 **智能重试** 发布失败时自动重试（最多 3 次）
- 💾 **断点恢复** 程序重启后继续未完成任务
- 📊 **全程追踪** 完整的任务状态记录和统计

### 适用场景

- 动画/视频资源批量发布
- PT 站点自动化维护
- 长期运行的发布任务队列

---

## 版本演进史

### v1.0 - MVP 基础版 ✅

**核心功能：**
- ✅ Watchdog 文件夹监控
- ✅ 视频信息提取（pymediainfo）
- ✅ MD5 重复检测
- ✅ JSON 任务生成

**架构：** 线性同步处理

---

### v1.1 - Torrent + OKP 集成版 ✅

**新增功能：**
- ✅ Torrent 生成（torf 库）
- ✅ OKP 一键发布集成
- ✅ 多 Tracker 支持（42 个）

**关键决策：**
- 选择 `torf` 而非 `qbittorrent-api`（后者无法创建 torrent）
- 基于 OKP GitHub 官方文档实现 CLI 调用

---

### v1.2 - Bug 修复 & 可控发布版 ✅

**修复的问题：**

| 问题 | 解决方案 |
|------|---------|
| Windows 控制台乱码 | 多编码自动检测（utf-8 → gbk → gb2312 → gb18030） |
| torf `.path` 属性错误 | 改用 `.name` 或 `str()` |
| basedpyright 类型注解错误 | 移除所有类型注解 |
| lambda 回调参数不匹配 | `lambda *args, **kwargs: None` |
| OKP 找不到可执行文件 | 智能路径搜索（6 个位置） |

**新增功能：**
- ✅ 预览模式（preview_only）
- ✅ 自动确认模式（auto_confirm）
- ✅ 三种运行模式切换
- ✅ 结构化日志输出

---

### v2.1 - Web 面板版 ⭐ 当前版本

**新增功能：**

| 特性 | 说明 |
|------|------|
| 🆕 **Web 管理面板** | FastAPI + 单文件前端，零外部依赖 |
| 🆕 **REST API** | 完整的任务 CRUD、日志流（SSE）、手动触发 |
| 🆕 **实时日志** | Server-Sent Events 推送，按级别过滤 |
| 🆕 **任务操作** | 通过面板重试/删除/手动触发任务 |

**访问方式：** 启动后打开 `http://localhost:8080`

---

### v2.0 - 队列架构版 ✅

**重大重构：**

| 特性 | 说明 |
|------|------|
| 🆕 任务队列系统 | Queue + Worker 异步架构 |
| 🆕 状态机驱动 | 7 种显式状态转换 |
| 🆕 自动重试机制 | 指数退避策略（10s → 20s → 30s） |
| 🆕 JSON 持久化 | 断点恢复支持 |
| 🆕 统计报表 | 成功/失败/重试统计 |
| 🆕 优雅关闭 | Ctrl+C 安全退出 |

**架构升级：** 同步阻塞 → 异步队列

---

## ✨ 核心特性

### 🎯 核心能力

```
┌─────────────────────────────────────────────────────────────┐
│                     v2.1 功能矩阵                            │
├──────┬──────────────────────────────────────────────┤
│ 📂 文件监控   │ watchdog 实时监控，支持 .mkv/.mp4/.avi       │
│ 📦 Torrent   │ torf 生成，支持 40+ Tracker                  │
│ 🚀 自动发布  │ OKP 集成，支持多站点同时发布                   │
│ 🔄 重试机制  │ 失败自动重试（最多 3 次，指数退避）            │
│ 💾 断点恢复  │ JSON 持久化，重启后恢复未完成任务              │
│ 👁️ 预览模式  │ 发布前查看 torrent 信息                      │
│ 📊 状态追踪  │ 7 种状态完整记录                              │
│ 📈 统计报表  │ 成功/失败/进行中实时统计                      │
│ 🛡️ 编码修复  │ Windows 控制台完美显示中文                    │
│ ⏹️ 优雅关闭  │ Ctrl+C 安全退出并保存状态                    │
│ 🌐 Web 面板  │ 浏览器管理任务/查看日志/手动操作              │
│ 🔌 REST API  │ 完整的 HTTP 接口，可远程控制                  │
└──────┴──────────────────────────────────────────────┘
```

### 🎬 三种运行模式

| 模式 | 配置 | 效果 |
|------|------|------|
| **预览模式** | `okp_preview_only: true` | 仅展示信息，不执行发布 |
| **交互模式** | `okp_auto_confirm: false` | 手动确认每个发布步骤 |
| **自动模式** ⭐ | `okp_auto_confirm: true` | 全自动执行，无人值守 |

---

## 🏗️ 系统架构

### 架构图（v2.0）

```
┌─────────────────────────────────────────────────────────────────┐
│                    BT 自动发布系统 v2.0                          │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌────────────┐                                                │
│  │  main.py   │ ← 主入口，启动所有组件                           │
│  └─────┬──────┘                                                │
│        │                                                        │
│        ▼                                                        │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │                    系统初始化                             │   │
│  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────────┐  │   │
│  │  │ TaskQueue   │  │ TaskWorker  │  │    Watcher      │  │   │
│  │  │ (队列管理)   │  │ (执行引擎)   │  │  (文件监控)     │  │   │
│  │  └──────┬──────┘  └──────┬──────┘  └────────┬────────┘  │   │
│  └─────────┼────────────────┼──────────────────┼───────────┘   │
│            │                │                  │               │
│            ▼                ▼                  ▼               │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │                 TaskPersistence (JSON)                   │   │
│  │                   data/tasks.json                        │   │
│  └─────────────────────────────────────────────────────────┘   │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘

                         运行时数据流

┌──────────┐     ┌──────────────┐     ┌──────────────┐
│ Watcher  │────▶│  TaskQueue   │────▶│  TaskWorker  │
│ (发现文件) │     │  (排队等待)   │     │  (状态机引擎)  │
└──────────┘     └──────────────┘     └──────┬───────┘
                                               │
                                    ┌──────────┼──────────┐
                                    ▼          ▼          ▼
                               ┌────────┐ ┌────────┐ ┌────────┐
                               │Torrent │ │  OKP   │ │Scanner │
                               │Builder │ │Executor│ │ Probe  │
                               └────────┘ └────────┘ └────────┘
```

### 组件职责

| 组件 | 职责 | 特性 |
|------|------|------|
| **Watcher** | 监控文件夹，发现新视频 | 只负责入队，不阻塞 |
| **TaskQueue** | 管理任务队列 | 去重、持久化、断点恢复 |
| **TaskWorker** | 执行任务（状态机驱动） | 单线程顺序处理 |
| **TaskPersistence** | JSON 存储 | 线程安全、实时写入 |

---

## 📦 快速开始

### 1️⃣ 环境要求

- Python 3.10+
- Windows / Linux / macOS
- （可选）OKP 工具用于 BT 发布

### 2️⃣ 安装依赖

```bash
git clone <your-repo-url>
cd BT_Automatic_Publishing

pip install -r requirements.txt
```

**核心依赖：**

```
watchdog>=4.0.0       # 文件夹监控
pymediainfo>=6.1.0    # 视频信息提取
torf>=4.2.0           # Torrent 生成
PyYAML>=6.0           # 配置文件解析
fastapi>=0.110.0      # Web 面板后端（v2.1 新增）
uvicorn>=0.29.0       # ASGI 服务器（v2.1 新增）
```

> **提示：** 如果不需要 Web 面板，可以不安装 fastapi/uvicorn，设置 `web_enabled: false` 即可。

### 3️⃣ 配置文件

编辑 `config.yaml`：

```yaml
# ========== 基础配置 ==========
watch_dir: ./data/watch            # 监控目录
output_torrent_dir: ./data/torrents # Torrent 输出目录
log_dir: ./logs                     # 日志目录

# ========== Tracker 配置 ==========
tracker_urls:
  - http://open.acgtracker.com:1096/announce
  - http://nyaa.tracker.wf:7777/announce
  - # ... 更多 tracker（已内置 42 个）

# ========== OKP 发布配置 ==========
okp_path: null                      # OKP 路径（null=自动查找）
okp_setting_path: null              # setting.toml 路径
okp_cookies_path: null              # cookies.txt 路径
okp_timeout: 300                    # 超时时间（秒）
okp_auto_confirm: true              # true=自动发布 false=手动确认
okp_preview_only: false             # true=仅预览不发布

# ========== 视频格式 ==========
video_extensions:
  - .mkv
  - .mp4
  - .avi
```

### 4️⃣ 启动系统

```bash
python main.py
```

启动成功后：
- 控制台会显示 **🌐 Web 面板地址**（默认 `http://localhost:8080`）
- 浏览器打开即可看到管理面板

### 5️⃣ 测试

将视频文件放入 `data/watch/` 目录，观察日志输出。

---

## ⚙️ 配置说明

### 完整配置项

| 配置项 | 类型 | 默认值 | 说明 |
|--------|------|--------|------|
| `watch_dir` | string | `./data/watch` | 监控目录路径 |
| `output_torrent_dir` | string | `./data/torrents` | Torrent 输出目录 |
| `processed_dir` | string | `./data/processed` | 已处理文件目录 |
| `log_dir` | string | `./logs` | 日志存储目录 |
| `db_path` | string | `./data/processed_files.json` | MD5 数据库路径 |
| `tracker_urls` | list | 42个Tracker | Announce URL 列表 |
| `okp_path` | string/null | `null` | OKP 可执行文件路径 |
| `okp_setting_path` | string/null | `null` | OKP 配置文件路径 |
| `okp_cookies_path` | string/null | `null` | Cookie 文件路径 |
| `okp_timeout` | int | `300` | OKP 执行超时（秒） |
| `okp_auto_confirm` | bool | `true` | 是否自动确认（-y 参数） |
| `okp_preview_only` | bool | `false` | 是否仅预览不发布 |
| `video_extensions` | list | [.mkv,.mp4,.avi] | 支持的视频格式 |
| `web_enabled` | bool | `true` | 是否启用 Web 面板（v2.1 新增） |
| `web_host` | string | `"0.0.0.0"` | Web 面板监听地址 |
| `web_port` | int | `8080` | Web 面板端口号 |

### OKP 配置详解

#### 下载 OKP

从 GitHub 下载最新版本：
```bash
# 下载地址
https://github.com/AmusementClub/OKP/releases
```

将 `OKP.Core.exe` 放入以下任一位置（按优先级）：
1. `config.yaml` 中 `okp_path` 指定的路径
2. 项目根目录
3. `tools/` 子目录
4. 系统 PATH 环境变量

#### 导出 Cookie

1. 安装 Chrome 扩展 **"Get cookies.txt LOCALLY"**
2. 登录目标 BT 站点
3. 点击扩展图标 → Export → 保存为 `cookies.txt`
4. 将文件放入项目目录或配置 `okp_cookies_path`

#### OKP CLI 参数

```
用法: OKP.Core <torrent_file> [选项]

选项:
  -s, --setting <file>     指定配置文件 (默认: setting.toml)
  --cookies <file>         指定 Cookie 文件
  -y, --no_reaction        跳过所有需要回车的步骤
  --allow_skip             登录失败时跳过该站点
  -l, --log_level <level>  日志级别 (Debug/Info/Verbose)
```

---

## 🔄 处理流程

### 完整生命周期

```
视频文件进入 data/watch/
         │
         ▼
    ┌─────────────┐
    │  Watcher    │  检测到新文件 (.mkv/.mp4/.avi)
    │  发现文件   │
    └──────┬──────┘
           │ 创建 Task 对象
           ▼
    ┌─────────────┐
    │  TaskQueue  │  入队（去重检查）
    │  排队等待   │
    └──────┬──────┘
           │ Worker 取出任务
           ▼
    ┌─────────────────────────────────────────────┐
    │              TaskWorker (状态机)              │
    │                                             │
    │  NEW                                        │
    │   │                                         │
    │   ├─▶ TORRENT_CREATING                      │
    │   │     ├─ 提取视频信息 (Probe)              │
    │   │     ├─ 生成 Torrent (TorrentBuilder)     │
    │   │     └─▶ TORRENT_CREATED                 │
    │   │           │                             │
    │   │           ▼                             │
    │   │      UPLOADING                          │
    │   │        ├─ 调用 OKP (OKPExecutor)        │
    │   │        │                               │
    │   │        ├──▶ SUCCESS ✅                  │
    │   │        │                               │
    │   │        └──▶ FAILED ⚠️                  │
    │   │              │                         │
    │   │              ├── retry_count < 3        │
    │   │              │   └─ 延迟后重新入队       │
    │   │              │                         │
    │   │              └── retry_count >= 3       │
    │   │                  └─▶ PERMANENT_FAILED ❌│
    │   │                                         │
    │   └─ (任何阶段严重错误)                      │
    │       └─▶ PERMANENT_FAILED ❌               │
    │                                             │
    └─────────────────────────────────────────────┘
```

### 各阶段详细说明

#### 阶段 1：文件发现（Watcher）

```python
# watcher.py - on_created()
1. 检测到新文件
2. 验证扩展名（.mkv/.mp4/.avi）
3. 等待 1 秒（确保文件写入完成）
4. 生成 Task ID（MD5 前 12 位）
5. 创建 Task 对象（status=NEW）
6. 放入 TaskQueue（去重检查）
```

#### 阶段 2：Torrent 生成（Worker - _handle_new_task）

```python
# task_worker.py - _handle_new_task()
1. 状态: NEW → TORRENT_CREATING
2. 检查文件是否存在
3. 检查是否已处理（MD5 去重）
4. 提取视频信息（分辨率、编码、时长、大小）
5. 标准化任务格式
6. 生成 Torrent 文件（含 42 个 Tracker）
7. 状态: TORRENT_CREATING → TORRENT_CREATED
8. 标记为已处理（写入 processed_files.json）
```

#### 阶段 3：OKP 发布（Worker - _handle_upload）

```python
# task_worker.py - _handle_upload()
1. 状态: TORRENT_CREATED → UPLOADING
2. 解析 Torrent 信息（用于预览日志）
3. 构建 OKP 命令行参数
4. 调用 subprocess.run() 执行 OKP
5. 解码输出（多编码自动检测）
6. 判断结果：
   - success → SUCCESS
   - failed → FAILED（触发重试或永久失败）
```

---

## 📊 任务状态机

### 状态定义（枚举）

```python
class TaskStatus(Enum):
    NEW                = "new"                  # 新任务，待处理
    TORRENT_CREATING   = "torrent_creating"     # 正在生成 Torrent
    TORRENT_CREATED    = "torrent_created"      # Torrent 已生成
    UPLOADING          = "uploading"            # 正在调用 OKP
    SUCCESS            = "success"              # ✅ 成功完成
    FAILED             = "failed"               # ⚠️ 失败（可重试）
    PERMANENT_FAILED   = "permanent_failed"     # ❌ 永久失败
```

### 状态转换图

```
                    ┌──────────────────────────────────────┐
                    │                                      │
                    ▼                                      │
  ┌──────┐   生成Torrent   ┌─────────────────┐   上传OKP  ┌──────────┐
  │ NEW  │ ─────────────▶ │ TORRENT_CREATED │ ─────────▶ │UPLOADING │
  └──┬───┘                └────────┬────────┘            └────┬─────┘
     │                             │                          │
     │  文件不存在/                │  Torrent 生成失败        │
     │  信息提取失败               │                          │
     │                             │                          │
     ▼                             ▼                          │
┌─────────────┐             ┌─────────────┐                  │
│PERMANENT_   │             │PERMANENT_   │                  │
│FAILED       │             │FAILED       │                  │
└─────────────┘             └─────────────┘                  │
                                                          │ 成功
                                                          ▼
                                                    ┌──────────┐
                                                    │ SUCCESS  │
                                                    └──────────┘

                                                          │ 失败
                                                          ▼
                                                     ┌──────────┐
                                                     │ FAILED   │
                                                     └────┬─────┘
                                                          │
                                            ┌─────────────┴────────────┐
                                            │                          │
                                     retry < max_retries         retry >= max_retries
                                            │                          │
                                            ▼                          ▼
                                    ┌─────────────┐          ┌─────────────┐
                                    │  延迟重试    │          │PERMANENT_   │
                                    │ (重新入队)   │          │FAILED       │
                                    └─────────────┘          └─────────────┘
```

### 状态转换规则

| 当前状态 | 触发条件 | 目标状态 | 说明 |
|---------|---------|---------|------|
| NEW | Worker 取出任务 | TORRENT_CREATING | 开始处理 |
| TORRENT_CREATING | Torrent 生成成功 | TORRENT_CREATED | 准备上传 |
| TORRENT_CREATING | 文件不存在/提取失败 | PERMANENT_FAILED | 致命错误 |
| TORRENT_CREATED | 开始调用 OKP | UPLOADING | 上传中 |
| UPLOADING | OKP 返回成功 | SUCCESS | 完成 ✅ |
| UPLOADING | OKP 返回失败 | FAILED | 可重试 |
| FAILED | retry_count < max_retries | FAILED（延迟后重新入队） | 等待重试 |
| FAILED | retry_count >= max_retries | PERMANENT_FAILED | 超过最大次数 ❌ |

---

## 🔁 重试机制

### 重试规则

| 属性 | 值 | 说明 |
|------|-----|------|
| 最大重试次数 | `3` 次 | 可在代码中修改 `Task.max_retries` |
| 重试对象 | **仅 OKP 上传失败** | Torrent 生成失败直接终止 |
| 延迟策略 | **指数退避** | 10s → 20s → 30s |
| 最大延迟 | `30` 秒 | 防止无限等待 |

### 延迟计算公式

```python
delay = min(10 * (retry_count + 1), 30)

# 第 1 次失败: delay = 10 * 1 = 10 秒
# 第 2 次失败: delay = 10 * 2 = 20 秒
# 第 3 次失败: delay = 10 * 3 = 30 秒
# 第 4 次失败: → PERMANENT_FAILED
```

### 重试流程图

```
OKP 上传失败
     │
     ▼
retry_count += 1
     │
     ▼
retry_count < max_retries?
     │
   ┌─┴─┐
   │Yes│  ─────────────────────────┐
   └───┘                           │
     │                              ▼
     │                        计算延迟时间
     │                              │
     │                              ▼
     │                        启动延迟线程
     │                       (不阻塞主队列)
     │                              │
     │                         sleep(delay)
     │                              │
     │                              ▼
     │                        重新放入队列
     │                              │
     └──────────────────────────────┘
     
   ┌─┴─┐
   │No │
   └───┘
     │
     ▼
标记为 PERMANENT_FAILED
```

---

## 💾 断点恢复

### 工作原理

程序每次状态变化都会立即写入 `data/tasks.json`：

```json
{
  "A1B2C3D4E5F6": {
    "id": "A1B2C3D4E5F6",
    "video_path": "D:/videos/test.mp4",
    "torrent_path": "data/torrents/test.torrent",
    "status": "failed",
    "retry_count": 1,
    "max_retries": 3,
    "error_message": "OKP 登录失败",
    "created_at": "2026-01-15T10:30:00",
    "updated_at": "2026-01-15T10:35:00"
  }
}
```

### 启动时恢复逻辑

```python
def _recover_pending_tasks(self):
    pending_tasks = self.persistence.get_pending_tasks()
    
    for task in pending_tasks:
        if task.status == FAILED and task.can_retry():
            # 情况1: 失败任务 → 准备重试
            logger.info(f"[{task.id}] 恢复失败任务 - 重试 {task.retry_count + 1}/{task.max_repeats}")
            self._queue.put(task)
            
        elif task.status in [NEW, CREATING, CREATED, UPLOADING]:
            # 情况2: 中断的任务 → 标记为失败后重试
            task.update_status(FAILED, "程序中断，重新排队")
            self._queue.put(task)
            
        # SUCCESS 和 PERMANENT_FAILED 不恢复
```

### 恢复的场景

| 场景 | 行为 |
|------|------|
| 任务正在生成 Torrent | 标记为 FAILED，重新从头开始 |
| 任务正在上传 OKP | 标记为 FAILED，从上传阶段重试 |
| 任务已失败且可重试 | 直接重新入队 |
| 任务已成功 | 跳过（不重复处理） |
| 任务永久失败 | 跳过（需手动干预） |

### 手动干预

如果想重试永久失败的任务：

1. 编辑 `data/tasks.json`
2. 找到目标任务
3. 修改：
   ```json
   {
     "status": "failed",
     "retry_count": 0,
     "error_message": null
   }
   ```
4. 重启程序

---

## 🎮 使用指南

### 日常操作

#### 启动系统

```bash
# 前台运行（推荐调试时使用）
python main.py

# 后台运行（Windows CMD）
start /b python main.py > log.txt 2>&1

# 后台运行（PowerShell）
Start-Process -FilePath "python" -ArgumentList "main.py" -WindowStyle Hidden
```

#### 停止系统

```bash
# 优雅关闭（推荐）
Ctrl+C

# 输出示例：
# ⏹️  收到停止信号，正在优雅关闭...
# ⏹️  正在停止 Worker...
# 📊 任务统计:
#   ✅ 成功: 5
#   ⚠️  失败（可重试）: 1
#   📋 总计: 6 个任务
# 👋 系统已停止
```

#### 查看任务状态

```bash
# 方法1: 直接查看 JSON
type data\tasks.json

# 方法2: Python 解析
python -c "import json; tasks=json.load(open('data/tasks.json','r',encoding='utf-8')); print(f'总计 {len(tasks)} 个任务')"

# 方法3: 查看日志
type logs\video_scanner.log
```

### 模式切换

#### 预览模式（测试用）

```yaml
# config.yaml
okp_preview_only: true
okp_auto_confirm: true
```

**效果：** 只展示 Torrent 信息，不实际调用 OKP

#### 交互模式（调试用）

```yaml
okp_preview_only: false
okp_auto_confirm: false
```

**效果：** OKP 会提示"是否继续？"，需手动按 Enter

#### 自动模式（生产环境）⭐

```yaml
okp_preview_only: false
okp_auto_confirm: true
```

**效果：** 全自动执行，无需人工干预

---

## 🌐 Web 管理面板（v2.1 新功能）

### 功能概览

| 页面 | 说明 |
|------|------|
| **仪表盘** | 任务统计（成功/失败/队列中）+ 近期任务 |
| **任务列表** | 分页、状态过滤、搜索，支持重试/删除操作 |
| **实时日志** | SSE 推送，按 INFO/WARN/ERROR 过滤，自动滚动 |
| **配置查看** | config.yaml 内容只读展示 |

### 访问地址

启动程序后控制台会显示：
```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  🌐  Web 面板地址: http://localhost:8080
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

### REST API

面板底层提供完整 API，也可直接调用：

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/status` | 系统状态 + 任务统计 |
| GET | `/api/tasks` | 任务列表（支持 `?status=xxx` 过滤） |
| GET | `/api/tasks/{id}` | 单个任务详情 |
| POST | `/api/tasks/{id}/retry` | 手动重试任务 |
| DELETE | `/api/tasks/{id}` | 删除任务记录 |
| POST | `/api/tasks/trigger` | 手动触发处理视频文件 |
| POST | `/api/tasks/clear_failed` | 清除所有永久失败任务 |
| GET | `/api/logs` | 最近日志（支持 `?level=ERROR` 过滤） |
| GET | `/api/logs/stream` | SSE 实时日志流 |
| GET | `/api/logs/file` | 读取日志文件尾部 |
| GET | `/api/config` | 当前配置（脱敏） |

**手动触发示例：**
```bash
curl -X POST http://localhost:8080/api/tasks/trigger \
  -H "Content-Type: application/json" \
  -d '{"video_path": "D:/videos/test.mp4"}'
```

### 前端技术说明

- **零外部依赖：** 单文件 HTML，内嵌 CSS + JS，不需要 npm/CDN/Node.js
- **离线友好：** 直接打包进 Docker 镜像即可，NAS 无网络也能用
- **实时通信：** 使用 Server-Sent Events (SSE)，无需 WebSocket

---

## 📁 项目结构

```
BT_Automatic_Publishing/
│
├── main.py                          # 🚀 主程序入口（v2.1）
├── config.yaml                      # ⚙️ 配置文件
├── requirements.txt                 # 📦 依赖列表
├── README.md                        # 📖 本文档
│
├── src/
│   ├── __init__.py
│   ├── config.py                    # 配置加载器（YAML）
│   ├── logger.py                    # 日志系统（双处理器）
│   │
│   ├── web/                         # 🌐 v2.1 新增：Web 面板
│   │   ├── __init__.py
│   │   ├── api.py                   # FastAPI 后端 + REST API + SSE
│   │   └── panel.html               # 前端面板（单文件，零依赖）
│   │
│   └── core/
│       ├── __init__.py
│       │
│       │  🆕 v2.0 新增模块
│       ├── task_model.py            # 📋 Task 数据模型 + 状态枚举
│       ├── task_persistence.py      # 💾 JSON 持久化存储
│       ├── task_queue.py            # 📦 任务队列管理器
│       ├── task_worker.py           # ⚙️ Worker 执行引擎（状态机）
│       │
│       │  📝 v1.x 核心模块
│       ├── watcher.py               # 👁️ 文件夹监控（v2.0 改造）
│       ├── scanner.py               # 🔍 MD5 重复检测
│       ├── probe.py                 # 🎬 视频信息提取
│       ├── normalizer.py            # 📐 任务标准化
│       ├── planner.py               # 📋 任务规划器（旧版流程）
│       ├── torrent_builder.py       # 📦 Torrent 生成器（torf）
│       └── executor_okp.py          # 🚀 OKP 调用执行器
│
└── data/
    ├── watch/                       # 📂 监控目录（放视频文件这里）
    ├── torrents/                    # 📂 Torrent 输出目录
    ├── processed/                   # 📂 已处理文件目录
    ├── logs/                        # 📂 日志存储目录
    ├── tasks.json                   # 💾 🆕 任务持久化数据库
    └── processed_files.json         # 🔐 MD5 去重数据库
```

---

## 🔧 核心模块

### 1️⃣ Task Model（任务模型）

**文件：** [src/core/task_model.py](src/core/task_model.py)

```python
@dataclass
class Task:
    id: str                          # 唯一标识（MD5[:12].upper()）
    video_path: str                  # 视频文件绝对路径
    torrent_path: Optional[str]      # 生成的 torrent 路径
    status: TaskStatus               # 当前状态（枚举）
    retry_count: int = 0             # 已重试次数
    max_retries: int = 3             # 最大重试次数
    error_message: Optional[str]     # 最后一次错误信息
    created_at: str                  # ISO 格式创建时间
    updated_at: str                  # ISO 格式最后更新时间
    
    # 关键方法
    def to_dict(self) -> dict        # 序列化为字典
    def from_dict(cls, data) -> Task # 从字典反序列化
    def update_status(self, status, error=None)  # 更新状态
    def can_retry(self) -> bool      # 是否可以重试
    def increment_retry(self)        # 增加重试计数
```

**使用示例：**

```python
from src.core.task_model import Task, TaskStatus

# 创建任务
task = Task(
    id="A1B2C3D4E5F6",
    video_path="D:/videos/test.mp4",
    status=TaskStatus.NEW
)

# 更新状态
task.update_status(TaskStatus.TORRENT_CREATING)

# 检查是否可重试
if task.can_retry():
    task.increment_retry()

# 序列化保存
data = task.to_dict()
# {'id': 'A1B2C3D4E5F6', 'status': 'torrent_creating', ...}
```

---

### 2️⃣ Task Persistence（持久化存储）

**文件：** [src/core/task_persistence.py](src/core/task_persistence.py)

**特性：**
- JSON 格式存储（人类可读）
- 线程安全（`threading.Lock`）
- 实时写入（每次 `save_task()` 都立即持久化）

**API：**

```python
persistence = TaskPersistence("data/tasks.json")

# 保存任务
persistence.save_task(task)

# 查询任务
task = persistence.get_task("A1B2C3D4E5F6")
all_tasks = persistence.get_all_tasks()
pending = persistence.get_pending_tasks()  # 未完成任务
stats = persistence.get_task_count_by_status()  # 统计

# 删除任务
persistence.delete_task("A1B2C3D4E5F6")
```

**存储位置：** 默认 `{log_dir}/tasks.json`（即 `data/tasks.json`）

---

### 3️⃣ Task Queue（队列管理器）

**文件：** [src/core/task_queue.py](src/core/task_queue.py)

**核心功能：**

```python
queue = TaskQueue(persistence)

# 入队（带去重检查）
success = queue.enqueue(task)  # 返回 True/False

# 出队（阻塞等待）
task = queue.dequeue(block=True, timeout=1.0)

# 标记完成
queue.task_done()

# 延迟重试入队
queue.requeue_for_retry(task, delay_seconds=20)

# 查询
size = queue.queue_size()
stats = queue.get_statistics()
```

**特殊方法：**

- `_recover_pending_tasks()` - 启动时自动恢复未完成任务
- `requeue_for_retry()` - 在独立线程中延迟后重新入队（不阻塞主线程）

---

### 4️⃣ Task Worker（执行引擎）⭐ 核心

**文件：** [src/core/task_worker.py](src/core/task_worker.py)

**状态机驱动的任务执行器：**

```python
worker = TaskWorker(task_queue)

# 启动（后台线程）
worker_thread = worker.start()

# 停止
worker.stop()

# 打印统计
worker.print_statistics()
```

**内部流程：**

```
_run_loop()          # 主循环
  └─ _process_task()  # 处理单个任务
       ├─ _handle_new_task()   # 阶段1: 提取信息 + 生成 Torrent
       └─ _handle_upload()     # 阶段2: 调用 OKP 发布
```

**复用的现有模块：**

| 模块 | 用途 | 调用方式 |
|------|------|---------|
| Scanner | MD5 去重 | `self.scanner.is_processed()` |
| Probe | 视频信息提取 | `self.probe.get_video_info()` |
| Normalizer | 任务标准化 | `self.normalizer.normalize()` |
| TorrentBuilder | Torrent 生成 | `TorrentBuilder.create_torrent()` |
| OKPExecutor | OKP 调用 | `OKPExecutor.run_okp_upload()` |

---

### 5️⃣ Watcher（文件监控）

**文件：** [src/core/watcher.py](src/core/watcher.py)（v2.0 改造）

**改造前（v1.x）：**
```python
# 直接调用 Planner.process_task()（同步阻塞）
def on_created(self, event):
    task = self.normalizer.normalize(...)
    self.planner.process_task(task)  # 阻塞！
```

**改造后（v2.0）：**
```python
# 只创建 Task 并放入队列（异步非阻塞）
def on_created(self, event):
    task = Task(id=..., video_path=...)
    self.task_queue.enqueue(task)  # 立即返回！
```

**优势：**
- 不阻塞文件监控
- 多文件快速连续入队
- Worker 按序处理，不会漏任务

---

### 6️⃣ Torrent Builder（Torrent 生成器）

**文件：** [src/core/torrent_builder.py](src/core/torrent_builder.py)

**特性：**
- 使用 `torf` 库（非 qbittorrent-api）
- 支持多 Tracker（列表形式）
- 显示 Tracker 数量而非完整 URL

**调用：**

```python
from src.core.torrent_builder import TorrentBuilder

torrent_path = TorrentBuilder.create_torrent(
    file_path="D:/videos/test.mp4",
    tracker_urls=["http://tracker1/announce", "http://tracker2/announce"],
    output_dir="./data/torrents"
)
# 返回: "D:/data/torrents/test.torrent"
```

---

### 7️⃣ OKP Executor（OKP 执行器）

**文件：** [src/core/executor_okp.py](src/core/executor_okp.py)

**三大核心功能：**

#### ✅ 编码问题修复

```python
@staticmethod
def _decode_output(raw_bytes):
    encodings_to_try = ['utf-8', 'gbk', 'gb2312', 'gb18030', 'latin-1']
    
    for encoding in encodings_to_try:
        try:
            decoded = raw_bytes.decode(encoding)
            if not decoded.startswith('\ufffd'):
                return decoded, encoding
        except UnicodeDecodeError:
            continue
    
    return raw_bytes.decode('utf-8', errors='replace'), 'utf-8-replace'
```

#### ✅ 预览模式（使用 torf 解析）

```python
@staticmethod
def _parse_torrent_info(torrent_path):
    import torf
    from pathlib import Path
    
    # 类型检查 + 安全访问
    if isinstance(torrent_path, Path):
        torrent_path_str = str(torrent_path)
    
    torrent = torf.Torrent.read(torrent_path_str)
    
    info = {
        'name': getattr(torrent, 'name', 'Unknown'),
        'size': getattr(torrent, 'size', 0),
        'files': [...],
        'trackers': [...]
    }
    
    return info
```

#### ✅ 三种运行模式

```python
def run_okp_upload(
    torrent_path,
    auto_confirm=True,      # 控制 -y 参数
    preview_only=False      # 是否仅预览
):
    if preview_only:
        # 解析 torrent 信息并返回
        return {"mode": "preview", ...}
    
    cmd = [okp_executable, torrent_path]
    
    if auto_confirm:
        cmd.append("-y")  # 自动确认
    
    result = subprocess.run(cmd, ...)
    return {"mode": "publish", "success": ..., ...}
```

**其他特性：**
- 智能 OKP 路径查找（6 个候选位置）
- 结构化日志输出（边框 + Emoji）
- 关键信息提取（标题/站点/登录状态）
- 分层异常捕获（清晰的错误信息）

---

## 📝 日志示例

### 场景 1：正常发布流程

```
╔════════════════════════════════════════════════════════════╗
║     🎬 BT 自动发布系统 v2.0 - 队列架构版                  ║
╚════════════════════════════════════════════════════════════╝

功能特性:
  ✅ 任务队列管理
  ✅ 状态机驱动流程
  ✅ 自动重试机制
  ✅ 断点恢复支持
  ✅ 持久化存储

============================================================
👁️  文件监控启动
   监控目录: ./data/watch
   支持格式: .mkv, .mp4, .avi
============================================================

============================================================
🚀 Worker 启动 - 开始处理任务队列
============================================================

从持久化存储加载 0 个任务

🔍 检测到新视频文件: D:\data\watch\新番第01集.mp4
📋 创建任务 [A1B2C3D4E5F6] - 文件: 新番第01集.mp4
✅ 任务 [A1B2C3D4E5F6] 已加入队列，等待 Worker 处理

╔════════════════════════════════════════════════╗
║  [A1B2C3D4E5F6] 🎬 开始处理任务                ║
╚════════════════════════════════════════════════╝
  文件: D:\data\watch\新番第01集.mp4
  初始状态: new

[A1B2C3D4E5F6] 状态转换: NEW → TORRENT_CREATING
[A1B2C3D4E5F6] 🔍 提取视频信息...
[A1B2C3D4E5F6] 📦 生成 Torrent...
[A1B2C3D4E5F6] ✅ Torrent 已生成: D:\data\torrents\新番第01集.torrent

[A1B2C3D4E5F6] 状态转换: TORRENT_CREATED → UPLOADING
[A1B2C3D4E5F6] 🚀 调用 OKP 发布...
[A1B2C3D4E5F6]    重试次数: 0/3

╔════════════════════════════════════════════════════════════╗
║              🔶 BT 发布任务 - 开始处理                    ║
╚════════════════════════════════════════════════════════════╝

📦 Torrent 文件信息:
  路径: D:\data\torrents\新番第01集.torrent
  大小: 15.23 KB

📋 内容详情:
  标题: 新番第01集.mp4
  总大小: 1.25 GB
  文件列表 (1 个文件):
    📄 新番第01集.mp4 (1.25 GB)
  Tracker (前3个):
    • http://open.acgtracker.com:1096/announce
    • http://nyaa.tracker.wf:7777/announce
    • http://opentracker.acgnx.se/announce

⚙️  执行配置:
  模式: 自动发布模式 (auto_confirm=True)
  OKP 路径: D:\BT_Automatic_Publishing\tools\OKP.Core.exe
  工作目录: D:\data\torrents

💻 执行命令:
  OKP.Core.exe 新番第01集.torrent -y

------------------------------------------------------------
📊 执行结果:
  返回码: 0
  输出编码: STDOUT=gbk, STDERR=utf-8

  ✅ 状态: 发布成功
  📝 OKP 输出摘要:
     ✓ 登录成功 - NyaaSi
     ✓ 发布标题: [动漫组] 新番第01集 [1080p]
     ✓ 所有站点发布完成

╔════════════════════════════════════════════════════════════╗
║              ✅ BT 发布任务 - 完成                         ║
╚════════════════════════════════════════════════════════════╝

[A1B2C3D4E5F6] ✅ 任务完成 - 模式: publish

╔════════════════════════════════════════════════╗
║  [A1B2C3D4E5F6] ✅ 任务成功完成                 ║
╚════════════════════════════════════════════════╝
```

---

### 场景 2：失败自动重试

```
╔════════════════════════════════════════════════╗
║  [B2C3D4E5F6A7] 🎬 开始处理任务               ║
╚════════════════════════════════════════════════╝
  文件: D:\data\watch\动漫合集.mkv
  初始状态: new

[B2C3D4E5F6A7] ✅ Torrent 已生成: data/torrents/动漫合集.torrent

[B2C3D4E5F6A7] 状态转换: TORRENT_CREATED → UPLOADING
[B2C3D4E5F6A7] 🚀 调用 OKP 发布...
[B2C3D4E5F6A7]    重试次数: 0/3

📊 执行结果:
  返回码: 1
  ❌ 状态: 发布失败
  
  ⚠️  错误摘要:
     ✗ 登录失败 - NyaaSi: Cookie 过期

[B2C3D4E5F6A7] ⚠️  任务失败
[B2C3D4E5F6A7]    错误: 返回码 1
[B2C3D4E5F6A7]    重试: 1/3
[B2C3D4E5F6A7] 🔄 将在 20秒 后重试...

... (20秒后自动重试) ...

[B2C3D4E5F6A7] 任务已重新入队
[B2C3D4E5F6A7] 状态转换: TORRENT_CREATED → UPLOADING
[B2C3D4E5F6A7] 🚀 调用 OKP 发布...
[B2C3D4E5F6A7]    重试次数: 1/3

... (这次成功了) ...

[B2C3D4E5F6A7] ✅ 任务完成 - 模式: publish
```

---

### 场景 3：多任务并行入队

```
🔍 检测到新视频文件: D:\data\watch\第01集.mp4
📋 创建任务 [AAA111222333] - 文件: 第01集.mp4
✅ 任务 [AAA111222333] 已加入队列，等待 Worker 处理

🔍 检测到新视频文件: D:\data\watch\第02集.mp4
📋 创建任务 [BBB222333444] - 文件: 第02集.mp4
✅ 任务 [BBB222333444] 已加入队列，等待 Worker 处理

🔍 检测到新视频文件: D:\data\watch\第03集.mp4
📋 创建任务 [CCC333444555] - 文件: 第03集.mp4
✅ 任务 [CCC333444555] 已加入队列，等待 Worker 处理

... Worker 按顺序处理 ...

[AAA111222333] 🎬 开始处理任务
[AAA111222333] ✅ 任务成功完成

[BBB222333444] 🎬 开始处理任务
[BBB222333444] ✅ 任务成功完成

[CCC333444555] 🎬 开始处理任务
[CCC333444555] ✅ 任务成功完成
```

---

### 场景 4：断点恢复

```bash
# 第一次运行
$ python main.py
... 处理了 5 个任务，第 6 个失败 ...
^C
⏹️  收到停止信号，正在优雅关闭...

📊 任务统计:
  ----------------------------------------
  ✅ 成功: 5
  ⚠️  失败（可重试）: 1
  ----------------------------------------
  📋 总计: 6 个任务

👋 系统已停止


# 第二次启动
$ python main.py

从持久化存储加载 6 个任务
恢复 1 个未完成任务到队列
[DDD444555666] 恢复失败任务 - 重试 1/3
[DDD444555666] 任务已重新入队

... 继续处理 ...
[DDD444555666] ✅ 任务成功完成  ← 自动恢复！
```

---

### 场景 5：优雅关闭统计

```
⏹️  收到停止信号，正在优雅关闭...
⏹️  正在停止 Worker...
🛑 Worker 已停止
停止文件监控...
文件监控已停止

📊 任务统计:
  ----------------------------------------
  🆕 新任务: 0
  📦 生成Torrent中: 0
  ✓ Torrent已生成: 0
  🚀 上传中: 0
  ✅ 成功: 12
  ⚠️  失败（可重试）: 1
  ❌ 永久失败: 0
  ----------------------------------------
  📋 总计: 13 个任务

👋 系统已停止
```

---

## ❓ 常见问题

### Q1: Windows 控制台出现乱码？

**原因：** OKP 输出编码与终端不一致

**解决方案：** 已在 v1.2 修复，使用多编码自动检测链：

```python
encodings_to_try = ['utf-8', 'gbk', 'gb2312', 'gb18030', 'latin-1']
```

如果仍有问题，请检查：
1. 确保 Windows 终端编码为 UTF-8 或 GBK
2. 查看 `logs/video_scanner.log`（文件日志通常无乱码）

---

### Q2: `'WindowsPath' object has no attribute 'path'` 错误？

**原因：** torf 的 TorrentFile 对象是 `pathlib.Path` 类型，没有 `.path` 属性

**解决方案：** 已在 v1.2 修复，改用：

```python
# 错误写法
info['files'].append(f.path)  # ❌ AttributeError

# 正确写法
if hasattr(f, 'name'):
    file_display = f.name      # ✅ 文件名
else:
    file_display = str(f)      # ✅ 完整路径
```

---

### Q3: OKP 找不到可执行文件？

**错误：** `[WinError 2] 系统找不到指定的文件`

**解决方案：** OKP 会自动搜索以下位置：

1. `config.yaml` 中的 `okp_path`
2. 项目根目录 (`OKP.Core.exe`, `OKP.exe`)
3. `tools/` 子目录
4. 系统 PATH 环境变量

**建议：** 设置 `okp_path: null`（让系统自动查找），或将 OKP 放入项目根目录。

---

### Q4: 如何只预览不发布？

**配置：**

```yaml
okp_preview_only: true
okp_auto_confirm: true
```

**效果：** 显示 Torrent 信息后立即返回，不调用 OKP。

---

### Q5: 如何手动重试失败的任务？

**方法：**

1. 编辑 `data/tasks.json`
2. 找到目标任务
3. 修改以下字段：
   ```json
   {
     "status": "failed",
     "retry_count": 0,
     "error_message": null,
     "updated_at": "2026-01-15T12:00:00"
   }
   ```
4. 保存文件
5. 重启程序（或等待下次自动恢复周期）

---

### Q6: 如何清空所有任务历史？

删除 `data/tasks.json` 文件，下次启动时会创建新的空数据库。

```bash
del data\tasks.json
```

**注意：** 这不会影响 `processed_files.json`（MD5 去重库）。如果也想重新处理已处理的文件，需同时删除它。

---

### Q7: 程序崩溃后如何恢复？

**自动恢复机制：**

1. 每次状态变化都立即写入 `tasks.json`
2. 程序启动时自动加载未完成任务
3. 根据状态决定恢复策略：
   - `NEW/TORRENT_CREATING/TORRENT_CREATED/UPLOADING` → 标记为 FAILED 后重试
   - `FAILED` 且 `retry_count < max_retries` → 直接重试
   - `SUCCESS/PERMANENT_FAILED` → 跳过

**无需手动干预！** 直接重启即可。

---

### Q8: 如何调整重试次数和延迟？

**修改位置：** [src/core/task_model.py:16](src/core/task_model.py#L16)

```python
@dataclass
class Task:
    max_retries: int = 3  # ← 修改此值
```

**延迟算法：** [src/core/task_worker.py:200](src/core/task_worker.py#L200)

```python
delay = min(10 * (task.retry_count + 1), 30)
# 当前: 10s, 20s, 30s
# 可改为: 5 * (retry + 1), 60 等
```

---

### Q9: 支持哪些视频格式？

当前支持：`.mkv`, `.mp4`, `.avi`

**添加新格式：** 编辑 `config.yaml`：

```yaml
video_extensions:
  - .mkv
  - .mp4
  - .avi
  - .wmv    # 新增
  - .flv    # 新增
  - .mov    # 新增
```

---

### Q10: Tracker 列表在哪里配置？

**两种方式：**

1. **编辑 `config.yaml`**（推荐）：
   ```yaml
   tracker_urls:
     - http://your-tracker/announce
   ```

2. **修改默认值：** [src/config.py](src/config.py) 中的 `DEFAULT_CONFIG`

当前已内置 **42 个常用 Tracker**。

---

## 🛠️ 技术栈

### 核心依赖

| 库名 | 版本 | 用途 |
|------|------|------|
| `watchdog` | ≥4.0.0 | 文件系统事件监控 |
| `pymediainfo` | ≥6.1.0 | 视频元数据提取 |
| `torf` | ≥4.2.0 | Torrent 文件生成 |
| `PyYAML` | ≥6.0 | YAML 配置解析 |
| `fastapi` | ≥0.110.0 | Web 面板后端（v2.1） |
| `uvicorn` | ≥0.29.0 | ASGI 服务器（v2.1） |

### 设计模式

| 模式 | 应用场景 |
|------|---------|
| **观察者模式** | Watchdog 文件监控 |
| **生产者-消费者** | Watcher（生产）→ Queue → Worker（消费）|
| **状态机** | Task 生命周期管理 |
| **单例模式** | Logger、Config 全局实例 |
| **策略模式** | 多编码解码尝试 |

### 并发模型

- **Watcher:** 主线程（Watchdog Observer）
- **Worker:** 独立后台线程（daemon=True）
- **重试延迟:** 独立临时线程（不阻塞主队列）
- **持久化:** 线程安全（Lock 保护）

---

## 📈 性能指标

| 指标 | 典型值 |
|------|--------|
| 文件检测延迟 | <1 秒 |
| 视频信息提取 | 1-3 秒（取决于文件大小）|
| Torrent 生成 | 5-30 秒（取决于文件大小）|
| OKP 发布 | 30-120 秒（取决于网络）|
| 内存占用 | ~50 MB（空闲）|
| CPU 占用 | <1%（空闲）|

**建议硬件：**
- 最低配置：2核 CPU + 4GB RAM
- 推荐配置：4核 CPU + 8GB RAM
- 存储：SSD 推荐（提升 Torrent 生成速度）

---

## 🎯 路线图

### v2.1 ✅ 已完成

- [x] Web 管理界面（FastAPI + 单文件前端）
- [x] REST API（任务 CRUD、日志流、手动操作）
- [ ] 多 Worker 并发处理
- [ ] 定时任务调度（cron）
- [ ] 邮件/Telegram 通知

### v2.2（远期）

- [ ] Docker 容器化部署
- [ ] 分布式任务队列（Redis + Celery）
- [ ] 数据库升级（SQLite → PostgreSQL）
- [ ] Webhook 集成
- [ ] 插件系统

---

## 📄 许可证

MIT License

Copyright (c) 2026 BT Auto Publishing System

---

## 🤝 贡献

欢迎提交 Issue 和 Pull Request！

### 开发规范

1. 遵循现有代码风格
2. 不添加类型注解（basedpyright 兼容性）
3. 所有异常必须捕获并提供清晰日志
4. 新功能需更新本文档

---

## 📞 支持

- **Issue:** [GitHub Issues](链接)
- **文档:** 本 README
- **OKP 文档:** https://github.com/AmusementClub/OKP

---

**最后更新：** 2026-04-03
**当前版本：** v2.1.0
**作者：** BT Auto Publishing Team