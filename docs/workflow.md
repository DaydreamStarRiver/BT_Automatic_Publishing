# 🔄 任务流程文档

> BT 自动发布系统 v2.1 - 任务生命周期、状态机、重试与恢复机制

---

## 目录

- [任务生命周期](#任务生命周期)
- [状态机设计](#状态机设计)
- [重试机制](#重试机制)
- [断点恢复](#断点恢复)
- [各阶段详细说明](#各阶段详细说明)
- [日志示例](#日志示例)

---

## 任务生命周期

### 完整流程图

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
    │   │     ├─ MD5 去重检查 (Scanner)            │
    │   │     ├─ 标准化任务 (Normalizer)           │
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

### 流程阶段说明

| 阶段 | 状态 | 操作 | 输出 |
|------|------|------|------|
| **1. 文件发现** | NEW → TORRENT_CREATING | Watcher 检测新文件 | Task 对象入队 |
| **2. 信息提取** | TORRENT_CREATING | Probe + Scanner + Normalizer | video_meta, publish_info |
| **3. Torrent 生成** | TORRENT_CREATING → TORRENT_CREATED | TorrentBuilder | .torrent 文件 |
| **4. OKP 发布** | TORRENT_CREATED → UPLOADING/SUCCESS/FAILED | OKPExecutor | 发布结果 |
| **5. 失败处理** | FAILED → 重试或 PERMANENT_FAILED | 自动或手动 | 更新状态 |

---

## 状态机设计

### 状态枚举定义

```python
from enum import Enum

class TaskStatus(Enum):
    """任务状态枚举"""
    
    # 初始状态
    NEW = "new"                              # 新任务，待处理
    
    # Torrent 生成阶段
    TORRENT_CREATING = "torrent_creating"    # 正在生成 Torrent
    TORRENT_CREATED = "torrent_created"      # Torrent 已生成
    
    # OKP 发布阶段
    UPLOADING = "uploading"                  # 正在调用 OKP
    
    # 终止状态
    SUCCESS = "success"                      # ✅ 成功完成
    FAILED = "failed"                        # ⚠️ 失败（可重试）
    PERMANENT_FAILED = "permanent_failed"    # ❌ 永久失败（不可重试）
```

### 状态分类

```python
# 终止状态（不可再变化）
TERMINAL_STATUSES = {TaskStatus.SUCCESS, TaskStatus.PERMANENT_FAILED}

# 活跃状态（正在处理）
ACTIVE_STATUSES = {
    TaskStatus.NEW,
    TaskStatus.TORRENT_CREATING,
    TaskStatus.TORRENT_CREATED,
    TaskStatus.UPLOADING,
}

# 可重试状态
RETRYABLE_STATUS = TaskStatus.FAILED
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

### 状态转换规则表

| 当前状态 | 触发条件 | 目标状态 | 说明 |
|---------|---------|---------|------|
| `NEW` | Worker 取出任务 | `TORRENT_CREATING` | 开始处理 |
| `NEW` | 文件不存在 / 权限错误 | `PERMANENT_FAILED` | 致命错误，无法恢复 |
| `TORRENT_CREATING` | Torrent 生成成功 | `TORRENT_CREATED` | 准备上传 |
| `TORRENT_CREATING` | 视频信息提取失败 | `PERMANENT_FAILED` | 致命错误 |
| `TORRENT_CREATING` | Torrent 生成失败 | `PERMANENT_FAILED` | 致命错误 |
| `TORRENT_CREATED` | 开始调用 OKP | `UPLOADING` | 上传中 |
| `UPLOADING` | OKP 返回成功 | `SUCCESS` | 完成 ✅ |
| `UPLOADING` | OKP 返回失败 | `FAILED` | 可重试 |
| `UPLOADING` | 超时 / 异常 | `PERMANENT_FAILED` | 严重错误 |
| `FAILED` | `retry_count < max_retries` | `FAILED`（延迟后重新入队） | 等待重试 |
| `FAILED` | `retry_count >= max_retries` | `PERMANENT_FAILED` | 超过最大次数 ❌ |

### 状态验证代码

```python
class Task:
    def update_status(self, new_status: TaskStatus, error: str = None):
        """
        更新任务状态（带验证）
        
        Args:
            new_status: 目标状态
            error: 错误信息（可选）
            
        Raises:
            ValueError: 如果状态转换不合法
        """
        # 定义合法的状态转换
        allowed_transitions = {
            TaskStatus.NEW: [
                TaskStatus.TORRENT_CREATING,
                TaskStatus.PERMANENT_FAILED,  # 文件不存在等致命错误
            ],
            TaskStatus.TORRENT_CREATING: [
                TaskStatus.TORRENT_CREATED,
                TaskStatus.PERMANENT_FAILED,  # 提取失败/生成失败
            ],
            TaskStatus.TORRENT_CREATED: [
                TaskStatus.UPLOADING,
            ],
            TaskStatus.UPLOADING: [
                TaskStatus.SUCCESS,
                TaskStatus.FAILED,
                TaskStatus.PERMANENT_FAILED,  # 超时/异常
            ],
            TaskStatus.FAILED: [
                # FAILED 状态本身不变，而是通过 requeue_for_retry() 重新入队
            ],
            # 终止状态不允许再转换
            TaskStatus.SUCCESS: [],
            TaskStatus.PERMANENT_FAILED: [],
        }
        
        # 验证转换合法性
        if new_status not in allowed_transitions.get(self.status, []):
            raise ValueError(
                f"Illegal state transition: {self.status.value} -> {new_status.value}"
            )
        
        # 执行状态更新
        self.status = new_status
        self.error_message = error
        self.updated_at = datetime.now().isoformat()
        
        # 记录日志
        logger.info(f"[{self.id}] Status: {self.status.value} -> {new_status.value}")
        
        # 立即持久化
        self.persistence.save_task(self)
    
    def can_retry(self) -> bool:
        """检查是否可以重试"""
        return (
            self.status == TaskStatus.FAILED and 
            self.retry_count < self.max_retries
        )
    
    def is_terminal(self) -> bool:
        """是否为终止状态"""
        return self.status in TERMINAL_STATUSES
    
    def is_active(self) -> bool:
        """是否为活跃状态（正在处理）"""
        return self.status in ACTIVE_STATUSES
```

---

## 重试机制

### 重试规则

| 属性 | 值 | 说明 |
|------|-----|------|
| 最大重试次数 | **3 次** | 可在代码中修改 `Task.max_retries` |
| 重试对象 | **仅 OKP 上传失败** | Torrent 生成失败直接终止 |
| 延迟策略 | **指数退避** | 10s → 20s → 30s |
| 最大延迟 | **30 秒** | 防止无限等待 |

### 延迟计算公式

```python
def calculate_retry_delay(retry_count: int, max_delay: int = 30) -> int:
    """
    计算重试延迟时间（指数退避）
    
    Args:
        retry_count: 当前重试次数（从 0 开始）
        max_delay: 最大延迟时间（秒）
    
    Returns:
        延迟秒数
    
    Examples:
        >>> calculate_retry_delay(0)   # 第1次失败
        10
        >>> calculate_retry_delay(1)   # 第2次失败
        20
        >>> calculate_retry_delay(2)   # 第3次失败
        30
        >>> calculate_retry_delay(3)   # 第4次失败 -> 超过最大次数
        None  # 不再重试
    """
    if retry_count >= max_retries:
        return None  # 超过最大次数，不再重试
    
    delay = min(10 * (retry_count + 1), max_delay)
    return delay


# 使用示例
delay = calculate_retry_delay(task.retry_count)

if delay is not None:
    # 启动延迟线程（不阻塞主队列）
    threading.Thread(
        target=_delayed_retry,
        args=(task, delay),
        daemon=True
    ).start()
else:
    # 标记为永久失败
    task.update_status(TaskStatus.PERMANENT_FAILED, "超过最大重试次数")
```

### 重试流程图

```
OKP 上传失败
     │
     ▼
retry_count += 1
     │
     ▼
retry_count < max_retries? (retry_count < 3?)
     │
   ┌─┴─┐
   │Yes│  ─────────────────────────┐
   └───┘                           │
     │                              ▼
     │                        计算延迟时间
     │                        delay = min(10 * (retry+1), 30)
     │                              │
     │                              ▼
     │                        启动延迟线程
     │                       (不阻塞主队列)
     │                              │
     │                         sleep(delay)
     │                              │
     │                              ▼
     │                        重新放入队列
     │                         status 保持 FAILED
     │                              │
     └──────────────────────────────┘
     
   ┌─┴─┐
   │No │
   └───┘
     │
     ▼
标记为 PERMANENT_FAILED
     │
     ▼
记录错误信息到 tasks.json
```

### 延迟重试实现

```python
import threading
import time

class TaskQueue:
    def requeue_for_retry(self, task: Task, delay_seconds: int = 20):
        """
        延迟重试入队
        
        在独立线程中等待指定时间后将任务重新放回队列，
        不阻塞主 Worker 循环。
        
        Args:
            task: 要重试的任务
            delay_seconds: 延迟秒数
        """
        def _delayed_enqueue():
            time.sleep(delay_seconds)
            
            # 重新入队
            self._queue.put(task)
            
            logger.info(
                f"[{task.id}] Retry #{task.retry_count + 1}: "
                f"Re-enqueued after {delay_seconds}s delay"
            )
        
        # 启动守护线程（程序退出时自动终止）
        retry_thread = threading.Thread(
            target=_delayed_enqueue,
            daemon=True
        )
        retry_thread.start()
        
        logger.info(
            f"[{task.id}] Will retry in {delay_seconds}s "
            f"(attempt {task.retry_count + 1}/{task.max_retries})"
        )
```

### 为什么只重试 OKP 失败？

**设计决策：**

| 失败类型 | 是否重试 | 原因 |
|---------|---------|------|
| OKP 登录失败 | ✅ 重试 | 可能是临时网络问题 |
| OKP 发布超时 | ✅ 重试 | 网络波动导致 |
| OKP 返回错误 | ✅ 重试 | 可能是站点临时故障 |
| 视频文件不存在 | ❌ 不重试 | 文件不会凭空出现 |
| 视频信息提取失败 | ❌ 不重试 | 文件损坏，无法修复 |
| Torrent 生成失败 | ❌ 不重试 | 磁盘空间不足等系统问题 |
| MD5 重复检测 | ❌ 不重试 | 文件已处理，无需重复 |

**这种设计的优势：**
- 避免无意义的重试浪费资源
- 快速识别并报告真正的问题
- 让用户及时介入处理永久性错误

---

## 断点恢复

### 工作原理

程序每次状态变化都会**立即写入** `data/tasks.json`：

```json
{
  "A1B2C3D4E5F6": {
    "id": "A1B2C3D4E5F6",
    "video_path": "D:/videos/test.mp4",
    "torrent_path": "data/torrents/test.torrent",
    "status": "failed",
    "retry_count": 1,
    "max_retries": 3,
    "error_message": "OKP 登录失败: Cookie 过期",
    "created_at": "2026-01-15T10:30:00",
    "updated_at": "2026-01-15T10:35:00"
  }
}
```

### 启动时恢复逻辑

```python
class TaskQueue:
    def _recover_pending_tasks(self):
        """
        启动时恢复未完成任务
        
        从 tasks.json 加载所有任务，
        根据状态决定恢复策略：
        - FAILED 且可重试 → 直接重新入队
        - 中断的任务 → 标记为 FAILED 后重试
        - SUCCESS / PERMANENT_FAILED → 跳过
        """
        pending_tasks = self.persistence.get_pending_tasks()
        
        recovered_count = 0
        
        for task in pending_tasks:
            if task.status == TaskStatus.FAILED and task.can_retry():
                # 情况1: 失败任务 → 准备重试
                logger.info(
                    f"[{task.id}] Recovering failed task - "
                    f"Retry {task.retry_count + 1}/{task.max_retries}"
                )
                self._queue.put(task)
                recovered_count += 1
                
            elif task.status in [
                TaskStatus.NEW,
                TaskStatus.TORRENT_CREATING,
                TaskStatus.TORRENT_CREATED,
                TaskStatus.UPLOADING,
            ]:
                # 情况2: 中断的任务 → 标记为失败后重试
                logger.warning(
                    f"[{task.id}] Interrupted task found - "
                    f"Marking as FAILED and requeuing"
                )
                task.update_status(
                    TaskStatus.FAILED,
                    "Program interrupted, requeuing"
                )
                self._queue.put(task)
                recovered_count += 1
            
            elif task.status in [TaskStatus.SUCCESS, TaskStatus.PERMANENT_FAILED]:
                # 情况3: 已完成 → 跳过
                logger.debug(f"[{task.id}] Skipping terminal status: {task.status.value}")
        
        logger.info(f"Recovered {recovered_count} pending tasks")
        
        return recovered_count
```

### 恢复场景矩阵

| 场景 | 当前状态 | 恢复行为 | 说明 |
|------|---------|---------|------|
| 正在生成 Torrent | `TORRENT_CREATING` | 标记为 `FAILED`，从头开始 | Torrent 可能不完整 |
| 正在上传 OKP | `UPLOADING` | 标记为 `FAILED`，从上传阶段重试 | OKP 可能已部分发布 |
| 已失败且可重试 | `FAILED` + `retry_count < 3` | 直接重新入队 | 继续未完成的尝试 |
| 已失败且不可重试 | `FAILED` + `retry_count >= 3` | 跳过 | 需手动干预 |
| 已成功 | `SUCCESS` | 跳过 | 不重复处理 |
| 永久失败 | `PERMANENT_FAILED` | 跳过 | 需手动解决根本原因 |

### 手动干预方法

如果想重试永久失败的任务：

#### 方法 1：编辑 JSON 文件

1. 打开 `data/tasks.json`
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
5. 重启程序（或等待下次启动）

#### 方法 2：使用 Web 面板（v2.1）

1. 打开 `http://localhost:8080`
2. 在任务列表找到目标任务
3. 点击「重试」按钮
4. 系统会自动将 `retry_count` 重置并重新入队

#### 方法 3：使用 REST API（v2.1）

```bash
curl -X POST http://localhost:8080/api/tasks/A1B2C3D4E5F6/retry
```

### 断点恢复的可靠性保证

| 保证措施 | 实现 |
|---------|------|
| **实时写入** | 每次 `update_status()` 都立即调用 `save_task()` |
| **原子操作** | 写入前加锁，避免并发问题 |
| **完整数据** | 保存所有字段，包括中间状态 |
| **容错格式** | JSON 格式，即使损坏也可手动修复 |
| **备份建议** | 定期备份 `data/tasks.json` 到云存储 |

---

## 各阶段详细说明

### 阶段 1：文件发现（Watcher）

**触发条件：** 新视频文件出现在监控目录

**执行步骤：**

```python
# watcher.py - VideoFileHandler.on_created()

def on_created(self, event):
    """
    Watchdog 回调：检测到新文件
    
    1. 验证扩展名
    2. 等待文件写入完成
    3. 创建 Task 对象
    4. 放入队列
    """
    # Step 1: 验证文件类型
    if not self._is_video_file(event.src_path):
        return  # 忽略非视频文件
    
    # Step 2: 短暂等待（确保文件完全写入）
    time.sleep(1)
    
    # Step 3: 生成唯一 ID（基于路径的 MD5 前12位）
    task_id = Task.generate_id(event.src_path)
    
    # Step 4: 创建 Task 对象
    task = Task(
        id=task_id,
        video_path=event.src_path,
        status=TaskStatus.NEW,
    )
    
    # Step 5: 放入队列（带去重检查）
    success = self.task_queue.enqueue(task)
    
    if success:
        logger.info(f"📋 Task [{task_id}] created - {Path(event.src_path).name}")
    else:
        logger.warning(f"⚠️ Duplicate file skipped - {event.src_path}")
```

**关键特性：**
- ⚡ **非阻塞：** 立即返回，不等待处理完成
- 🔍 **去重：** 基于 MD5 避免重复处理
- 🛡️ **安全：** 等待 1 秒确保文件写入完成

---

### 阶段 2：Torrent 生成（Worker - _handle_new_task）

**触发条件：** Worker 从队列取出 `status=NEW` 的任务

**执行步骤：**

```python
# task_worker.py - TaskWorker._handle_new_task()

def _handle_new_task(self, task: Task):
    """
    处理新任务：提取信息 + 生成 Torrent
    
    Steps:
    1. 更新状态为 TORRENT_CREATING
    2. 检查文件是否存在
    3. 提取视频元数据
    4. MD5 去重检查
    5. 标准化发布信息
    6. 生成 Torrent 文件
    7. 更新状态为 TORRENT_CREATED
    """
    try:
        # Step 1: 状态转换
        task.update_status(TaskStatus.TORRENT_CREATING)
        
        # Step 2: 文件存在性检查
        if not Path(task.video_path).exists():
            raise FileNotFoundError(f"Video file not found: {task.video_path}")
        
        # Step 3: 提取视频信息
        logger.info(f"[{task.id}] Extracting video metadata...")
        video_meta = self.probe.get_video_info(task.video_path)
        task.video_meta = VideoMeta(**video_meta)
        
        # Step 4: MD5 去重检查
        md5_hash = video_meta['md5']
        if self.scanner.is_processed(md5_hash):
            raise Exception("File already processed (MD5 duplicate)")
        
        # Step 5: 标准化发布信息
        publish_info = self.normalizer.normalize(video_meta)
        task.publish_info = PublishInfo(**publish_info)
        
        # Step 6: 生成 Torrent
        logger.info(f"[{task.id}] Generating torrent...")
        torrent_path = TorrentBuilder.create_torrent(
            file_path=task.video_path,
            tracker_urls=self.config.tracker_urls,
            output_dir=self.config.output_torrent_dir,
        )
        task.torrent_path = torrent_path
        
        # Step 7: 标记为已处理
        self.scanner.mark_as_processed(md5_hash, task.video_path)
        
        # Step 8: 状态转换
        task.update_status(TaskStatus.TORRENT_CREATED)
        
        logger.info(f"[{task.id}] ✅ Torrent generated: {Path(torrent_path).name}")
        
    except Exception as e:
        logger.error(f"[{task.id}] ❌ Error in _handle_new_task: {e}")
        task.update_status(TaskStatus.PERMANENT_FAILED, str(e))
```

**输出产物：**
- `task.video_meta` - 视频分辨率、编码、时长、大小、MD5
- `task.publish_info` - 标题、标签、简介等发布信息
- `task.torrent_path` - 生成的 .torrent 文件路径

---

### 阶段 3：OKP 发布（Worker - _handle_upload）

**触发条件：** Worker 从队列取出 `status=TORRENT_CREATED` 的任务

**执行步骤：**

```python
# task_worker.py - TaskWorker._handle_upload()

def _handle_upload(self, task: Task):
    """
    执行 OKP 发布
    
    Steps:
    1. 更新状态为 UPLOADING
    2. 解析 Torrent 信息（用于日志）
    3. 构建 OKP 命令行参数
    4. 调用 subprocess 执行 OKP
    5. 解码输出（多编码检测）
    6. 判断结果并更新状态
    """
    try:
        # Step 1: 状态转换
        task.update_status(TaskStatus.UPLOADING)
        
        # Step 2: 解析 Torrent 信息（用于预览日志）
        torrent_info = OKPExecutor._parse_torrent_info(task.torrent_path)
        self._log_torrent_preview(task, torrent_info)
        
        # Step 3: 构建 OKP 参数
        okp_params = {
            'torrent_path': task.torrent_path,
            'auto_confirm': self.auto_confirm,
            'preview_only': self.preview_only,
            'timeout': self.okp_timeout,
        }
        
        # Step 4: 执行 OKP
        logger.info(f"[{task.id}] 🚀 Calling OKP (mode={'preview' if self.preview_only else 'publish'})")
        result = OKPExecutor.run_okp_upload(**okp_params)
        
        # Step 5: 记录结果
        task.okp_result = OKPResult(**result)
        
        # Step 6: 判断结果
        if result.get('success', False):
            task.update_status(TaskStatus.SUCCESS)
            logger.info(f"[{task.id}] ✅ Task completed successfully")
        else:
            error_msg = result.get('error', 'Unknown error')
            task.update_status(TaskStatus.FAILED, error_msg)
            
            # 检查是否需要重试
            if task.can_retry():
                delay = calculate_retry_delay(task.retry_count)
                logger.warning(
                    f"[{task.id}] ⚠️ Task failed - "
                    f"Retry {task.retry_count + 1}/{task.max_retries} in {delay}s"
                )
                self.task_queue.requeue_for_retry(task, delay)
            else:
                task.update_status(TaskStatus.PERMANENT_FAILED, "Max retries exceeded")
                logger.error(f"[{task.id}] ❌ Max retries reached - Marking as PERMANENT_FAILED")
                
    except Exception as e:
        logger.error(f"[{task.id}] ❌ Exception in _handle_upload: {e}", exc_info=True)
        task.update_status(TaskStatus.PERMANENT_FAILED, str(e))
```

**三种运行模式对比：**

| 模式 | 配置 | 效果 | 适用场景 |
|------|------|------|---------|
| **预览模式** | `okp_preview_only: true` | 仅展示 Torrent 信息，不实际发布 | 测试配置 |
| **交互模式** | `okp_auto_confirm: false` | 手动确认每个步骤 | 调试问题 |
| **自动模式** ⭐ | `okp_auto_confirm: true` | 全自动执行，无人值守 | 生产环境 |

---

## 日志示例

### 场景 1：正常发布流程

```
╔══════════════════════════════════════════════╗
║  🎬 BT 自动发布系统 v2.0                    ║
╚══════════════════════════════════════════════╝

============================================================
👁️  文件监控启动
   监控目录: ./data/watch
   支持格式: .mkv, .mp4, .avi
============================================================

============================================================
🚀 Worker 启动 - 开始处理任务队列
============================================================

🔍 检测到新视频文件: D:\data\watch\新番第01集.mp4
📋 创建任务 [A1B2C3D4E5F6] - 文件: 新番第01集.mp4
✅ 任务 [A1B2C3D4E5F6] 已加入队列，等待 Worker 处理

╔══════════════════════════════════════════════╗
║  [A1B2C3D4E5F6] 🎬 开始处理任务                ║
╚══════════════════════════════════════════════╝
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
```

---

### 场景 2：失败自动重试

```
╔══════════════════════════════════════════════╗
║  [B2C3D4E5F6A7] 🎬 开始处理任务               ║
╚══════════════════════════════════════════════╝
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
  ⚠️ 失败（可重试）: 1
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
  ⚠️ 失败（可重试）: 1
  ❌ 永久失败: 0
  ----------------------------------------
  📋 总计: 13 个任务

👋 系统已停止
```

---

## 总结

本系统的任务流程设计遵循以下原则：

1. **状态驱动** - 每个阶段都有明确的状态定义
2. **可追溯** - 完整的日志记录和状态历史
3. **容错性强** - 多层次的错误处理和恢复机制
4. **自动化高** - 最小化人工干预
5. **可观测性** - 丰富的统计信息和实时反馈

这套流程保证了系统能够稳定运行 7×24 小时，同时提供足够的灵活性来应对各种异常情况。

---

**文档版本：** v2.1  
**最后更新：** 2026-04-05  
**作者：** BT Auto Publishing Team
