# 🏗️ 系统架构文档

> BT 自动发布系统 v2.1 - 架构设计详解

---

## 目录

- [架构概览](#架构概览)
- [系统架构图](#系统架构图)
- [核心组件](#核心组件)
- [数据流设计](#数据流设计)
- [设计模式](#设计模式)
- [技术选型](#技术选型)
- [并发模型](#并发模型)

---

## 架构概览

本系统采用 **生产者-消费者** 架构模式，结合 **状态机驱动** 的任务执行引擎，实现 7×24 小时无人值守的自动发布流程。

### 核心设计理念

```
┌──────────────┐     ┌──────────────┐     ┌──────────────┐
│   Watcher    │────▶│  TaskQueue   │────▶│ TaskWorker   │
│  (生产者)    │     │  (队列缓冲)   │     │  (消费者)     │
└──────────────┘     └──────────────┘     └──────────────┘
      │                   │                     │
      ▼                   ▼                     ▼
  文件发现            去重/持久化          状态机执行
  快速入队            断点恢复              Torrent生成+OKP发布
```

### 架构优势

| 特性 | 说明 |
|------|------|
| **解耦** | 文件监控与任务处理完全分离，互不阻塞 |
| **可扩展** | 易于添加多个 Worker 并发处理 |
| **容错** | 每个任务独立失败，不影响其他任务 |
| **可恢复** | JSON 实时持久化，断电重启后继续 |

---

## 系统架构图

### 整体架构（v2.0）

```
┌─────────────────────────────────────────────────────────────────┐
│                    BT 自动发布系统 v2.1                          │
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
│  ┌─────────────────────────────────────────────────────────┐   │
│  │                  Web 面板层 (v2.1 新增)                   │   │
│  │  ┌─────────────┐  ┌─────────────────────────────────┐  │   │
│  │  │ FastAPI API │◄─│         panel.html (前端)        │  │   │
│  │  │ (REST/SSE)  │  │  单文件，零外部依赖              │  │   │
│  │  └──────┬──────┘  └─────────────────────────────────┘  │   │
│  └─────────┼──────────────────────────────────────────────┘   │
│            │                                                  │
│            ▼                                                  │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │                    外部依赖                               │   │
│  │  ┌────────┐  ┌────────┐  ┌────────┐  ┌──────────────┐  │   │
│  │  │ OKP    │  │ torf   │  │PyMedia │  │  Watchdog    │  │   │
│  │  │(BT发布)│  │(Torrent)│  │Info    │  │ (文件监控)   │  │   │
│  │  └────────┘  └────────┘  └────────┘  └──────────────┘  │   │
│  └─────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────┘
```

### 运行时数据流

```
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
                                    │          │          │
                                    ▼          ▼          ▼
                              Torrent文件  发布结果   视频信息
```

---

## 核心组件

### 1️⃣ Watcher（文件监控器）

**文件位置：** `src/core/watcher.py`

**职责：**
- 监控指定文件夹的新视频文件
- 验证文件格式（.mkv / .mp4 / .avi）
- 创建 Task 对象并放入队列
- **只负责入队，不阻塞主线程**

**关键特性：**
```python
def on_created(self, event):
    # 1. 验证扩展名
    if not self._is_video_file(event.src_path):
        return
    
    # 2. 等待文件写入完成
    time.sleep(1)
    
    # 3. 创建 Task（非阻塞）
    task = Task(
        id=Task.generate_id(event.src_path),
        video_path=event.src_path,
        status=TaskStatus.NEW
    )
    
    # 4. 入队（立即返回）
    self.task_queue.enqueue(task)
```

**改造历史：**
- **v1.x：** 同步调用 `Planner.process_task()`（阻塞）
- **v2.0：** 改为异步入队，Worker 独立处理

---

### 2️⃣ TaskQueue（任务队列）

**文件位置：** `src/core/task_queue.py`

**职责：**
- 管理任务队列（FIFO）
- 去重检查（基于 MD5）
- 断点恢复（启动时加载未完成任务）
- 提供统计信息

**核心 API：**

```python
class TaskQueue:
    def enqueue(self, task: Task) -> bool:
        """入队（带去重检查）"""
        
    def dequeue(self, block=True, timeout=1.0) -> Optional[Task]:
        """出队（阻塞等待）"""
        
    def requeue_for_retry(self, task: Task, delay_seconds=20):
        """延迟重试入队（不阻塞主线程）"""
        
    def get_statistics(self) -> dict:
        """获取队列统计信息"""
```

**特殊方法：**
- `_recover_pending_tasks()` - 启动时自动恢复未完成任务
- `requeue_for_retry()` - 在独立线程中延迟后重新入队

---

### 3️⃣ TaskWorker（执行引擎）⭐ 核心

**文件位置：** `src/core/task_worker.py`

**职责：**
- 从队列取出任务
- 通过 **状态机** 驱动任务执行
- 调用子模块完成具体工作
- 处理异常和重试逻辑

**内部流程：**

```python
class TaskWorker:
    def _run_loop(self):
        """主循环"""
        while self._running:
            task = self.task_queue.dequeue()
            if task:
                self._process_task(task)
    
    def _process_task(self, task: Task):
        """处理单个任务"""
        try:
            if task.status == TaskStatus.NEW:
                self._handle_new_task(task)      # 阶段1: Torrent生成
            elif task.status == TaskStatus.TORRENT_CREATED:
                self._handle_upload(task)         # 阶段2: OKP发布
        except Exception as e:
            task.update_status(TaskStatus.PERMANENT_FAILED, str(e))
    
    def _handle_new_task(self, task):
        """阶段1: 提取信息 + 生成 Torrent"""
        # 1. 视频信息提取
        video_info = self.probe.get_video_info(task.video_path)
        # 2. MD5 去重检查
        if self.scanner.is_processed(video_info['md5']):
            raise Exception("文件已处理")
        # 3. 标准化任务
        task.publish_info = self.normalizer.normalize(video_info)
        # 4. 生成 Torrent
        task.torrent_path = TorrentBuilder.create_torrent(...)
        # 5. 更新状态
        task.update_status(TaskStatus.TORRENT_CREATED)
    
    def _handle_upload(self, task):
        """阶段2: 调用 OKP 发布"""
        result = OKPExecutor.run_okp_upload(
            torrent_path=task.torrent_path,
            auto_confirm=self.auto_confirm,
            preview_only=self.preview_only
        )
        if result['success']:
            task.update_status(TaskStatus.SUCCESS)
        else:
            task.update_status(TaskStatus.FAILED, result.get('error'))
```

**复用的子模块：**

| 子模块 | 用途 | 调用方式 |
|--------|------|---------|
| Scanner | MD5 去重 | `self.scanner.is_processed()` |
| Probe | 视频信息提取 | `self.probe.get_video_info()` |
| Normalizer | 任务标准化 | `self.normalizer.normalize()` |
| TorrentBuilder | Torrent 生成 | `TorrentBuilder.create_torrent()` |
| OKPExecutor | OKP 调用 | `OKPExecutor.run_okp_upload()` |

---

### 4️⃣ TaskPersistence（持久化存储）

**文件位置：** `src/core/task_persistence.py`

**职责：**
- JSON 格式存储任务数据
- 线程安全读写（`threading.Lock`）
- 实时写入（每次状态变化立即保存）

**存储格式：**

```json
{
  "A1B2C3D4E5F6": {
    "id": "A1B2C3D4E5F6",
    "video_path": "D:/videos/test.mp4",
    "torrent_path": "data/torrents/test.torrent",
    "status": "success",
    "retry_count": 0,
    "max_retries": 3,
    "error_message": null,
    "created_at": "2026-01-15T10:30:00",
    "updated_at": "2026-01-15T10:35:00"
  }
}
```

**API 接口：**

```python
class TaskPersistence:
    def save_task(self, task: Task):
        """保存/更新任务（实时写入）"""
        
    def get_task(self, task_id: str) -> Optional[Task]:
        """查询单个任务"""
        
    def get_all_tasks(self) -> dict[str, Task]:
        """查询所有任务"""
        
    def get_pending_tasks(self) -> list[Task]:
        """获取未完成任务（用于断点恢复）"""
        
    def delete_task(self, task_id: str):
        """删除任务"""
```

---

### 5️⃣ Web 面板层（v2.1 新增）

#### FastAPI 后端

**文件位置：** `src/web/api.py`

**职责：**
- 提供 RESTful API
- SSE 实时日志推送
- 任务 CRUD 操作
- 配置查看

**核心路由：**

```python
app = FastAPI(title="BT 自动发布系统")

# 系统状态
@app.get("/api/status")
@app.get("/api/config")

# 任务管理
@app.get("/api/tasks")
@app.get("/api/tasks/{task_id}")
@app.put("/api/tasks/{task_id}/publish_info")
@app.post("/api/tasks/{task_id}/retry")
@app.delete("/api/tasks/{task_id}")

# 手动操作
@app.post("/api/tasks/trigger")
@app.post("/api/tasks/clear_failed")

# 日志
@app.get("/api/logs")
@app.get("/api/logs/stream")  # SSE
```

#### 前端面板

**文件位置：** `src/web/panel.html`

**技术特点：**
- **单文件 HTML**，内嵌 CSS + JS
- **零外部依赖**（不需要 npm/CDN/Node.js）
- **离线友好**（可直接打包进 Docker）
- **实时通信** 使用 Server-Sent Events (SSE)

**功能模块：**
- 📊 仪表盘（任务统计）
- 📋 任务列表（分页、过滤、搜索）
- ✏️ 发布编辑器（表单填写）
- 📝 实时日志（SSE 推送）
- ⚙️ 配置查看

---

## 数据流设计

### 任务生命周期数据流

```
视频文件
  │
  ├─▶ Watcher.on_created()
  │     └─ 创建 Task(status=NEW)
  │           │
  │           ▼
  │     TaskQueue.enqueue()
  │           │ (去重检查)
  │           ▼
  │     data/tasks.json (持久化)
  │           │
  │           ▼
  │     TaskWorker._run_loop()
  │           │
  │           ▼
  │     _handle_new_task()
  │           ├─ Probe.get_video_info() → video_meta
  │           ├─ Scanner.is_processed() → md5_check
  │           ├─ Normalizer.normalize() → publish_info
  │           ├─ TorrentBuilder.create_torrent() → torrent_path
  │           └─ status: NEW → TORRENT_CREATED
  │                 │
  │                 ▼
  │           _handle_upload()
  │                 ├─ OKPExecutor.run_okp_upload() → okp_result
  │                 └─ status: TORRENT_CREATED → SUCCESS/FAILED
  │                       │
  │                       ▼
  │                 data/tasks.json (更新)
  │                       │
  │                       ▼
  │                 Web Panel (SSE 推送更新)
```

### 数据模型关系

```
Task (主实体)
  ├── id: str                          # 唯一标识
  ├── video_path: str                  # 视频路径
  ├── torrent_path: str                # Torrent路径
  ├── status: TaskStatus               # 当前状态
  ├── retry_count: int                 # 重试次数
  ├── error_message: str               # 错误信息
  ├── created_at: str                  # 创建时间
  ├── updated_at: str                  # 更新时间
  │
  ├── publish_info: PublishInfo        # 发布信息
  │     ├── title: str
  │     ├── subtitle: str
  │     ├── tags: str
  │     ├── description: str
  │     ├── category: str
  │     └── ...
  │
  ├── video_meta: VideoMeta            # 视频元数据
  │     ├── resolution: str
  │     ├── codec: str
  │     ├── duration_seconds: float
  │     └── file_size: int
  │
  ├── torrent_meta: TorrentMeta        # Torrent 元数据
  │     ├── name: str
  │     ├── size: int
  │     ├── file_count: int
  │     └── tracker_count: int
  │
  └── okp_result: OKPResult            # 执行结果
        ├── mode: str
        ├── success: bool
        ├── returncode: int
        ├── stdout: str
        ├── stderr: str
        └── error: str
```

---

## 设计模式

### 1. 生产者-消费者模式

**应用场景：** Watcher → Queue → Worker

```python
# 生产者（Watcher）
def on_created(self, event):
    task = create_task(event)
    queue.enqueue(task)  # 非阻塞

# 消费者（Worker）
while running:
    task = queue.dequeue(block=True)  # 阻塞等待
    process(task)
```

**优势：**
- 解耦文件监控和任务处理
- 平衡生产和消费速度
- 支持多 Worker 扩展

---

### 2. 状态机模式

**应用场景：** Task 生命周期管理

```python
class TaskStatus(Enum):
    NEW = "new"
    TORRENT_CREATING = "torrent_creating"
    TORRENT_CREATED = "torrent_created"
    UPLOADING = "uploading"
    SUCCESS = "success"
    FAILED = "failed"
    PERMANENT_FAILED = "permanent_failed"

def update_status(self, new_status, error=None):
    # 状态转换验证
    allowed_transitions = {
        TaskStatus.NEW: [TaskStatus.TORRENT_CREATING],
        TaskStatus.TORRENT_CREATING: [TaskStatus.TORRENT_CREATED, TaskStatus.PERMANENT_FAILED],
        TaskStatus.TORRENT_CREATED: [TaskStatus.UPLOADING],
        TaskStatus.UPLOADING: [TaskStatus.SUCCESS, TaskStatus.FAILED],
        TaskStatus.FAILED: [TaskStatus.UPLOADING, TaskStatus.PERMANENT_FAILED],
    }
    
    if new_status not in allowed_transitions[self.status]:
        raise ValueError(f"Invalid transition: {self.status} -> {new_status}")
    
    self.status = new_status
    self.error_message = error
    self.updated_at = datetime.now().isoformat()
```

**优势：**
- 明确的状态转换规则
- 易于追踪和调试
- 防止非法状态跳转

---

### 3. 策略模式

**应用场景：** 多编码解码尝试

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

**优势：**
- 封装不同算法实现
- 易于添加新的编码支持
- 自动降级策略

---

### 4. 观察者模式

**应用场景：** Watchdog 文件监控

```python
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

class VideoFileHandler(FileSystemEventHandler):
    def __init__(self, callback):
        self.callback = callback
    
    def on_created(self, event):
        if self._is_video_file(event.src_path):
            self.callback(event)

observer = Observer()
observer.schedule(handler, path=watch_dir, recursive=False)
observer.start()
```

**优势：**
- 松耦合的事件通知
- 支持多个监听器
- 平台无关的实现

---

## 技术选型

### 为什么选择这些技术？

| 技术 | 选型原因 | 替代方案对比 |
|------|---------|-------------|
| **Python** | 开发效率高、生态丰富、跨平台 | Go（性能更好但开发慢）、Node.js（不适合 CPU 密集型） |
| **FastAPI** | 现代、高性能、自动文档、类型安全 | Flask（较老）、Django（太重） |
| **Watchdog** | 跨平台、事件驱动、低延迟 | 轮询（CPU 浪费）、inotify（仅 Linux） |
| **torf** | 纯 Python、轻量、功能完整 | qbittorrent-api（无法创建 torrent）、libtorrent（C++ 依赖） |
| **OKP** | 成熟的 BT 发布工具、多站点支持 | 手动上传（不可自动化）、其他 CLI 工具（不成熟） |
| **JSON** | 人类可读、易调试、无需数据库 | SQLite（过度）、CSV（不够结构化） |

### 关键决策记录

#### 决策 1：为什么使用 torf 而不是 qbittorrent-api？

**背景：** 需要生成 Torrent 文件

**选项：**
- `qbittorrent-api` - 只能操作 qBittorrent 客户端，无法创建 torrent
- `libtorrent` - C++ 库，Python 绑定复杂
- `torf` - 纯 Python 实现，专门用于创建 torrent

**结论：** 选择 `torf`，因为它：
- ✅ 可以创建 torrent 文件
- ✅ 纯 Python，无额外依赖
- ✅ API 简洁易用
- ✅ 支持多 Tracker

---

#### 决策 2：为什么选择 FastAPI 而不是 Flask？

**背景：** v2.1 需要 Web 面板

**选项：**
- `Flask` - 传统框架，需要手动编写文档
- `Django` - 全栈框架，过于重量级
- `FastAPI` - 现代 ASGI 框架，自动文档生成

**结论：** 选择 `FastAPI`，因为它：
- ✅ 自动生成 OpenAPI 文档（Swagger UI）
- ✅ 内置类型验证（Pydantic）
- ✅ 高性能（基于 Starlette + Pydantic）
- ✅ 原生支持异步
- ✅ 自动数据序列化

---

#### 决策 3：为什么使用 JSON 而不是 SQLite？

**背景：** 任务持久化存储

**选项：**
- `SQLite` - 关系型数据库，支持复杂查询
- `JSON` - 文本格式，人类可读
- `Pickle` - Python 序列化格式

**结论：** 选择 `JSON`，因为：
- ✅ 人类可读，易于调试
- ✅ 无需额外依赖
- ✅ 版本控制友好（Git 友好）
- ✅ 数据量小（通常 <1000 个任务）
- ❌ 不适合大规模数据（但当前场景足够）

**如果未来任务量增大，可以考虑迁移到 SQLite。**

---

## 并发模型

### 线程架构

```
主线程 (main.py)
  │
  ├─▶ Watchdog Observer (守护线程)
  │     └─ 监控文件夹事件
  │
  ├─▶ TaskWorker Thread (守护线程)
  │     └─ 主循环: dequeue → process → save
  │
  ├─▶ Retry Timer Threads (临时线程)
  │     └─ 延迟后重新入队 (不阻塞主循环)
  │
  └─▶ FastAPI/Uvicorn (主线程或独立线程)
        └─ HTTP 请求处理 + SSE 推送
```

### 线程安全机制

| 组件 | 保护方式 | 说明 |
|------|---------|------|
| TaskQueue | `threading.Queue` | 线程安全的 FIFO 队列 |
| TaskPersistence | `threading.Lock` | 读写互斥锁 |
| Log Buffer | `threading.Lock` | 日志追加保护 |
| SSE Clients | `list` + 异常捕获 | 客户端列表管理 |

### 性能指标

| 指标 | 典型值 | 说明 |
|------|--------|------|
| 文件检测延迟 | <1 秒 | Watchdog 事件触发 |
| 视频信息提取 | 1-3 秒 | PyMediaInfo 解析 |
| Torrent 生成 | 5-30 秒 | 取决于文件大小 |
| OKP 发布 | 30-120 秒 | 取决于网络速度 |
| 内存占用 | ~50 MB | 空闲状态 |
| CPU 占用 | <1% | 空闲状态 |

### 硬件建议

| 场景 | 最低配置 | 推荐配置 |
|------|---------|---------|
| 个人使用 | 2核 CPU + 4GB RAM | 4核 CPU + 8GB RAM |
| 小团队 | 4核 CPU + 8GB RAM | 8核 CPU + 16GB RAM |
| 大规模部署 | 8核 CPU + 16GB RAM | 16核 CPU + 32GB RAM |

> **提示：** SSD 可显著提升 Torrent 生成速度

---

## 扩展性设计

### 当前限制

- **单 Worker：** 任务串行处理，不支持并发
- **本地存储：** JSON 文件存储，不适合分布式
- **单进程：** 无法利用多核 CPU

### 未来扩展方向

#### 1. 多 Worker 并发

```python
# 未来可能的实现
workers = []
for i in range(num_workers):
    worker = TaskWorker(task_queue, name=f"Worker-{i}")
    workers.append(worker.start())
```

**挑战：**
- 共享资源竞争（文件 I/O、网络带宽）
- 任务优先级调度
- 全局速率限制

---

#### 2. 分布式队列

```python
# 未来可能的技术选型
# 方案 A: Redis + RQ (Redis Queue)
import rq
queue = rq.Queue(connection=Redis())

# 方案 B: Celery
from celery import Celery
app = Celery('tasks', broker='redis://localhost')

# 方案 D: Kafka (超大规模)
from kafka import KafkaProducer
producer = KafkaProducer(bootstrap_servers=['localhost:9092'])
```

**适用场景：**
- 多机器协同工作
- 高吞吐量任务处理
- 故障转移和高可用

---

#### 3. 数据库升级

```python
# 从 JSON 迁移到 SQLite
import sqlite3

class SQLiteDatabase:
    def __init__(self, db_path="data/tasks.db"):
        self.conn = sqlite3.connect(db_path)
        self._create_tables()
    
    def _create_tables(self):
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS tasks (
                id TEXT PRIMARY KEY,
                video_path TEXT NOT NULL,
                torrent_path TEXT,
                status TEXT NOT NULL,
                retry_count INTEGER DEFAULT 0,
                ...
            )
        """)
```

**优势：**
- 支持复杂查询（按状态、时间范围筛选）
- ACID 事务保证
- 更好的并发性能

---

## 总结

本系统的架构设计遵循以下原则：

1. **简单性优先** - 不过度设计，满足需求即可
2. **关注点分离** - 每个组件职责单一明确
3. **容错性** - 每个环节都有错误处理和恢复机制
4. **可观测性** - 丰富的日志和统计信息
5. **渐进式演进** - 保留扩展空间，但不提前优化

这种架构使得系统能够稳定运行 7×24 小时，同时保持代码的可维护性和可扩展性。

---

**文档版本：** v2.1  
**最后更新：** 2026-04-05  
**作者：** BT Auto Publishing Team
