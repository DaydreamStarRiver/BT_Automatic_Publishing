# BT 发布系统 - 统一数据模型与 API 使用指南 (v3.0)

## 📋 目录

1. [架构概览](#-架构概览)
2. [Task 数据结构](#-task-数据结构)
3. [状态机说明](#-状态机说明)
4. [REST API 接口](#-rest-api-接口)
5. [示例 JSON 数据](#-示例-json-数据)
6. [前端 UI 集成指南](#-前端-ui-集成指南)
7. [Worker 执行层对接](#-worker-执行层对接)

---

## 🏗️ 架构概览

### 三层统一架构

```
┌─────────────────────────────────────────────────────┐
│                   前端 UI 层                         │
│  (panel.html / Vue / React)                          │
│                                                     │
│  • 使用 Task Pydantic 模型                           │
│  • 调用 REST API                                     │
│  • 渲染表单、列表、日志                               │
└──────────────────────┬──────────────────────────────┘
                       │ HTTP (JSON)
                       ▼
┌─────────────────────────────────────────────────────┐
│                 后端 API 层 (api_v3.py)               │
│                                                     │
│  • FastAPI RESTful 接口                              │
│  • Task 模型验证                                      │
│  • 状态机控制                                        │
│  • 日志记录                                          │
└──────────────────────┬──────────────────────────────┘
                       │ Python 对象
                       ▼
┌─────────────────────────────────────────────────────┐
│               Worker 执行层 (task_worker.py)          │
│                                                     │
│  • 任务队列管理                                      │
│  • Torrent 构建                                     │
│  • OKP 调用                                         │
│  • 结果回写                                          │
└─────────────────────────────────────────────────────┘
```

### 核心设计原则

✅ **统一数据结构**: 前后端使用同一套 `Task` Pydantic 模型  
✅ **类型安全**: 所有字段都有明确的类型注解和验证  
✅ **状态机控制**: 严格的状态流转规则  
✅ **RESTful 设计**: 标准 HTTP 方法和语义化 URL  
✅ **完整文档**: 自动生成 Swagger/OpenAPI 文档  

---

## 📦 Task 数据结构

### 完整字段定义

```python
class Task(BaseModel):
    # 基础标识
    id: str                    # 唯一ID（12位MD5前缀大写）
    file_path: str             # 视频文件绝对路径
    torrent_path: Optional[str]  # Torrent文件路径

    # 发布信息（UI编辑区）
    publish_info: PublishInfo   # 标题/Tags/内容等

    # 媒体信息（解析得到）
    media_info: MediaInfo       # 分辨率/编码等

    # 元数据（自动提取）
    video_meta: VideoMeta      # ffprobe结果
    torrent_meta: TorrentMeta  # torf解析结果

    # 发布配置
    publish_config: PublishConfig  # 站点/选项

    # 状态信息
    status: TaskStatus         # 当前状态
    retry_count: int           # 已重试次数
    max_retries: int           # 最大重试次数
    error_message: Optional[str]  # 错误信息

    # 执行结果
    okp_result: Optional[OKPResult]  # OKP执行结果

    # 时间戳
    created_at: str            # 创建时间 (ISO 8601)
    updated_at: str            # 更新时间 (ISO 8601)
```

### 子模型详情

#### PublishInfo（发布信息）

```json
{
  "title": "[SweetSub] Oniichan wa Oshimai! - 01 [WebRip][1080p]",
  "subtitle": "Episode 01 - お兄ちゃんはおしまい！",
  "group_name": "SweetSub",
  "poster": "https://example.com/poster.jpg",
  "tags": "Anime, HD, Hi10P",
  "description": "## Release Info\n\n- Source: WebRip"
}
```

**字段说明：**
- `title`: 发布标题（必填）
- `subtitle`: 副标题/Episode信息（可选）
- `poster`: 海报URL（dmhy必需）
- `group_name`: 发布组名称
- `tags`: Tags字符串（逗号分隔），如 `"Anime, HD"`
- `description`: Markdown格式的内容

#### MediaInfo（媒体参数）

```json
{
  "resolution": "1080p",
  "video_codec": "H265",
  "audio_codec": "FLAC",
  "subtitle_type": "内嵌",
  "source": "WEB"
}
```

**注意**: 这些字段通常由 Normalizer 自动提取，用户无需手动填写。

#### PublishConfig（发布配置）

```json
{
  "sites": ["nyaa", "dmhy"],
  "auto_confirm": true,
  "dry_run": false,
  "mode": "publish"
}
```

**字段说明：**
- `sites`: 目标站点列表（至少1个）
- `auto_confirm`: 是否自动确认OKP弹窗
- `dry_run`: 是否试运行模式
- `mode`: 发布模式 (`preview`/`dry_run`/`publish`)

---

## ⚙️ 状态机说明

### 状态流转图

```
                    ┌─────────┐
                    │ PENDING │ ← 初始状态
                    └────┬────┘
                         │ Torrent生成完成
                         ↓
                    ┌────────┐
                    │  READY │ ← 可发布
                    └───┬────┘
                        │ 开始发布
                        ↓
                   ┌──────────┐
                   │UPLOADING │ ← 发布中
                   └────┬─────┘
            ┌─────────────┼─────────────┐
            ↓             ↓             ↓
       ┌────────┐  ┌────────┐  ┌─────────┐
       │SUCCESS │  │FAILED  │  │CANCELLED│
       └────────┘  └───┬────┘  └─────────┘
                        │ 重试
                        ↓
                   ┌──────────┐
                   │RETRYING  │
                   └────┬─────┘
              ┌───────────┼───────────┐
              ↓           ↓           ↓
        回到UPLOADING   FAILED     CANCELLED
```

### 状态转换规则

| 当前状态 | 可转换到 | 触发条件 |
|---------|---------|----------|
| PENDING | READY | Torrent生成完成 |
| PENDING | CANCELLED | 用户取消 |
| READY | UPLOADING | 开始发布 |
| READY | CANCELLED | 用户取消 |
| UPLOADING | SUCCESS | 发布成功 |
| UPLOADING | FAILED | 发布失败 |
| UPLOADING | CANCELLED | 用户中断 |
| FAILED | RETRYING | 用户触发重试 (< max_retries) |
| FAILED | CANCELLED | 用户放弃 |
| RETRYING | UPLOADING | 重新尝试 |
| RETRYING | FAILED | 重试仍失败 |
| RETRYING | CANCELLED | 用户取消重试 |

### 终态约束

- ✅ **SUCCESS**: 成功终态，不可变更
- ✅ **FAILED**: 失败终态（可重试或取消）
- ✅ **CANCELLED**: 取消终态，不可恢复

---

## 🌐 REST API 接口

### Base URL

```
http://localhost:8000/api
Content-Type: application/json
```

### 1. 获取任务列表

**请求：**
```http
GET /api/tasks?status=ready&limit=20&offset=0
```

**响应：**
```json
{
  "total": 42,
  "offset": 0,
  "limit": 20,
  "tasks": [
    {
      "id": "A1B2C3D4E5F6",
      "file_path": "D:/Videos/video.mp4",
      "status": "ready",
      "display_title": "[SweetSub] Oniichan...",
      "created_at": "2026-01-30T10:30:00"
    }
  ]
}
```

### 2. 获取单个任务

**请求：**
```http
GET /api/tasks/A1B2C3D4E5F6?full=true
```

**响应：**
```json
{
  "task": { /* 完整Task对象 */ },
  "message": null
}
```

### 3. 创建任务

**请求：**
```http
POST /api/tasks
Content-Type: application/json

{
  "file_path": "D:/Videos/new_video.mp4"
}
```

**响应：**
```json
{
  "success": true,
  "data": { /* 新创建的Task */ },
  "message": "任务创建成功: A1B2C3D4E5F6"
}
```

### 4. 更新任务（UI编辑）

**请求：**
```http
PUT /api/tasks/A1B2C3D4E5F6
Content-Type: application/json

{
  "publish_info": {
    "title": "[SweetSub] New Title",
    "tags": "Anime, HD",
    "description": "## Info\n\n- Test"
  },
  "publish_config": {
    "sites": ["nyaa", "dmhy"]
  }
}
```

**响应：**
```json
{
  "success": true,
  "message": "任务更新成功"
}
```

### 5. 发布任务（核心接口）⭐

**请求：**
```http
POST /api/tasks/A1B2C3D4E5F6/publish
Content-Type: application/json

{
  "mode": "publish",
  "sites": ["nyaa", "dmhy"],
  "auto_confirm": true
}
```

**行为流程：**
1. ✅ 验证状态必须是 `READY`
2. ✅ 验证 torrent_path 存在
3. ✅ 验证 sites 不为空
4. ✅ 状态转换: `READY → UPLOADING`
5. ✅ 加入 Worker 队列
6. ✅ 异步执行 OKP
7. ✅ 结果更新: `UPLOADING → SUCCESS/FAILED`

**响应（异步）：**
```json
{
  "success": true,
  "data": {
    "task_id": "A1B2C3D4E5F6",
    "status": "uploading",
    "mode": "publish",
    "sites": ["nyaa", "dmhy"]
  },
  "message": "正式发布任务已启动"
}
```

**支持的模式：**
- `preview`: 仅预览，不实际发布
- `dry_run`: 试运行，模拟但不提交
- `publish`: 正式发布

### 6. 获取任务日志

**请求：**
```http
GET /api/tasks/A1B2C3D4E5F6/logs?level=ERROR&limit=50
```

**响应：**
```json
{
  "task_id": "A1B2C3D4E5F6",
  "logs": [
    {
      "timestamp": "2026-01-30T11:00:00",
      "level": "INFO",
      "message": "开始发布",
      "source": "api_v3"
    }
  ],
  "total": 25
}
```

### 7. 重试任务

**请求：**
```http
POST /api/tasks/A1B2C3D4E5F6/retry
```

**条件：**
- 当前状态必须是 `FAILED`
- `retry_count < max_retries`（默认最多3次）

**响应：**
```json
{
  "success": true,
  "message": "重试已启动 (第2/3次)"
}
```

### 8. 取消任务

**请求：**
```http
POST /api/tasks/A1B2C3D4E5F6/cancel
```

**条件：**
- 必须是活跃状态（非终态）

**响应：**
```json
{
  "success": true,
  "message": "任务已取消"
}
```

### 9. 上传 Torrent 文件

**请求：**
```http
POST /api/tasks/A1B2C3D4E5F6/torrent
Content-Type: multipart/form-data

file: <torrent文件>
```

**行为：**
1. 保存文件到 output 目录
2. 解析 Torrent 元信息（torf）
3. 更新 `torrent_path` 和 `torrent_meta`
4. 如果是 PENDING 且有 torrent → READY

**响应：**
```json
{
  "success": true,
  "data": {
    "torrent_path": "D:/output/torrents/A1B2C3D4E5F6.torrent",
    "torrent_meta": { /* 解析结果 */ },
    "new_status": "ready"
  },
  "message": "Torrent 上传成功"
}
```

---

## 💡 示例 JSON 数据

### 完整 Task 示例

参见 `src/core/task_schema.py` 中的 `EXAMPLE_TASK_JSON` 常量。

### 发布成功响应示例

```json
{
  "success": true,
  "data": {
    "task_id": "A1B2C3D4E5F6",
    "status": "uploading",
    "started_at": "2026-01-30T11:00:00.000000",
    "sites": ["nyaa", "dmhy"],
    "mode": "publish"
  },
  "message": "发布任务已启动，正在调用OKP..."
}
```

### OKP 执行结果示例

```json
{
  "mode": "publish",
  "success": true,
  "returncode": 0,
  "stdout": "[OKP] Upload to nyaa.si successful!\n[OKP] Upload to dmhy.org successful!",
  "stderr": "",
  "error": null,
  "command": "OKP.Core.exe publish torrent.torrent",
  "executed_at": "2026-01-30T11:02:15.654321",
  "duration_ms": 135650,
  "site_results": [
    {
      "site": "nyaa",
      "success": true,
      "url": "https://nyaa.si/view/12345678",
      "error": null
    },
    {
      "site": "dmhy",
      "success": true,
      "url": "https://share.dmhy.org/topics/list/123456",
      "error": null
    }
  ]
}
```

---

## 🎨 前端 UI 集成指南

### JavaScript API 封装示例

```javascript
// ═══ API 基础配置 ═══
const API_BASE = '/api';

async function api(url, options = {}) {
  const response = await fetch(API_BASE + url, {
    headers: { 'Content-Type': 'application/json' },
    ...options
  });

  const data = await response.json();

  if (!response.ok || !data.success) {
    throw new Error(data.error || data.message || '请求失败');
  }

  return data;
}

// ═══ 任务操作 ═══

// 获取任务列表
async function loadTasks(status = null, limit = 200) {
  const params = new URLSearchParams({ limit });
  if (status) params.set('status', status);

  const data = await api(`/tasks?${params}`);
  return data.tasks;  // Array<Task>
}

// 获取单个任务
async function getTask(taskId, full = true) {
  const data = await api(`/tasks/${taskId}?full=${full}`);
  return data.task;  // Task
}

// 更新任务（保存表单）
async function saveTask(taskId, publishInfo, publishConfig) {
  const body = {
    publish_info: publishInfo,
    publish_config: publishConfig
  };

  return await api(`/tasks/${taskId}`, {
    method: 'PUT',
    body: JSON.stringify(body)
  });
}

// 发布任务
async function publishTask(taskId, mode = 'publish', sites = [], autoConfirm = true) {
  const body = {
    mode,
    sites,
    auto_confirm: autoConfirm
  };

  return await api(`/tasks/${taskId}/publish`, {
    method: 'POST',
    body: JSON.stringify(body)
  });
}

// 重试任务
async function retryTask(taskId) {
  return await api(`/tasks/${taskId}/retry`, {
    method: 'POST'
  });
}

// 取消任务
async function cancelTask(taskId) {
  return await api(`/tasks/${taskId}/cancel`, {
    method: 'POST'
  });
}

// 上传 Torrent
async function uploadTorrent(taskId, file) {
  const formData = new FormData();
  formData.append('file', file);

  const response = await fetch(`${API_BASE}/tasks/${taskId}/torrent`, {
    method: 'POST',
    body: formData
  });

  return await response.json();
}

// ═══ 使用示例 ═══

async function example() {
  try {
    // 1. 加载任务列表
    const tasks = await loadTasks('pending');
    console.log(`找到 ${tasks.length} 个待处理任务`);

    // 2. 选择第一个任务
    const task = tasks[0];
    const taskDetail = await getTask(task.id);
    console.log('任务详情:', taskDetail);

    // 3. 编辑并保存
    await saveTask(task.id, {
      title: '[MyGroup] My Title - 01 [1080p]',
      tags: 'Anime, HD',
      description: '## Release\n\n- Test'
    }, {
      sites: ['nyaa', 'dmhy'],
      auto_confirm: true
    });

    // 4. 发布
    const result = await publishTask(task.id, 'publish', ['nyaa']);
    console.log('发布启动:', result);

  } catch (error) {
    console.error('操作失败:', error.message);
  }
}
```

### 表单绑定示例

```javascript
// 从 Task 对象填充表单
function fillFormFromTask(task) {
  const pi = task.publish_info;

  document.getElementById('title').value = pi.title || '';
  document.getElementById('subtitle').value = pi.subtitle || '';
  document.getElementById('group').value = pi.group_name || '';
  document.getElementById('poster').value = pi.poster || '';
  document.getElementById('tags').value = pi.tags || '';
  document.getElementById('description').value = pi.description || '';

  // 站点选择
  const pc = task.publish_config;
  pc.sites.forEach(site => {
    const checkbox = document.querySelector(`input[name="sites"][value="${site}"]`);
    if (checkbox) checkbox.checked = true;
  });
}

// 从表单收集数据
function collectFormData() {
  return {
    publish_info: {
      title: document.getElementById('title').value.trim(),
      subtitle: document.getElementById('subtitle').value.trim(),
      group_name: document.getElementById('group').value.trim(),
      poster: document.getElementById('poster').value.trim(),
      tags: document.getElementById('tags').value.trim(),
      description: document.getElementById('description').value
    },
    publish_config: {
      sites: getSelectedSites(),  // 自定义函数
      auto_confirm: document.getElementById('autoConfirm').checked
    }
  };
}
```

### 状态轮询示例

```javascript
// 轮询任务状态（用于监控发布进度）
function pollTaskStatus(taskId, intervalMs = 2500) {
  let pollCount = 0;
  const maxPolls = 120;  // 最多轮询5分钟

  const timer = setInterval(async () => {
    pollCount++;
    if (pollCount > maxPolls) {
      clearInterval(timer);
      showToast('超时，请手动检查', 'warning');
      return;
    }

    try {
      const task = await getTask(taskId);

      updateStatusDisplay(task);  // 更新UI显示

      // 终态检测
      if (['success', 'failed', 'cancelled'].includes(task.status)) {
        clearInterval(timer);
        handleFinalStatus(task);  // 处理最终状态
      }

    } catch (error) {
      console.error('轮询失败:', error);
    }

  }, intervalMs);

  return timer;  // 返回定时器ID以便取消
}
```

---

## 🔧 Worker 执行层对接

### Worker 如何使用 Task 模型

```python
# src/core/task_worker.py (示例)

from src.core.task_schema import Task, TaskStatus, OKPResult

class TaskWorker:
    def _process_task(self, task: Task):
        """处理单个任务"""

        # 1. 状态转换
        task.transition_to(TaskStatus.UPLOADING)
        self._save_task(task)

        try:
            # 2. 调用 OKP
            result = self._execute_okp(task)

            # 3. 更新结果
            task.okp_result = OKPResult(**result)

            # 4. 状态转换
            if result['success']:
                task.transition_to(TaskStatus.SUCCESS)
            else:
                task.transition_to(
                    TaskStatus.FAILED,
                    error_message=result.get('error')
                )

        except Exception as e:
            task.transition_to(TaskStatus.FAILED, str(e))

        finally:
            self._save_task(task)
```

### 数据流完整路径

```
用户操作 (UI)
    ↓
HTTP POST /api/tasks/{id}/publish
    ↓
FastAPI (api_v3.py)
    ├─ 验证 Task 模型
    ├─ 状态转换: READY → UPLOADING
    ├─ 持久化到 JSON
    └─ 异步执行 _do_publish()
        ↓
    asyncio.create_task()
        ↓
OKPExecutor.run_okp_upload()
    ├─ 调用 OKP.Core.exe
    ├─ 解析输出
    └─ 返回结果字典
        ↓
更新 Task.okp_result
状态转换: UPLOADING → SUCCESS/FAILED
持久化更新
    ↓
前端轮询 GET /api/tasks/{id}
    ↓
渲染最新状态
```

---

## 📚 参考资源

- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc
- **数据模型定义**: `src/core/task_schema.py`
- **API 实现**: `src/web/api_v3.py`
- **旧版兼容**: `src/web/api.py` (v2.x)
- **Task 模型（旧版）**: `src/core/task_model.py`

---

## ✅ 检查清单

使用本规范时，请确认：

- [ ] 前端使用统一的 Task 字段名
- [ ] API 调用遵循 RESTful 规范
- [ ] 状态转换通过 API 触发（不直接修改）
- [ ] 错误处理覆盖所有异常情况
- [ ] 日志记录关键操作
- [ ] 时间戳使用 ISO 8601 格式
- [ ] Tags 使用逗号分隔的字符串格式

---

**版本**: v3.0.0 Standard  
**最后更新**: 2026-01-30  
**维护者**: BT Auto Publishing System Team
