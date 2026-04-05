# 💻 开发指南

> BT 自动发布系统 v2.1 - 开发规范、模块详解、扩展开发

---

## 目录

- [开发环境搭建](#开发环境搭建)
- [代码规范](#代码规范)
- [项目结构详解](#项目结构详解)
- [核心模块说明](#核心模块说明)
- [如何添加新功能](#如何添加新功能)
- [调试技巧](#调试技巧)
- [测试指南](#测试指南)
- [贡献流程](#贡献流程)

---

## 开发环境搭建

### 必需工具

| 工具 | 版本要求 | 用途 |
|------|---------|------|
| Python | 3.10+ | 开发语言 |
| VS Code / PyCharm | 最新版 | IDE（推荐 VS Code）|
| Git | 2.x | 版本控制 |

### 推荐的 VS Code 扩展

- **Python** - Microsoft 官方 Python 扩展
- **Pylance** - Python 语言服务器（类型检查、自动补全）
- **YAML** - YAML 文件语法高亮和验证
- **Thunder Client** 或 **REST Client** - API 测试工具

### 环境初始化

```bash
# 1. 克隆仓库
git clone <your-repo-url>
cd BT_Automatic_Publishing_copy

# 2. 创建虚拟环境
python -m venv .venv

# Windows
.venv\Scripts\activate

# Linux/macOS
source .venv/bin/activate

# 3. 安装依赖
pip install -r requirements.txt

# 4. 安装开发依赖（可选）
pip install pytest black isort mypy

# 5. 验证安装
python --version
python -c "import fastapi; print('FastAPI:', fastapi.__version__)"
```

### VS Code 配置

创建 `.vscode/settings.json`：

```json
{
    "python.defaultInterpreterPath": "${workspaceFolder}/.venv/Scripts/python.exe",
    "python.formatting.provider": "black",
    "python.linting.enabled": true,
    "python.linting.pylintEnabled": false,
    "files.eol": "\n",
    "files.insertFinalNewline": true,
    "editor.tabSize": 4,
    "editor.insertSpaces": true
}
```

---

## 代码规范

### 基本原则

#### ✅ 遵守规范

1. **不使用类型注解**（basedpyright 兼容性）
   ```python
   # ❌ 错误写法
   def process_task(task: Task) -> bool:
       ...
   
   # ✅ 正确写法
   def process_task(task):
       ...
   ```

2. **所有异常必须捕获**
   ```python
   try:
       result = risky_operation()
   except Exception as e:
       logger.error(f"Operation failed: {e}", exc_info=True)
       # 不要让异常导致程序崩溃
   ```

3. **提供清晰的日志**
   ```python
   logger.info(f"[{task_id}] Starting task processing")
   logger.warning(f"[{task_id}] Retry attempt {retry_count + 1}")
   logger.error(f"[{task_id}] Fatal error: {error}")
   ```

4. **遵循 PEP 8 风格**
   - 使用 4 个空格缩进
   - 行长度不超过 120 字符
   - 函数和类之间空两行
   - 使用有意义的变量名

---

#### ❌ 禁止事项

```python
# 1. 不要使用 type hints
def foo(x: int) -> str:  # ❌
    ...

# 2. 不要裸 except
try:
    ...except:  # ❌ 太宽泛
    ...

# 3. 不要忽略异常
try:
    ...except Exception:  # ❌ 没有处理
    pass

# 4. 不要使用 print() 记录日志
print("Task started")  # ❌ 使用 logger
logger.info("Task started")  # ✅
```

---

### 命名规范

| 类型 | 规范 | 示例 |
|------|------|------|
| **文件名** | 小写下划线 | `task_worker.py`, `api.py` |
| **类名** | 大驼峰 | `TaskWorker`, `TaskQueue` |
| **函数/方法** | 小写下划线 | `get_task_info()`, `_handle_upload()` |
| **变量** | 小写下划线 | `task_id`, `video_path` |
| **常量** | 大写下划线 | `MAX_RETRIES`, `DEFAULT_CONFIG` |
| **私有方法** | 单下划线前缀 | `_process_task()`, `_recover_tasks()` |

---

### 注释规范

#### 函数注释（Docstring）

```python
def requeue_for_retry(self, task, delay_seconds=20):
    """
    延迟重试入队
    
    在独立线程中等待指定时间后将任务重新放回队列，
    不阻塞主 Worker 循环。
    
    Args:
        task: 要重试的任务对象
        delay_seconds: 延迟秒数
    
    Returns:
        None
    
    Example:
        >>> queue.requeue_for_retry(task, 30)
        # 30秒后任务会自动重新入队
    """
```

#### 行内注释

```python
# 检查文件是否存在（避免 FileNotFoundError）
if not Path(video_path).exists():
    raise FileNotFoundError(f"Video file not found: {video_path}")

# 使用守护线程（程序退出时自动终止）
retry_thread = threading.Thread(target=_delayed_enqueue, daemon=True)
```

---

## 项目结构详解

### 完整目录树

```
BT_Automatic_Publishing_copy/
│
├── main.py                          # 🚀 主入口，启动所有组件
├── config.yaml                      # ⚙️ 配置文件
├── requirements.txt                 # 📦 Python 依赖列表
├── README.md                        # 📖 项目简介（简洁版）
│
├── docs/                            # 📚 详细文档
│   ├── architecture.md              # 系统架构文档
│   ├── workflow.md                  # 任务流程文档
│   ├── api.md                       # REST API 文档
│   ├── deployment.md                # 部署说明文档
│   └── development.md               # 本文件：开发指南
│
├── src/                             # 🔧 源代码根目录
│   │
│   ├── __init__.py                  # 包初始化
│   │
│   ├── config.py                    # 📋 配置加载器
│   │                               #   - YAML 解析
│   │                               #   - 默认值管理
│   │                               #   - 路径验证
│   │
│   ├── logger.py                    # 📝 日志系统
│   │                               #   - 双处理器（控制台 + 文件）
│   │                               #   - 日志轮转
│   │                               #   - 多级别支持
│   │
│   └── web/                         # 🌐 Web 面板层 (v2.1 新增)
│       ├── __init__.py
│       │
│       ├── api.py                   # FastAPI 后端
│       │                           #   - RESTful API 路由
│       │                           #   - SSE 实时日志
│       │                           #   - 任务 CRUD 操作
│       │
│       └── panel.html               # 前端面板
│                                   #   - 单文件 HTML
│                                   #   - 内嵌 CSS + JS
│                                   #   - 零外部依赖
│
│   └── core/                        # ⚙️ 核心业务逻辑
│       ├── __init__.py
│       │
│       │  ════════════════════════════════════
│       │  v2.0 架构新增模块（队列系统）
│       │  ════════════════════════════════════
│       │
│       ├── task_model.py            # 📋 Task 数据模型
│       │                           #   - TaskStatus 枚举
│       │                           #   - Task dataclass
│       │                           #   - PublishInfo, VideoMeta 等
│       │                           #   - 状态转换方法
│       │
│       ├── task_persistence.py      # 💾 持久化存储
│       │                           #   - JSON 读写
│       │                           #   - 线程安全
│       │                           #   - CRUD 操作
│       │
│       ├── task_queue.py            # 📦 任务队列
│       │                           #   - FIFO 队列
│       │                           #   - 去重检查
│       │                           #   - 断点恢复
│       │                           #   - 统计信息
│       │
│       └── task_worker.py           # ⚙️ Worker 执行引擎
│                                   #   - 状态机驱动
│                                   #   - 任务调度
│                                   #   - 重试逻辑
│                                   #   - 异常处理
│       │
│       │  ════════════════════════════════════
│       │  v1.x 核心业务模块
│       │  ════════════════════════════════════
│       │
│       ├── watcher.py               # 👁️ 文件监控
│       │                           #   - Watchdog 集成
│       │                           #   - 事件回调
│       │                           #   - 文件过滤
│       │
│       ├── scanner.py               # 🔍 MD5 去重检测
│       │                           #   - 文件哈希计算
│       │                           #   - 已处理记录
│       │
│       ├── probe.py                 # 🎬 视频信息提取
│       │                           #   - PyMediaInfo 封装
│       │                           #   - 元数据解析
│       │
│       ├── normalizer.py            # 📐 任务标准化
│       │                           #   - 文件名解析
│       │                           #   - 发布信息生成
│       │
│       ├── planner.py               # 📋 任务规划器（旧版）
│       │                           #   - v1.x 流程编排
│       │                           #   - （v2.0 已弃用）
│       │
│       ├── torrent_builder.py       # 📦 Torrent 生成器
│       │                           #   - torf 库封装
│       │                           #   - Tracker 管理
│       │                           #   - 文件遍历
│       │
│       └── executor_okp.py          # 🚀 OKP 执行器
│                                   #   - subprocess 调用
│                                   #   - 编码问题修复
│                                   #   - 三种运行模式
│                                   #   - 输出解析
│
└── data/                            # 💾 运行时数据
    ├── watch/                      # 📂 监控目录
    │   └── (用户放置视频文件)         #     支持的视频会自动被处理
    │
    ├── torrents/                   # 📂 Torrent 输出
    │   └── *.torrent               #     生成的种子文件
    │
    ├── processed/                  # 📂 已处理文件备份
    │
    ├── logs/                       # 📂 日志存储
    │   ├── video_scanner.log       #     主日志文件
    │   └── video_scanner_YYYYMMDD.log  #     按日期归档
    │
    ├── tasks.json                  # 💾 任务数据库
    │                               #     JSON 格式，实时更新
    │
    └── processed_files.json         # 🔐 MD5 去重库
                                    #     记录已处理的文件哈希值
```

---

## 核心模块说明

### 1️⃣ main.py - 主入口

**职责：** 启动所有组件并协调它们的工作

**核心流程：**

```python
def main():
    """主函数"""
    
    # 1. 初始化配置
    config = load_config()
    
    # 2. 初始化日志
    setup_logger(config['log_dir'], config['log_level'])
    
    # 3. 初始化持久化层
    persistence = TaskPersistence(get_db_path())
    
    # 4. 初始化任务队列
    task_queue = TaskQueue(persistence)
    
    # 5. 初始化 Worker
    worker = TaskWorker(task_queue)
    
    # 6. 初始化 Watcher
    watcher = VideoFileHandler(
        watch_dir=config['watch_dir'],
        task_queue=task_queue,
        # ... 其他参数
    )
    
    # 7. 初始化 Web 面板（可选）
    if config.get('web_enabled', True):
        init_web(task_queue, worker)
    
    # 8. 启动所有组件
    observer = Observer()
    observer.schedule(watcher, path=config['watch_dir'], recursive=False)
    observer.start()
    
    worker_thread = worker.start()
    
    if config.get('web_enabled', True):
        uvicorn.run(app, host=config['web_host'], port=config['web_port'])
    
    # 9. 等待退出信号
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        # 优雅关闭
        observer.stop()
        worker.stop()
        
        # 输出统计
        worker.print_statistics()

if __name__ == "__main__":
    main()
```

**关键点：**
- 组件启动顺序很重要（先底层，后上层）
- 使用 `KeyboardInterrupt` 实现优雅关闭
- 所有组件都是可单独替换的

---

### 2️⃣ config.py - 配置加载器

**职责：** 加载、验证和管理配置

**核心功能：**

```python
import yaml
from pathlib import Path

# 默认配置
DEFAULT_CONFIG = {
    'watch_dir': './data/watch',
    'output_torrent_dir': './data/torrents',
    'log_dir': './logs',
    'okp_auto_confirm': True,
    'okp_preview_only': False,
    'okp_timeout': 300,
    'web_enabled': True,
    'web_port': 8080,
    'video_extensions': ['.mkv', '.mp4', '.avi'],
    'tracker_urls': [
        'http://open.acgtracker.com:1096/announce',
        # ... 更多 tracker
    ],
}

_config_cache = None

def load_config(config_path='config.yaml'):
    """
    加载配置文件并与默认值合并
    
    Returns:
        dict: 合并后的完整配置
    """
    global _config_cache
    
    if _config_cache:
        return _config_cache
    
    # 1. 从 YAML 文件加载
    config = {}
    if Path(config_path).exists():
        with open(config_path, 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f) or {}
    
    # 2. 与默认值合并（用户配置覆盖默认值）
    merged_config = {**DEFAULT_CONFIG, **config}
    
    # 3. 验证必要字段
    _validate_config(merged_config)
    
    # 4. 缓存结果
    _config_cache = merged_config
    
    return merged_config

def get_config(key=None, default=None):
    """
    获取配置项（支持点号访问嵌套字段）
    
    Examples:
        >>> get_config('watch_dir')
        './data/watch'
        
        >>> get_config('okp_timeout', 300)
        300
    """
    config = load_config()
    
    if key is None:
        return config
    
    return config.get(key, default)

def WATCH_DIR():
    return Path(get_config('watch_dir')).resolve()

def OUTPUT_TORRENT_DIR():
    return Path(get_config('output_torrent_dir')).resolve()
```

**设计特点：**
- 延迟加载（首次访问时才读取）
- 缓存机制（避免重复 I/O）
- 默认值回退（缺失字段使用默认值）
- 类型安全的辅助函数

---

### 3️⃣ logger.py - 日志系统

**职责：** 提供统一的日志接口

**特性：**

```python
import logging
from logging.handlers import RotatingFileHandler

def setup_logger(log_dir, log_level='INFO'):
    """
    初始化双处理器日志系统
    
    Args:
        log_dir: 日志目录路径
        log_level: 日志级别 (DEBUG/INFO/WARNING/ERROR)
    """
    # 创建日志目录
    Path(log_dir).mkdir(parents=True, exist_ok=True)
    
    # 创建 Logger
    logger = logging.getLogger('BTAutoPublisher')
    logger.setLevel(getattr(logging, log_level.upper()))
    
    # 格式化器
    formatter = logging.Formatter(
        fmt='%(asctime)s %(levelname)-8s %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    # 处理器 1: 控制台输出
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)
    
    # 处理器 2: 文件输出（带轮转）
    log_file = Path(log_dir) / 'video_scanner.log'
    file_handler = RotatingFileHandler(
        filename=log_file,
        maxBytes=100 * 1024 * 1024,  # 100 MB
        backupCount=5,                 # 保留 5 个备份
        encoding='utf-8'
    )
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)
    
    return logger


# 使用示例
logger = setup_logger('./logs')

logger.debug("Debug message")     # 开发调试
logger.info("Info message")       # 一般信息
logger.warning("Warning message") # 警告
logger.error("Error message")     # 错误
```

**日志轮转机制：**
- 单个文件最大 100 MB
- 自动保留最近 5 个历史文件
- 按日期命名归档文件

---

### 4️⃣ task_model.py - 数据模型

**职责：** 定义所有数据结构和状态枚举

**核心类：**

```python
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime
from typing import Optional

class TaskStatus(Enum):
    """任务状态枚举"""
    NEW = "new"
    TORRENT_CREATING = "torrent_creating"
    TORRENT_CREATED = "torrent_created"
    UPLOADING = "uploading"
    SUCCESS = "success"
    FAILED = "failed"
    PERMANENT_FAILED = "permanent_failed"


@dataclass
class PublishInfo:
    """发布信息"""
    title: str = ""
    subtitle: str = ""
    tags: str = ""
    description: str = ""
    about: str = ""
    poster: str = ""
    group_name: str = ""
    category: str = ""
    source: str = ""
    video_codec: str = ""
    audio_codec: str = ""
    subtitle_type: str = ""


@dataclass
class VideoMeta:
    """视频元数据"""
    resolution: str = ""
    codec: str = ""
    duration_seconds: float = 0.0
    file_size: int = 0
    width: int = 0
    height: int = 0
    md5: str = ""


@dataclass
class TorrentMeta:
    """Torrent 元数据"""
    name: str = ""
    size: int = 0
    file_count: int = 0
    files: list = field(default_factory=list)
    tracker_count: int = 0
    tracker_sample: list = field(default_factory=list)


@dataclass
class OKPResult:
    """OKP 执行结果"""
    mode: str = ""
    success: bool = False
    returncode: int = 0
    stdout: str = ""
    stderr: str = ""
    error: Optional[str] = None
    command: str = ""


@dataclass
class Task:
    """任务主体"""
    id: str                          # 唯一标识
    video_path: str                  # 视频路径
    torrent_path: Optional[str]      # Torrent 路径
    status: TaskStatus               # 当前状态
    retry_count: int = 0             # 重试次数
    max_retries: int = 3             # 最大重试次数
    error_message: Optional[str]     # 错误信息
    created_at: str = ""             # 创建时间
    updated_at: str = ""             # 更新时间
    
    publish_info: PublishInfo = field(default_factory=PublishInfo)
    video_meta: VideoMeta = field(default_factory=VideoMeta)
    torrent_meta: TorrentMeta = field(default_factory=TorrentMeta)
    okp_result: Optional[OKPResult] = None
    
    def update_status(self, new_status, error=None):
        """更新状态（带验证）"""
        # ... 状态转换规则验证
        
    def can_retry(self):
        """是否可以重试"""
        return self.status == TaskStatus.FAILED and self.retry_count < self.max_retries
    
    def to_dict(self):
        """序列化为字典"""
        # ...
    
    @staticmethod
    def from_dict(data):
        """从字典反序列化"""
        # ...
    
    @staticmethod
    def generate_id(video_path):
        """基于视频路径生成唯一 ID"""
        import hashlib
        md5_hash = hashlib.md5(str(Path(video_path).resolve()).encode()).hexdigest()
        return md5_hash[:12].upper()
```

---

### 5️⃣ task_worker.py - 执行引擎

**职责：** 状态机驱动的任务执行器（最复杂的模块）

**关键方法：**

```python
class TaskWorker:
    def __init__(self, task_queue):
        self.task_queue = task_queue
        self._running = False
        
        # 从配置获取参数
        self.auto_confirm = get_config('okp_auto_confirm')
        self.preview_only = get_config('okp_preview_only')
        self.okp_timeout = get_config('okp_timeout')
        
        # 初始化子模块
        self.scanner = Scanner()
        self.probe = Probe()
        self.normalizer = Normalizer()
    
    def start(self):
        """启动 Worker 线程"""
        self._running = True
        thread = threading.Thread(target=self._run_loop, daemon=True)
        thread.start()
        return thread
    
    def stop(self):
        """停止 Worker"""
        self._running = False
    
    def _run_loop(self):
        """主循环 - 不断从队列取任务处理"""
        while self._running:
            try:
                # 阻塞等待任务（超时 1 秒以便检查停止标志）
                task = self.task_queue.dequeue(block=True, timeout=1.0)
                
                if task:
                    self._process_task(task)
                    
            except Exception as e:
                logger.error(f"Worker loop error: {e}", exc_info=True)
    
    def _process_task(self, task):
        """根据当前状态分发到对应的处理方法"""
        if task.status == TaskStatus.NEW:
            self._handle_new_task(task)
        elif task.status == TaskStatus.TORRENT_CREATED:
            self._handle_upload(task)
        else:
            logger.warning(f"[{task.id}] Unexpected status: {task.status.value}")
    
    def _handle_new_task(self, task):
        """阶段 1: 提取信息 + 生成 Torrent"""
        # ... 详见 workflow.md
    
    def _handle_upload(self, task):
        """阶段 2: 调用 OKP 发布"""
        # ... 详见 workflow.md
    
    def print_statistics(self):
        """打印最终统计信息"""
        stats = self.task_queue.get_statistics()
        print("\n📊 任务统计:")
        print(f"  ✅ 成功: {stats.get('success', 0)}")
        print(f"  ⚠️ 失败: {stats.get('failed', 0)}")
        print(f"  📋 总计: {stats.get('total', 0)}")
```

---

## 如何添加新功能

### 场景 1：添加新的视频格式支持

**步骤：**

1. **修改配置文件** (`config.yaml`)
   ```yaml
   video_extensions:
     - .mkv
     - .mp4
     - .avi
     - .rmvb    # ← 新增
   ```

2. **无需修改代码！** Watcher 会自动识别新格式。

---

### 场景 2：添加新的 BT 站点支持

**步骤：**

1. **在 `setting.toml` 中添加站点配置**
   ```toml
   [new_site]
   enabled = true
   url = "https://new-site.example.com"
   ```

2. **如果需要特殊的发布逻辑**，修改 `executor_okp.py`：

```python
def run_okp_upload(torrent_path, ..., site=None):
    """
    Args:
        site: 可选，指定目标站点
    """
    cmd = [okp_executable, torrent_path]
    
    if site:
        cmd.extend(['--site', site])  # OKP 的站点参数
    
    if auto_confirm:
        cmd.append('-y')
    
    result = subprocess.run(cmd, ...)
    return parse_result(result)
```

---

### 场景 3：添加新的通知渠道（如 Telegram）

**步骤：**

1. **创建新模块** `src/core/notifier.py`:

```python
import requests

class TelegramNotifier:
    def __init__(self, bot_token, chat_id):
        self.bot_token = bot_token
        self.chat_id = chat_id
        self.api_url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
    
    def send_message(self, text):
        payload = {
            'chat_id': self.chat_id,
            'text': text,
            'parse_mode': 'HTML'
        }
        requests.post(self.api_url, json=payload)
    
    def notify_task_success(self, task):
        msg = f"✅ <b>任务完成</b>\n\n标题: {task.publish_info.title}\n状态: {task.status.value}"
        self.send_message(msg)
    
    def notify_task_failed(self, task):
        msg = f"❌ <b>任务失败</b>\n\n标题: {task.publish_info.title}\n错误: {task.error_message}"
        self.send_message(msg)


# 全局实例
_notifier = None

def init_notifier():
    global _notifier
    bot_token = get_config('telegram_bot_token')
    chat_id = get_config('telegram_chat_id')
    
    if bot_token and chat_id:
        _notifier = TelegramNotifier(bot_token, chat_id)
        logger.info("Telegram notifier initialized")

def notify_success(task):
    if _notifier:
        _notifier.notify_task_success(task)

def notify_failure(task):
    if _notifier:
        _notifier.notify_task_failed(task)
```

2. **在 `task_worker.py` 中集成：**

```python
from src.core.notifier import notify_success, notify_failure

def _handle_upload(self, task):
    # ... 原有逻辑
    
    if result.get('success'):
        task.update_status(TaskStatus.SUCCESS)
        notify_success(task)  # ← 新增
    else:
        task.update_status(TaskStatus.FAILED, error)
        notify_failure(task)  # ← 新增
```

3. **在 `config.yaml` 中添加配置：**
   ```yaml
   telegram_bot_token: "your-bot-token"
   telegram_chat_id: "your-chat-id"
   ```

---

### 场景 4：添加新的 API 端点

**步骤：**

1. **打开 `src/web/api.py`**

2. **添加新的路由函数：**

```python
@app.get("/api/custom_endpoint")
def custom_endpoint():
    """自定义端点的描述"""
    _require_queue()
    
    # 业务逻辑
    result = do_something()
    
    return {
        "ok": True,
        "data": result
    }
```

3. **重启服务后即可访问：**
   ```bash
   curl http://localhost:8080/api/custom_endpoint
   ```

4. **Swagger UI 会自动更新**（访问 `/docs`）

---

## 调试技巧

### 1. 启用 DEBUG 日志

**临时修改：**

```yaml
# config.yaml
log_level: DEBUG
```

或**代码中动态设置：**

```python
import logging
logging.getLogger('BTAutoPublisher').setLevel(logging.DEBUG)
```

---

### 2. 使用断点调试（VS Code）

创建 `.vscode/launch.json`：

```json
{
    "version": "0.2.0",
    "configurations": [
        {
            "name": "Debug BT Publisher",
            "type": "python",
            "request": "launch",
            "program": "main.py",
            "console": "integratedTerminal",
            "cwd": "${workspaceFolder}",
            "env": {
                "PYTHONPATH": "${workspaceFolder}"
            },
            "args": []
        }
    ]
}
```

**使用方式：**
1. 在代码中设置断点（点击行号左侧）
2. 按 F5 启动调试
3. 程序会在断点处暂停
4. 查看变量、调用堆栈等

---

### 3. 快速测试单个模块

```bash
# 测试配置加载
python -c "from src.config import load_config; print(load_config())"

# 测试日志系统
python -c "from src.logger import setup_logger; logger = setup_logger('./logs'); logger.info('Test')"

# 测试 Task 模型
python -c "
from src.core.task_model import Task, TaskStatus
task = Task(id='TEST123', video_path='test.mp4', status=TaskStatus.NEW)
print(task.to_dict())
"

# 测试 Torrent 生成
python -c "
from src.core.torrent_builder import TorrentBuilder
path = TorrentBuilder.create_torrent('test.mp4', [], './data/torrents')
print(f'Torrent created: {path}')
"
```

---

### 4. 查看 OKP 原始输出

当 OKP 发布失败时，查看原始输出有助于诊断：

```bash
# 通过 API
curl http://localhost:8080/api/tasks/TASK_ID/okp_output

# 或直接查看 tasks.json 中的 okp_result 字段
```

---

### 5. 性能分析

```bash
# 使用 cProfile 分析性能瓶颈
python -m cProfile -s cumtime main.py > profile_output.txt

# 查看报告
cat profile_output.txt | head -50
```

---

## 测试指南

### 单元测试（推荐）

创建 `tests/` 目录：

```
tests/
├── __init__.py
├── test_task_model.py       # 测试数据模型
├── test_task_worker.py      # 测试执行引擎
├── test_api.py              # 测试 API 端点
└── conftest.py             # pytest fixtures
```

**示例测试：**

```python
# tests/test_task_model.py
import pytest
from src.core.task_model import Task, TaskStatus, PublishInfo

class TestTaskModel:
    
    def test_create_task(self):
        """测试创建任务"""
        task = Task(
            id="ABC123",
            video_path="/videos/test.mp4",
            status=TaskStatus.NEW
        )
        
        assert task.id == "ABC123"
        assert task.status == TaskStatus.NEW
        assert task.retry_count == 0
    
    def test_status_transition(self):
        """测试状态转换"""
        task = Task(
            id="ABC123",
            video_path="/videos/test.mp4",
            status=TaskStatus.NEW
        )
        
        # 合法转换
        task.update_status(TaskStatus.TORRENT_CREATING)
        assert task.status == TaskStatus.TORRENT_CREATING
        
        # 非法转换应抛出异常
        with pytest.raises(ValueError):
            task.update_status(TaskStatus.SUCCESS)  # 不能直接跳到成功
    
    def test_can_retry(self):
        """测试重试判断"""
        task = Task(
            id="ABC123",
            video_path="/videos/test.mp4",
            status=TaskStatus.FAILED,
            retry_count=1,
            max_retries=3
        )
        
        assert task.can_retry() == True
        
        task.retry_count = 3
        assert task.can_retry() == False
    
    def test_serialization(self):
        """测试序列化/反序列化"""
        original = Task(
            id="ABC123",
            video_path="/videos/test.mp4",
            status=TaskStatus.NEW,
            publish_info=PublishInfo(title="Test Title")
        )
        
        data = original.to_dict()
        restored = Task.from_dict(data)
        
        assert restored.id == original.id
        assert restored.publish_info.title == "Test Title"
```

**运行测试：**

```bash
# 运行所有测试
pytest tests/ -v

# 运行特定测试文件
pytest tests/test_task_model.py -v

# 运行并生成覆盖率报告
pytest tests/ --cov=src --cov-report=html
```

---

### 集成测试

测试完整的任务处理流程：

```python
# tests/integration_test_workflow.py
import pytest
import tempfile
from pathlib import Path
from src.core.task_model import Task, TaskStatus
from src.core.task_queue import TaskQueue
from src.core.task_persistence import TaskPersistence

class TestWorkflowIntegration:
    
    @pytest.fixture
    def temp_db(self, tmp_path):
        """创建临时数据库"""
        db_path = tmp_path / "tasks.json"
        return TaskPersistence(str(db_path))
    
    @pytest.fixture
    def queue(self, temp_db):
        """创建测试队列"""
        return TaskQueue(temp_db)
    
    def test_full_workflow(self, queue):
        """测试完整工作流：入队 → 处理 → 完成"""
        # 1. 创建任务
        task = Task(
            id="TEST001",
            video_path="/tmp/test.mp4",
            status=TaskStatus.NEW
        )
        
        # 2. 入队
        success = queue.enqueue(task)
        assert success == True
        assert queue.queue_size() == 1
        
        # 3. 出队
        retrieved = queue.dequeue(block=False)
        assert retrieved is not None
        assert retrieved.id == "TEST001"
        
        # 4. 模拟处理
        retrieved.update_status(TaskStatus.SUCCESS)
        temp_db.save_task(retrieved)
        
        # 5. 验证持久化
        loaded = temp_db.get_task("TEST001")
        assert loaded.status == TaskStatus.SUCCESS
```

---

### 手动测试清单

在提交代码前，请手动验证以下场景：

- [ ] 启动程序无报错
- [ ] Web 面板可以正常访问（`http://localhost:8080`）
- [ ] 将测试视频放入 `data/watch/` 能被正确发现
- [ ] 任务能正常完成整个流程（NEW → TORRENT_CREATED → SUCCESS）
- [ ] 失败任务能正确重试
- [ ] Ctrl+C 能优雅关闭
- [ ] 重启后能恢复未完成任务
- [ ] 所有 API 端点返回正确的数据
- [ ] 日志文件正常写入且无乱码

---

## 贡献流程

### 1. Fork 并克隆

```bash
# Fork 仓库后
git clone https://github.com/YOUR_USERNAME/BT_Automatic_Publishing.git
cd BT_Automatic_Publishing
git checkout -b feature/your-feature-name
```

---

### 2. 编写代码

- 遵循[代码规范](#代码规范)
- 为新功能编写测试
- 更新相关文档

---

### 3. 本地测试

```bash
# 运行单元测试
pytest tests/ -v

# 手动测试主要功能
python main.py
# 在另一个终端测试 API
curl http://localhost:8080/api/status
```

---

### 4. 提交代码

```bash
git add .
git commit -m "feat: add new feature description

- Detailed explanation of what changed
- Why this change was made
- Any breaking changes or caveats"
```

**Commit Message 规范：**

| 类型 | 说明 | 示例 |
|------|------|------|
| `feat` | 新功能 | `feat: add Telegram notification support` |
| `fix` | Bug 修复 | `fix: resolve Windows encoding issue` |
| `docs` | 文档更新 | `docs: update API documentation` |
| `refactor` | 重构 | `refactor: simplify task state machine` |
| `style` | 代码风格 | `style: format code with black` |
| `test` | 测试 | `test: add unit tests for task model` |
| `chore` | 构建/工具 | `chore: update dependencies` |

---

### 5. 创建 Pull Request

1. 推送到你的 fork：
   ```bash
   git push origin feature/your-feature-name
   ```

2. 在 GitHub 上创建 PR：
   - 填写清晰的标题和描述
   - 关联相关的 Issue（如有）
   - 确保 CI 检查通过

3. 等待 Code Review 和合并

---

### Code Review 清单

PR 应该满足以下条件：

- [ ] 代码符合[规范](#代码规范)
- [ ] 新功能有对应的测试
- [ ] 文档已更新（README / docs/）
- [ ] 没有 `print()` 调试语句残留
- [ ] 没有硬编码的路径或密钥
- [ ] 异常处理完善
- [ ] 日志记录清晰

---

## 总结

通过本文档，你应该能够：

✅ 搭建完整的开发环境  
✅ 理解并遵守代码规范  
✅ 熟悉项目的整体架构  
✅ 理解每个核心模块的职责  
✅ 自主添加新功能  
✅ 进行有效的调试  
✅ 编写和运行测试  
✅ 参与开源贡献  

如果你是第一次参与本项目，建议按以下顺序学习：

1. 先阅读 [架构文档](architecture.md) 了解整体设计
2. 再阅读 [任务流程文档](workflow.md] 理解业务逻辑
3. 然后阅读本文档了解实现细节
4. 最后尝试修复一个小 Issue 来练手

欢迎为项目做出贡献！🎉

---

**文档版本：** v2.1  
**最后更新：** 2026-04-05  
**作者：** BT Auto Publishing Team
