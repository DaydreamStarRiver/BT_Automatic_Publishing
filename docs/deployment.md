# 🚀 部署说明文档

> BT 自动发布系统 v2.1 - 安装、配置、运行完整指南

---

## 目录

- [环境要求](#环境要求)
- [快速安装](#快速安装)
- [详细配置](#详细配置)
- [OKP 配置指南](#okp-配置指南)
- [运行模式](#运行模式)
- [日常操作](#日常操作)
- [常见问题](#常见问题)
- [生产环境建议](#生产环境建议)

---

## 环境要求

### 系统要求

| 项目 | 最低要求 | 推荐配置 |
|------|---------|---------|
| **操作系统** | Windows 10 / Ubuntu 20.04 / macOS 12 | Windows 11 / Ubuntu 22.04 / macOS 13 |
| **Python** | 3.10+ | 3.11+ 或 3.12+ |
| **CPU** | 2 核 | 4 核+ |
| **内存** | 4 GB RAM | 8 GB RAM+ |
| **硬盘** | 10 GB 可用空间（SSD 推荐） | 50 GB+ SSD |
| **网络** | 稳定的互联网连接（用于 OKP 发布）| 宽带连接 |

### Python 版本检查

```bash
python --version
# 应输出: Python 3.10.x 或更高版本
```

> ⚠️ **重要：** 本系统不支持 Python 3.9 及以下版本！

---

## 快速安装

### 方法一：从源码安装（推荐）

```bash
# 1. 克隆项目
git clone <your-repo-url>
cd BT_Automatic_Publishing_copy

# 2. 创建虚拟环境（推荐）
python -m venv venv

# Windows
venv\Scripts\activate

# Linux / macOS
source venv/bin/activate

# 3. 安装依赖
pip install -r requirements.txt

# 4. 启动系统
python main.py
```

### 方法二：直接安装依赖

```bash
# 安装核心依赖
pip install watchdog>=4.0.0
pip install pymediainfo>=6.1.0
pip install torf>=4.2.0
pip install PyYAML>=6.0

# 安装 Web 面板依赖（可选，v2.1 新增）
pip install fastapi>=0.110.0
pip install uvicorn>=0.29.0
```

### 验证安装

```bash
# 检查所有依赖是否正确安装
pip list | grep -E "watchdog|pymediainfo|torf|PyYAML|fastapi|uvicorn"
```

预期输出：

```
fastapi          0.110.0
pymediainfo      6.1.0
PyYAML           6.0
torf             4.2.0
uvicorn          0.29.0
watchdog         4.0.0
```

---

## 详细配置

### 配置文件位置

主配置文件：`config.yaml`（位于项目根目录）

### 完整配置项说明

```yaml
# ═══════════════════════════════════════════════════════════════
# BT 自动发布系统 - 完整配置文件
# ═══════════════════════════════════════════════════════════════

# ========== 基础路径配置 ==========
watch_dir: ./data/watch                    # 监控目录（放视频文件的文件夹）
output_torrent_dir: ./data/torrents        # Torrent 输出目录
processed_dir: ./data/processed            # 已处理文件目录（可选）
log_dir: ./logs                             # 日志存储目录
db_path: ./data/processed_files.json       # MD5 去重数据库路径

# ========== 视频格式支持 ==========
video_extensions:
  - .mkv      # Matroska Video (推荐)
  - .mp4      # MPEG-4 Part 14
  - .avi      # Audio Video Interleave
  # 可添加更多格式:
  # - .wmv     # Windows Media Video
  # - .flv     # Flash Video
  # - .mov     # QuickTime File Format

# ========== Tracker 配置 ==========
tracker_urls:
  # 公共 Tracker（已内置 42 个，以下仅展示部分示例）
  - http://open.acgtracker.com:1096/announce
  - http://nyaa.tracker.wf:7777/announce
  - udp://tracker.opentrackr.org:1337/announce
  - http://opentracker.acgnx.se/announce
  
  # 添加自定义 Tracker:
  # - http://your-tracker.example.com/announce

# ========== OKP 发布配置 ==========
okp_path: null                              # OKP 可执行文件路径（null=自动查找）
okp_setting_path: null                      # OKP setting.toml 路径
okp_cookies_path: null                      # cookies.txt 文件路径
okp_timeout: 300                            # OKP 执行超时时间（秒）
okp_auto_confirm: true                      # 是否自动确认（-y 参数）
okp_preview_only: false                     # 是否仅预览不发布

# ========== Web 面板配置（v2.1 新增）==========
web_enabled: true                           # 是否启用 Web 面板
web_host: "0.0.0.0"                         # 监听地址（0.0.0.0=所有网卡）
web_port: 8080                              # 监听端口号

# ========== 日志配置 ==========
log_level: INFO                             # 日志级别：DEBUG/INFO/WARNING/ERROR
log_max_size_mb: 100                        # 单个日志文件最大大小（MB）
log_backup_count: 5                         # 保留的日志文件数量
```

### 配置项详解

#### 路径配置

| 配置项 | 类型 | 默认值 | 说明 |
|--------|------|--------|------|
| `watch_dir` | string | `./data/watch` | **必填** - 放置待处理视频文件的目录 |
| `output_torrent_dir` | string | `./data/torrents` | 生成的 Torrent 文件保存位置 |
| `processed_dir` | string | `./data/processed` | 已处理文件的备份位置（可选）|
| `log_dir` | string | `./logs` | 日志文件存储目录 |
| `db_path` | string | `./data/processed_files.json` | MD5 去重数据库 |

**路径注意事项：**
- ✅ 支持相对路径和绝对路径
- ✅ Windows 路径使用正斜杠 `/` 或反斜杠 `\\`
- ✅ 确保目录存在且有写入权限
- ❌ 不要使用中文路径（可能导致编码问题）

---

#### OKP 配置

| 配置项 | 类型 | 默认值 | 说明 |
|--------|------|--------|------|
| `okp_path` | string/null | `null` | OKP 可执行文件完整路径 |
| `okp_setting_path` | string/null | `null` | OKP 配置文件 (setting.toml) 路径 |
| `okp_cookies_path` | string/null | `null` | Cookie 文件 (cookies.txt) 路径 |
| `okp_timeout` | int | `300` | 单次 OKP 执行的最大等待时间（秒）|
| `okp_auto_confirm` | bool | `true` | 自动确认模式（跳过交互提示）|
| `okp_preview_only` | bool | `false` | 仅预览模式（不实际发布）|

---

#### Web 面板配置

| 配置项 | 类型 | 默认值 | 说明 |
|--------|------|--------|------|
| `web_enabled` | bool | `true` | 是否启用 Web 管理面板 |
| `web_host` | string | `"0.0.0.0"` | HTTP 服务监听地址 |
| `web_port` | int | `8080` | HTTP 服务监听端口 |

**安全提示：**
- 如果只在本地使用，保持默认即可
- 如果暴露到公网，请添加认证机制或防火墙规则

---

#### 日志配置

| 配置项 | 类型 | 默认值 | 说明 |
|--------|------|--------|------|
| `log_level` | string | `INFO` | 日志输出级别 |
| `log_max_size_mb` | int | `100` | 单个日志文件最大大小（MB）|
| `log_backup_count` | int | `5` | 保留的历史日志文件数量 |

**日志级别说明：**

| 级别 | 输出内容 | 适用场景 |
|------|---------|---------|
| `DEBUG` | 所有调试信息 | 开发调试 |
| `INFO` | 一般信息（推荐） | 日常运行 |
| `WARNING` | 警告信息 | 关注潜在问题 |
| `ERROR` | 错误信息 | 排查故障 |

---

## OKP 配置指南

### 什么是 OKP？

OKP (One Key Publish) 是一个命令行工具，用于自动发布 Torrent 到多个 BT 站点。

**官方仓库：** https://github.com/AmusementClub/OKP

### 下载与安装

#### 1. 下载 OKP

从 GitHub Releases 页面下载最新版本：

```bash
# 访问 https://github.com/AmusementClub/OKP/releases
# 下载适合你系统的版本：
#   - Windows: OKP.Core.exe
#   - Linux: okp-core
#   - macOS: okp-core-macos
```

#### 2. 放置 OKP 文件

将可执行文件放入以下任一位置（按优先级排序）：

1. **`config.yaml` 中指定的路径**
   ```yaml
   okp_path: "D:/tools/OKP.Core.exe"
   ```

2. **项目根目录**
   ```
   BT_Automatic_Publishing/
   ├── main.py
   ├── config.yaml
   └── OKP.Core.exe    ← 放这里
   ```

3. **`tools/` 子目录**
   ```
   BT_Automatic_Publishing/
   └── tools/
       └── OKP.Core.exe  ← 放这里
   ```

4. **系统 PATH 环境变量中的任意目录**

> 💡 **推荐方式：** 设置 `okp_path: null`（让系统自动查找），并将 OKP 放入项目根目录。

---

### 导出 Cookie

BT 站点通常需要登录才能发布，需要导出浏览器的 Cookie。

#### 步骤 1：安装浏览器扩展

**Chrome / Edge：**
1. 访问 Chrome Web Store
2. 搜索 "**Get cookies.txt LOCALLY**" 
3. 点击「添加到Chrome」

**Firefox：**
1. 访问 Firefox Add-ons
2. 搜索 "**cookies.txt**"
3. 点击「添加到Firefox」

---

#### 步骤 2：导出 Cookie

1. 打开目标 BT 站点（如 Nyaa.si）
2. **确保已登录**
3. 点击浏览器工具栏中的 Cookie 扩展图标
4. 选择 **"Export"** 或 **"导出"**
5. 选择保存位置，文件名设为 `cookies.txt`
6. 将文件放入项目目录或指定路径：

```yaml
# config.yaml
okp_cookies_path: "./cookies.txt"
```

---

#### 步骤 3：验证 Cookie 格式

正确的 `cookies.txt` 格式：

```
# Netscape HTTP Cookie File
.nyaa.si	TRUE	/	FALSE	2147483647	session	abc123def456
.nyaa.si	TRUE	/	FALSE	2147483647	user_id	12345
```

**注意：**
- ✅ 使用 Netscape 格式
- ✅ 包含域名、路径、过期时间等字段
- ❌ 不是 JSON 格式

---

### OKP Setting.toml 配置

OKP 的站点配置文件 `setting.toml` 定义了要发布的站点及其参数。

#### 示例配置

```toml
# setting.toml 示例

[nyaa]
enabled = true
url = "https://nyaa.si"

[dmhy]
enabled = true
url = "https://share.dmhy.org"

[acgrip]
enabled = false  # 禁用此站点
url = "https://acg.rip"
```

**获取方法：**
1. 从 OKP 官方文档或社区获取模板
2. 根据实际需求修改
3. 在 `config.yaml` 中指定路径：

```yaml
okp_setting_path: "./setting.toml"
```

---

### 测试 OKP 配置

#### 手动测试 OKP

```bash
# 进入 OKP 所在目录
cd D:/BT_Automatic_Publishing

# 测试预览模式（不实际发布）
OKP.Core.exe your_torrent.torrent --preview

# 测试自动确认模式
OKP.Core.exe your_torrent.torrent -y
```

如果看到类似输出，说明配置成功：

```
✓ 登录成功 - NyaaSi
✓ 发布标题: [Group] Title [1080p]
✅ 所有站点发布完成
```

---

## 运行模式

### 三种运行模式对比

| 模式 | 配置 | 效果 | 适用场景 |
|------|------|------|---------|
| **预览模式** ⭐ | `preview_only: true` | 只显示信息，不发布 | 初次配置测试 |
| **交互模式** | `auto_confirm: false` | 手动确认每一步 | 调试问题 |
| **自动模式** | `auto_confirm: true` + `preview_only: false` | 全自动执行 | 生产环境 7×24 运行 |

---

### 模式 1：预览模式（测试用）

**配置：**

```yaml
okp_preview_only: true
okp_auto_confirm: true
```

**效果：**
- ✅ 提取视频信息
- ✅ 生成 Torrent 文件
- ✅ 解析并显示 Torrent 内容
- ❌ **不调用** OKP 发布
- ❌ 不需要登录 BT 站点

**适用场景：**
- 首次运行，验证流程是否正常
- 检查生成的 Torrent 信息是否正确
- 不想实际发布时测试

**日志示例：**

```
📦 Torrent 文件信息:
  路径: D:\data\torrents\test.torrent
  大小: 15.23 KB

📋 内容详情:
  标题: test.mp4
  总大小: 1.25 GB
  Tracker 数量: 42

✅ 预览模式 — 未执行实际发布
```

---

### 模式 2：交互模式（调试用）

**配置：**

```yaml
okp_preview_only: false
okp_auto_confirm: false
```

**效果：**
- 执行完整的发布流程
- OKP 会暂停并提示：
  ```
  是否继续？(y/n):
  ```
- 需要手动按 `Enter` 或输入 `y` 继续

**适用场景：**
- 排查发布失败原因
- 查看 OKP 详细输出
- 学习 OKP 工作流程

**注意：** 此模式下 Worker 会阻塞等待用户输入，不适合无人值守。

---

### 模式 3：自动模式（生产环境）⭐

**配置：**

```yaml
okp_preview_only: false
okp_auto_confirm: true
```

**效果：**
- 全自动执行，无需任何人工干预
- OKP 使用 `-y` 参数跳过所有确认提示
- 失败时自动重试（最多 3 次）
- 适合 7×24 小时长期运行

**适用场景：**
- 正式投入使用
- 批量处理大量视频
- NAS 或服务器后台运行

**启动后只需：**
1. 将视频文件放入 `data/watch/`
2. 等待自动完成
3. 通过 Web 面板查看结果

---

## 日常操作

### 启动系统

#### 前台运行（推荐开发时使用）

```bash
python main.py
```

**优点：** 可以实时查看日志输出  
**缺点：** 关闭终端会停止程序

---

#### 后台运行（Windows）

**CMD：**

```bash
start /b python main.py > log.txt 2>&1
```

**PowerShell：**

```powershell
Start-Process -FilePath "python" `
  -ArgumentList "main.py" `
  -WindowStyle Hidden `
  -RedirectStandardOutput "output.log" `
  -RedirectStandardError "error.log"
```

---

#### 后台运行（Linux/macOS）

```bash
# 使用 nohup
nohup python main.py > output.log 2>&1 &

# 使用 screen（推荐）
screen -S btpublisher
python main.py
# 按 Ctrl+A, D 分离会话

# 使用 tmux（更现代）
tmux new -s btpublisher
python mainCtrl+B, D 分离窗口
```

---

### 停止系统

#### 优雅关闭（推荐）

在运行终端中按：

```
Ctrl+C
```

**输出示例：**

```
⏹️  收到停止信号，正在优雅关闭...
⏹️  正在停止 Worker...
🛑 Worker 已停止
停止文件监控...
文件监控已停止

📊 任务统计:
  ----------------------------------------
  ✅ 成功: 12
  ⚠️ 失败（可重试）: 1
  ----------------------------------------
  📋 总计: 13 个任务

👋 系统已停止
```

**优雅关闭的好处：**
- ✅ 等待当前任务完成（或安全中断）
- ✅ 保存所有状态到磁盘
- ✅ 输出最终统计信息
- ✅ 不会丢失数据

---

#### 强制终止（不推荐）

```bash
# Windows
taskkill /F /IM python.exe

# Linux/macOS
kill -9 $(pgrep -f "main.py")
```

⚠️ **风险：** 可能导致：
- 当前正在处理的任务丢失
- 数据未保存
- 下次启动需要恢复

---

### 查看任务状态

#### 方法 1：Web 面板（推荐）

打开浏览器访问：`http://localhost:8080`

功能：
- 📊 任务统计仪表盘
- 📋 任务列表（支持搜索、过滤）
- 📝 实时日志流
- ✏️ 编辑发布信息
- 🔄 重试/删除操作

---

#### 方法 2：REST API

```bash
# 获取所有任务
curl http://localhost:8080/api/tasks

# 获取失败的任务
curl "http://localhost:8080/api/tasks?status=failed"

# 获取单个任务详情
curl http://localhost:8080/api/tasks/A1B2C3D4E5F6?full=true
```

---

#### 方法 3：直接查看 JSON

```bash
# Windows PowerShell
Get-Content data\tasks.json | ConvertFrom-Json

# Linux/macOS
cat data/tasks.json | python -m json.tool
```

---

#### 方法 4：查看日志文件

```bash
# 查看最新日志
type logs\video_scanner.log              # Windows
tail -f logs/video_scanner.log            # Linux/macOS (实时)

# 查看特定日期的日志
type logs\video_scanner_20260115.log
```

---

### 手动干预任务

#### 重试失败任务

**方法 A：Web 面板**
1. 打开 `http://localhost:8080`
2. 找到失败的任务
3. 点击「重试」按钮

**方法 B：API**

```bash
curl -X POST http://localhost:8080/api/tasks/A1B2C3D4E5F6/retry
```

**方法 C：编辑 JSON**

1. 打开 `data/tasks.json`
2. 找到目标任务
3. 修改字段：

```json
{
  "status": "failed",
  "retry_count": 0,
  "error_message": null,
  "updated_at": "2026-01-15T12:00:00"
}
```

4. 保存并重启程序

---

#### 删除任务记录

```bash
# API 方式
curl -X DELETE http://localhost:8080/api/tasks/A1B2C3D4E5F6

# 清除所有永久失败的任务
curl -X POST http://localhost:8080/api/tasks/clear_failed
```

---

#### 手动触发处理

对于不在监控目录的视频文件：

```bash
curl -X POST http://localhost:8080/api/tasks/trigger \
  -H "Content-Type: application/json" \
  -d '{"video_path": "D:/videos/my_video.mp4"}'
```

---

## 常见问题

### Q1: Windows 控制台出现乱码？

**症状：** OKP 输出的中文显示为乱码（□□□ 或 ???）

**原因：** OKP 输出编码与终端编码不一致

**解决方案：**

本系统已在 v1.2 修复此问题，使用多编码自动检测链：

```python
encodings_to_try = ['utf-8', 'gbk', 'gb2312', 'gb18030', 'latin-1']
```

如果仍有问题：

1. **确保终端编码为 UTF-8：**
   ```bash
   # CMD
   chcp 65001
   
   # PowerShell
   [Console]::OutputEncoding = [System.Text.Encoding]::UTF8
   ```

2. **查看日志文件（通常无乱码）：**
   ```bash
   type logs\video_scanner.log
   ```

---

### Q2: `'WindowsPath' object has no attribute 'path'` 错误？

**症状：** Torrent 生成时报错

**原因：** `torf` 库的 `TorrentFile` 对象是 `pathlib.Path` 类型

**解决方案：** 已在 v1.2 修复，改用安全的属性访问：

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

**错误信息：** `[WinError 2] 系统找不到指定的文件`

**解决方案：** OKP 会按优先级自动搜索以下位置：

1. `config.yaml` 中 `okp_path` 指定的路径
2. 项目根目录 (`OKP.Core.exe`, `OKP.exe`)
3. `tools/` 子目录
4. 系统 PATH 环境变量

**建议：**
- 设置 `okp_path: null`（让系统自动查找）
- 将 OKP 放入项目根目录
- 或将 OKP 目录加入系统 PATH

---

### Q4: 如何只预览不发布？

**配置修改：**

```yaml
okp_preview_only: true
okp_auto_confirm: true
```

**效果：** 只生成 Torrent 并显示信息，不调用 OKP 发布

---

### Q5: 如何调整重试次数和延迟？

**修改位置：** `src/core/task_model.py`

```python
@dataclass
class Task:
    max_retries: int = 3  # ← 修改最大重试次数（默认 3 次）
```

**延迟算法：** `src/core/task_worker.py`

```python
delay = min(10 * (retry_count + 1), 30)
# 当前: 10秒 → 20秒 → 30秒
# 可改为: 5 * (retry + 1), 60 等
```

**注意：** 修改后需重启程序生效

---

### Q6: 支持哪些视频格式？

**默认支持：** `.mkv`, `.mp4`, `.avi`

**添加新格式：** 编辑 `config.yaml`：

```yaml
video_extensions:
  - .mkv
  - .mp4
  - .avi
  - .wmv    # 新增
  - .flv    # 新增
  - .mov    # 新增
  - .ts     # 新增 (MPEG-TS)
  - .mkv    # 已有
```

---

### Q7: Tracker 列表在哪里配置？

**两种方式：**

1. **编辑 `config.yaml`（推荐）：**
   ```yaml
   tracker_urls:
     - http://your-tracker/announce
   ```

2. **修改默认值：** `src/config.py` 中的 `DEFAULT_CONFIG`

**当前已内置 42 个常用 Tracker。**

---

### Q8: 如何清空所有任务历史？

**删除任务数据库：**

```bash
# Windows
del data\tasks.json

# Linux/macOS
rm data/tasks.json
```

**下次启动时会创建新的空数据库。**

> ⚠️ **注意：** 这不会影响 `processed_files.json`（MD5 去重库）。如果想重新处理已处理的文件，需同时删除它。

---

### Q9: 程序崩溃后如何恢复？

**好消息：无需手动干预！**

系统具备自动恢复能力：

1. **每次状态变化都立即写入** `tasks.json`
2. **程序启动时自动加载** 未完成任务
3. **根据状态决定恢复策略：**
   - `NEW/TORRENT_CREATING/TORRENT_CREATED/UPLOADING` → 标记为 FAILED 后重试
   - `FAILED` 且 `retry_count < max_retries` → 直接重试
   - `SUCCESS/PERMANENT_FAILED` → 跳过

**直接重启即可！**

---

### Q10: Web 面板无法访问？

**检查清单：**

1. **确认 Web 面板已启用：**
   ```yaml
   web_enabled: true
   ```

2. **检查端口是否被占用：**
   ```bash
   netstat -ano | findstr :8080    # Windows
   lsof -i :8080                   # Linux/macOS
   ```

3. **尝试其他端口：**
   ```yaml
   web_port: 9090
   ```

4. **检查防火墙设置：**
   - Windows Defender 防火墙
   - 第三方杀毒软件
   - 云服务器安全组

5. **确认服务已启动：**
   启动后控制台应显示：
   ```
   🌐  Web 面板地址: http://localhost:8080
   ```

---

### Q11: 内存/CPU 占用过高？

**正常范围：**

| 指标 | 空闲时 | 处理任务时 |
|------|--------|----------|
| CPU | <1% | 5-20% |
| 内存 | ~50 MB | ~100 MB |

**如果超出范围：**

1. **检查是否有大量任务积压：**
   ```bash
   curl http://localhost:8080/api/status
   # 查看 queue_size
   ```

2. **清理已完成的历史任务：**
   ```bash
   curl -X POST http://localhost:8080/api/tasks/clear_failed
   ```

3. **检查日志文件大小：**
   ```bash
   dir logs\*.log               # Windows
   du -sh logs/*.log            # Linux
   ```
   
   如果过大，可以删除旧日志或调整日志轮转配置。

---

### Q12: 如何更新到最新版本？

```bash
# 1. 停止当前运行的程序
Ctrl+C

# 2. 备份配置和数据
copy config.yaml config.yaml.bak
copy data\tasks.json data\tasks.json.bak

# 3. 拉取最新代码
git pull origin main

# 4. 更新依赖（如果有变化）
pip install -r requirements.txt

# 5. 启动新版本
python main.py
```

---

## 生产环境建议

### 1. 使用虚拟环境

```bash
python -m venv venv
venv\Scripts\activate   # Windows
source venv/bin/activate  # Linux/macOS
```

**优势：**
- 避免包冲突
- 易于迁移
- 版本隔离

---

### 2. 配置 systemd 服务（Linux）

创建 `/etc/systemd/system/bt-publisher.service`：

```ini
[Unit]
Description=BT Auto Publishing System
After=network.target

[Service]
Type=simple
User=your_username
WorkingDirectory=/path/to/BT_Automatic_Publishing
ExecStart=/path/to/venv/bin/python main.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

**启用服务：**

```bash
sudo systemctl daemon-reload
sudo systemctl enable bt-publisher
sudo systemctl start bt-publisher

# 查看状态
sudo systemctl status bt-publisher

# 查看日志
journalctl -u bt-publisher -f
```

---

### 3. 定期备份数据

**重要文件：**
- `config.yaml` - 配置文件
- `data/tasks.json` - 任务数据库
- `data/processed_files.json` - MD5 去重库
- `cookies.txt` - Cookie 文件（如使用）

**备份脚本示例：**

```bash
#!/bin/bash
# backup.sh - 每日备份脚本

BACKUP_DIR="/backups/bt-publisher/$(date +%Y%m%d)"
mkdir -p $BACKUP_DIR

cp config.yaml $BACKUP_DIR/
cp data/tasks.json $BACKUP_DIR/
cp data/processed_files.json $BACKUP_DIR/

# 保留最近 30 天的备份
find /backups/bt-publisher/ -type d -mtime +30 -exec rm -rf {} \;

echo "Backup completed: $BACKUP_DIR"
```

**设置定时任务：**

```bash
crontab -e
# 添加以下行（每天凌晨 3 点备份）
0 3 * * * /path/to/backup.sh >> /var/log/backup.log 2>&1
```

---

### 4. 监控与告警

#### 健康检查端点

定期请求：

```bash
curl http://localhost:8080/api/status
```

关注指标：
- `worker_running`: 是否为 true
- `queue_size`: 是否异常增大（可能卡住）
- `stats.failed`: 失败数是否激增

---

#### 日志监控

监控关键错误关键词：

```bash
# 实时监控 ERROR 级别日志
tail -f logs/video_scanner.log | grep ERROR

# 统计今日失败次数
grep "$(date +%Y-%m-%d)" logs/video_scanner.log | grep -c "FAILED"
```

---

### 5. 安全加固

如果需要暴露到公网：

1. **添加认证中间件：**
   ```python
   # 在 api.py 中添加
   from fastapi import Depends, HTTPException, status
   from fastapi.security import HTTPBasic, HTTPBasicCredentials
   
   security = HTTPBasic()
   
   def verify_credentials(credentials: HTTPBasicCredentials = Depends(security)):
       if not (credentials.username == "admin" and credentials.password == "your_password"):
           raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED)
       
       return True
   
   @app.get("/api/status", dependencies=[Depends(verify_credentials)])
   def get_status():
       ...
   ```

2. **使用 HTTPS：**
   - 反向代理（Nginx/Apache）配置 SSL 证书
   - 或使用 Uvicorn 内置 SSL 支持

3. **限制 IP 访问：**
   - 防火墙规则
   - Nginx `allow/deny` 指令

4. **定期更新 Cookie：**
   - Cookie 通常有有效期
   - 设置提醒定期重新导出

---

## 总结

通过本文档，你应该能够：

✅ 成功安装和配置 BT 自动发布系统  
✅ 理解所有配置选项的含义  
✅ 配置 OKP 并导出 Cookie  
✅ 选择合适的运行模式  
✅ 进行日常运维操作  
✅ 排查常见问题  
✅ 部署到生产环境  

如有其他问题，请查阅：
- [系统架构文档](architecture.md) - 了解技术细节
- [任务流程文档](workflow.md) - 深入理解工作原理
- [API 接口文档](api.md) - 开发自定义集成
- [开发指南](development.md) - 参与代码贡献

---

**文档版本：** v2.1  
**最后更新：** 2026-04-05  
**作者：** BT Auto Publishing Team
