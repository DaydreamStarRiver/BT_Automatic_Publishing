# 🔌 REST API 接口文档

> BT 自动发布系统 v2.1 - Web 面板 & RESTful API 完整说明

---

## 目录

- [API 概览](#api-概览)
- [基础信息](#基础信息)
- [系统状态接口](#系统状态接口)
- [任务管理接口](#任务管理接口)
- [任务操作接口](#任务操作接口)
- [手动触发接口](#手动触发接口)
- [日志接口](#日志接口)
- [配置接口](#配置接口)
- [模板系统接口](#模板系统接口)
- [SSE 实时日志](#sse-实时日志)
- [错误处理](#错误处理)
- [前端集成示例](#前端集成示例)

---

## API 概览

### 访问地址

```
http://localhost:8080
```

### Swagger 文档

启动服务后访问：

- **Swagger UI:** `http://localhost:8080/docs`
- **ReDoc:** `http://localhost:8080/redoc`

自动生成的交互式 API 文档，支持在线测试。

---

## 基础信息

### Base URL

```
http://localhost:8080/api
```

### 认证方式

当前版本 **无需认证**（本地使用）。

> ⚠️ **安全提示：** 如果部署到公网，请添加认证中间件。

### 数据格式

- **请求格式:** JSON
- **响应格式:** JSON
- **字符编码:** UTF-8

### HTTP 状态码

| 状态码 | 说明 |
|--------|------|
| 200 | 成功 |
| 201 | 创建成功 |
| 400 | 请求参数错误 |
| 404 | 资源不存在 |
| 500 | 服务器内部错误 |
| 503 | 系统未就绪（队列未初始化） |

---

## 系统状态接口

### GET /api/status

获取系统整体状态和统计信息。

**请求：**

```http
GET /api/status
```

**响应：**

```json
{
  "ok": true,
  "queue_size": 3,
  "worker_running": true,
  "watch_dir": "D:/BT_Automatic_Publishing/data/watch",
  "stats": {
    "total": 15,
    "success": 10,
    "failed": 2,
    "permanent_failed": 1,
    "pending": 2
  },
  "uptime_ts": "2026-01-15T12:30:00",
  "okp_configured": true,
  "auto_confirm": true,
  "preview_mode": false
}
```

**字段说明：**

| 字段 | 类型 | 说明 |
|------|------|------|
| `queue_size` | int | 当前队列中的任务数 |
| `worker_running` | bool | Worker 是否正在运行 |
| `watch_dir` | string | 监控目录路径 |
| `stats.total` | int | 总任务数 |
| `stats.success` | int | 成功任务数 |
| `stats.failed` | int | 失败任务数（可重试）|
| `stats.permanent_failed` | int | 永久失败任务数 |
| `stats.pending` | int | 待处理任务数 |
| `uptime_ts` | string | 启动时间 (ISO 格式) |
| `okp_configured` | bool | OKP 是否已配置 |
| `auto_confirm` | bool | 是否自动确认模式 |
| `preview_mode` | bool | 是否预览模式 |

---

### GET /api/config

获取当前配置（敏感信息已脱敏）。

**请求：**

```http
GET /api/config
```

**响应：**

```json
{
  "watch_dir": "./data/watch",
  "output_torrent_dir": "./data/torrents",
  "log_dir": "./logs",
  "okp_auto_confirm": true,
  "okp_preview_only": false,
  "okp_timeout": 300,
  "web_enabled": true,
  "web_port": 8080,
  "video_extensions": [".mkv", ".mp4", ".avi"]
}
```

---

## 任务管理接口

### GET /api/tasks

获取任务列表（支持分页和过滤）。

**请求：**

```http
GET /api/tasks?status=failed&limit=20&offset=0
```

**查询参数：**

| 参数 | 类型 | 必填 | 默认值 | 说明 |
|------|------|------|--------|------|
| `status` | string | 否 | null | 过滤状态：`new`, `torrent_creating`, `torrent_created`, `uploading`, `success`, `failed`, `permanent_failed` |
| `limit` | int | 否 | 200 | 返回数量限制 |
| `offset` | int | 否 | 0 | 分页偏移量 |

**响应：**

```json
{
  "total": 15,
  "offset": 0,
  "limit": 20,
  "tasks": [
    {
      "id": "A1B2C3D4E5F6",
      "video_path": "D:/videos/test.mp4",
      "video_name": "test.mp4",
      "torrent_path": "data/torrents/test.torrent",
      "status": "success",
      "retry_count": 0,
      "max_retries": 3,
      "error_message": null,
      "created_at": "2026-01-15T10:30:00",
      "updated_at": "2026-01-15T10:35:00"
    }
  ]
}
```

---

### GET /api/tasks/{task_id}

获取单个任务详情（完整信息）。

**请求：**

```http
GET /api/tasks/A1B2C3D4E5F6?full=true
```

**路径参数：**

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `task_id` | string | ✅ | 任务 ID（不区分大小写）|

**查询参数：**

| 参数 | 类型 | 必填 | 默认值 | 说明 |
|------|------|------|--------|------|
| `full` | bool | 否 | true | `true`=返回完整信息，`false`=仅基本信息 |

**响应（full=true）：**

```json
{
  "id": "A1B2C3D4E5F6",
  "video_path": "D:/videos/test.mp4",
  "video_name": "test.mp4",
  "torrent_path": "data/torrents/test.torrent",
  "status": "success",
  "retry_count": 0,
  "max_retries": 3,
  "error_message": null,
  "created_at": "2026-01-15T10:30:00",
  "updated_at": "2026-01-15T10:35:00",
  
  "publish_info": {
    "title": "[动漫组] 测试视频 [1080p]",
    "subtitle": "",
    "tags": "anime,1080p",
    "description": "测试视频简介...",
    "about": "",
    "poster": "",
    "group_name": "动漫组",
    "category": "Anime",
    "source": "WEB-DL",
    "video_codec": "H265",
    "audio_codec": "AAC",
    "subtitle_type": "内嵌"
  },
  
  "video_meta": {
    "resolution": "1920x1080",
    "codec": "H265",
    "duration_seconds": 1440.5,
    "file_size": 1342177280,
    "md5": "d41d8cd98f00b204e9800998ecf8427e"
  },
  
  "video_meta_display": {
    "resolution_label": "1080p",
    "codec_label": "H265",
    "duration_formatted": "24:00",
    "size_formatted": "1.25 GB"
  },
  
  "torrent_meta": {
    "name": "test.torrent",
    "size": 15360,
    "file_count": 1,
    "files": [{"name": "test.mp4", "size": 1342177280}],
    "tracker_count": 42,
    "tracker_sample": ["http://tracker1/announce", ...]
  },
  
  "torrent_meta_display": {
    "size_formatted": "15.23 KB",
    "name_display": "test.torrent"
  },
  
  "okp_result": {
    "mode": "publish",
    "success": true,
    "returncode": 0,
    "stdout": "OKP 输出内容...",
    "stderr": "",
    "error": null,
    "command": "OKP.Core.exe test.torrent -y"
  }
}
```

---

### PUT /api/tasks/{task_id}/publish_info

更新任务的发布信息（标题、标签、简介等）。

**请求：**

```http
PUT /api/tasks/A1B2C3D4E5F6/publish_info
Content-Type: application/json

{
  "title": "[动漫组] 新番第01集 [1080p]",
  "subtitle": "",
  "tags": "anime,新番,1080p",
  "description": "这是第一集的内容简介...",
  "about": "",
  "poster": "",
  "group_name": "动漫组",
  "category": "Anime",
  "source": "WEB-DL",
  "video_codec": "H265",
  "audio_codec": "AAC",
  "subtitle_type": "内嵌"
}
```

**请求体字段：**

| 字段 | 类型 | 必填 | 默认值 | 说明 |
|------|------|------|--------|------|
| `title` | string | 否 | "" | 发布标题 |
| `subtitle` | string | 否 | "" | 副标题 |
| `tags` | string | 否 | "" | 标签（逗号分隔）|
| `description` | string | 否 | "" | 简介（支持 Markdown）|
| `about` | string | 否 | "" | 关于/联系方式 |
| `poster` | string | 否 | "" | 海报 URL |
| `group_name` | string | 否 | "" | 发布组名称 |
| `category` | string | 否 | "" | 分类 |
| `source` | string | 否 | "" | 来源（WEB-DL, BD 等）|
| `video_codec` | string | 否 | "" | 视频编码 |
| `audio_codec` | string | 否 | "" | 音频编码 |
| `subtitle_type` | string | 否 | "" | 字幕类型（内嵌/外挂）|

**响应：**

```json
{
  "ok": true,
  "message": "发布信息已保存"
}
```

---

## 任务操作接口

### POST /api/tasks/{task_id}/retry

手动重试失败的任务。

**请求：**

```http
POST /api/tasks/A1B2C3D4E5F6/retry
```

**行为：**
- 将 `retry_count` 重置为 0
- 将状态改为 `FAILED`
- 重新放入队列

**响应：**

```json
{
  "ok": true,
  "message": "任务 A1B2C3D4E5F6 已重新加入队列"
}
```

**错误情况：**

| 状态码 | 错误信息 |
|--------|---------|
| 404 | 任务 {task_id} 不存在 |
| 400 | 任务已成功，无需重试 |

---

### DELETE /api/tasks/{task_id}

删除单个任务记录。

**请求：**

```http
DELETE /api/tasks/A1B2C3D4E5F6
```

**响应：**

```json
{
  "ok": true,
  "message": "任务 A1B2C3D4E5F6 已删除"
}
```

**注意：** 这只删除任务记录，不会删除视频文件或 Torrent 文件。

---

### POST /api/tasks/clear_failed

清除所有永久失败的任务记录。

**请求：**

```http
POST /api/tasks/clear_failed
```

**响应：**

```json
{
  "ok": true,
  "cleared": 5
}
```

**字段说明：**

| 字段 | 类型 | 说明 |
|------|------|------|
| `cleared` | int | 清除的任务数量 |

---

## 手动触发接口

### POST /api/tasks/trigger

手动触发处理一个视频文件（绕过文件监控）。

**请求：**

```http
POST /api/tasks/trigger
Content-Type: application/json

{
  "video_path": "D:/videos/my_video.mp4",
  "publish_info": {
    "title": "[我的组] 我的视频 [1080p]",
    "tags": "anime,1080p"
  }
}
```

**请求体字段：**

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `video_path` | string | ✅ | 视频文件的绝对路径 |
| `publish_info` | object | 否 | 可选的发布信息（会自动填充空字段）|

**响应：**

```json
{
  "ok": true,
  "task_id": "X9Y8Z7W6V5U4",
  "message": "任务已加入队列"
}
```

**错误情况：**

| 状态码 | 错误信息 |
|--------|---------|
| 400 | 文件不存在: {path} |
| 400 | 该文件已成功发布，若要重新发布请先删除旧记录 |

---

### POST /api/tasks/{task_id}/upload_torrent

上传 .torrent 文件到指定任务。

**请求：**

```http
POST /api/tasks/A1B2C3D4E5F6/upload_torrent
Content-Type: multipart/form-data

file: <torrent_file>
```

**表单字段：**

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `file` | file | ✅ | .torrent 文件（必须以 .torrent 结尾）|

**验证规则：**
- 文件扩展名必须是 `.torrent`
- 文件内容必须以 `d8:` 开头（bencode 格式）

**响应：**

```json
{
  "ok": true,
  "message": "种子文件已上传: my_video.torrent",
  "torrent_path": "data/torrents/A1B2C3D4E5F6_abc123_my_video.torrent",
  "torrent_meta": {
    "name": "my_video.mp4",
    "size": 1342177280,
    "file_count": 1,
    "files": [...],
    "tracker_count": 42,
    "tracker_sample": [...]
  }
}
```

---

### POST /api/tasks/{task_id}/preview

预览任务的发布信息（不实际调用 OKP）。

**请求：**

```http
POST /api/tasks/A1B2C3D4E5F6/preview
```

**响应：**

```json
{
  "ok": true,
  "mode": "preview",
  "publish_info": {
    "title": "[动漫组] 新番第01集 [1080p]",
    ...
  },
  "video_meta": {
    "resolution": "1920x1080",
    ...
  },
  "torrent_info": {
    "name": "新番第01集.torrent",
    "size": 15360,
    "files": ["新番第01集.mp4"],
    "trackers": [...]
  },
  "message": "预览模式 — 未执行实际发布"
}
```

---

### POST /api/tasks/{task_id}/okp_run

手动触发 OKP 执行（可指定模式）。

**请求：**

```http
POST /api/tasks/A1B2C3D4E5F6/okp_run
Content-Type: application/json

{
  "mode": "publish",
  "auto_confirm": true,
  "sites": ["nyaa", "dmhy"]
}
```

**请求体字段：**

| 字段 | 类型 | 必填 | 默认值 | 说明 |
|------|------|------|--------|------|
| `mode` | string | 否 | `"preview"` | 运行模式：`"preview"`, `"publish"`, `"dry_run"` |
| `auto_confirm` | bool | 否 | `true` | 是否自动确认（-y 参数）|
| `sites` | list | 否 | `null` | 选中的站点列表（用于多站点串行发布）|

**运行模式说明：**

| mode | 效果 |
|------|------|
| `preview` | 仅展示 Torrent 信息，不调用 OKP |
| `dry_run` | 同 preview（兼容旧版命名）|
| `publish` | 实际执行 OKP 发布 |

**响应：**

```json
{
  "ok": true,
  "message": "OKP 正式发布已启动（2个站点）",
  "mode": "publish",
  "preview_only": false,
  "sites": ["nyaa", "dmhy"]
}
```

**注意：** 这是一个异步操作，实际执行结果需要通过轮询任务状态或 SSE 日志获取。

---

### GET /api/tasks/{task_id}/autofill

自动填充任务的发布信息（从文件名 + 视频元数据智能解析）。

**请求：**

```http
GET /api/tasks/A1B2C3D4E5F6/autofill
```

**响应：**

```json
{
  "ok": true,
  "filled_fields": ["title", "group_name", "resolution", "video_codec", "category", "tags"],
  "fills": {
    "title": "新番第01集",
    "group_name": "动漫组",
    "resolution": "1080p",
    "video_codec": "H265",
    "category": "Anime",
    "tags": "Anime"
  },
  "sources": {
    "title": "filename_regex",
    "group_name": "filename_regex",
    "resolution": "filename",
    "video_codec": "filename",
    "category": "heuristic",
    "tags": "from_category"
  },
  "message": "填充了 6 个字段"
}
```

**字段说明：**

| 字段 | 类型 | 说明 |
|------|------|------|
| `filled_fields` | list | 本次填充的字段列表 |
| `fills` | object | 填充的字段及其值 |
| `sources` | object | 每个字段的数据来源 |
| `message` | string | 结果描述 |

**数据来源优先级：**

1. **video_meta** - 从 PyMediaInfo 提取的技术参数
2. **filename_regex** - 从文件名正则解析
3. **heuristic** - 启发式推断（如分类）

---

### GET /api/tasks/{task_id}/okp_output

获取某个任务的 OKP 执行输出（完整 stdout/stderr）。

**请求：**

```http
GET /api/tasks/A1B2C3D4E5F6/okp_output
```

**响应（有输出）：**

```json
{
  "has_output": true,
  "mode": "publish",
  "success": true,
  "returncode": 0,
  "stdout": "OKP 完整输出...\n✓ 登录成功\n✓ 发布完成",
  "stderr": "",
  "error": null,
  "command": "OKP.Core.exe test.torrent -y"
}
```

**响应（无输出）：**

```json
{
  "has_output": false,
  "stdout": "",
  "stderr": "",
  "error": "该任务尚无 OKP 执行记录"
}
```

---

## 日志接口

### GET /api/logs

获取最近的日志条目（支持按级别过滤）。

**请求：**

```http
GET /api/logs?limit=100&level=ERROR
```

**查询参数：**

| 参数 | 类型 | 必填 | 默认值 | 说明 |
|------|------|------|--------|------|
| `limit` | int | 否 | 200 | 返回数量限制 |
| `level` | string | 否 | null | 过滤级别：`DEBUG`, `INFO`, `WARNING`, `ERROR` |

**响应：**

```json
{
  "total": 150,
  "logs": [
    {
      "ts": "12:30:45",
      "level": "INFO",
      "msg": "[A1B2C3D4E5F6] ✅ Task completed successfully"
    },
    {
      "ts": "12:30:44",
      "level": "ERROR",
      "msg": "[B2C3D4E5F6A7] ❌ OKP login failed: Cookie expired"
    }
  ]
}
```

---

### GET /api/logs/file

读取日志文件尾部（持久化日志）。

**请求：**

```http
GET /api/logs/file?lines=500
```

**查询参数：**

| 参数 | 类型 | 必填 | 默认值 | 说明 |
|------|------|------|--------|------|
| `lines` | int | 否 | 500 | 读取行数（从末尾开始）|

**响应：**

```json
{
  "lines": [
    "2026-01-15 12:30:45 INFO [A1B2C3D4E5F6] Task completed successfully",
    "2026-01-15 12:30:44 ERROR [B2C3D4E5F6A7] OKP login failed: Cookie expired",
    "..."
  ]
}
```

---

## 配置接口

### GET /api/sites

获取可配置的站点列表和各站点的状态。

**请求：**

```http
GET /api/sites
```

**响应：**

```json
{
  "sites": [
    {
      "id": "nyaa",
      "name": "Nyaa.si",
      "url": "https://nyaa.si",
      "configured": true,
      "cookies_ok": true,
      "setting_ok": true
    },
    {
      "id": "dmhy",
      "name": "动漫花园",
      "url": "https://share.dmhy.org",
      "configured": true,
      "cookies_ok": true,
      "setting_ok": false
    }
  ],
  "global_cookies_ok": true,
  "global_setting_ok": false,
  "cookies_path": "D:/BT_Automatic_Publishing/cookies.txt",
  "setting_path": null
}
```

---

## 模板系统接口

### GET /api/templates

获取所有已保存的发布模板。

**请求：**

```http
GET /api/templates
```

**响应：**

```json
{
  "ok": true,
  "templates": [
    {
      "id": "abc12345",
      "name": "动漫模板",
      "description": "用于动漫发布的标准模板",
      "category": "Anime",
      "publish_info": {
        "title": "",
        "tags": "anime,1080p",
        "category": "Anime",
        ...
      },
      "created_at": "2026-01-15T10:00:00"
    }
  ]
}
```

---

### POST /api/templates

创建新的发布模板。

**请求：**

```http
POST /api/templates
Content-Type: application/json

{
  "name": "动漫模板",
  "description": "用于动漫发布的标准模板",
  "category": "Anime",
  "publish_info": {
    "tags": "anime,1080p",
    "category": "Anime",
    "source": "WEB-DL",
    "video_codec": "H265",
    "audio_codec": "AAC",
    "subtitle_type": "内嵌"
  }
}
```

**响应：**

```json
{
  "ok": true,
  "template": {
    "id": "abc12345",
    "name": "动漫模板",
    "description": "用于动漫发布的标准模板",
    "category": "Anime",
    "publish_info": {...},
    "created_at": "2026-01-15T12:30:00"
  }
}
```

---

### PUT /api/templates/{template_id}

更新指定模板。

**请求：**

```http
PUT /api/templates/abc12345
Content-Type: application/json

{
  "name": "更新后的模板名",
  "description": "更新后的描述",
  "category": "Anime",
  "publish_info": {
    "tags": "anime,1080p,HDR",
    ...
  }
}
```

**响应：**

```json
{
  "ok": true,
  "template": {
    "id": "abc12345",
    "name": "更新后的模板名",
    ...
  }
}
```

---

### DELETE /api/templates/{template_id}

删除指定模板。

**请求：**

```http
DELETE /api/templates/abc12345
```

**响应：**

```json
{
  "ok": true,
  "message": "模板 '动漫模板' 已删除"
}
```

---

### POST /api/tasks/{task_id}/apply_template/{template_id}

将指定模板应用到任务（填充发布信息，只覆盖空字段）。

**请求：**

```http
POST /api/tasks/A1B2C3D4E5F6/apply_template/abc12345
```

**行为：**
- 读取模板的 `publish_info`
- 对比任务当前的 `publish_info`
- 只填充为空的字段（已有值的不覆盖）
- 保存更新后的任务

**响应：**

```json
{
  "ok": true,
  "message": "模板 '动漫模板' 已应用，填充了 5 个字段",
  "filled_fields": ["tags", "category", "source", "video_codec", "audio_codec"]
}
```

---

## SSE 实时日志

### GET /api/logs/stream

Server-Sent Events (SSE) 实时日志流。

**请求：**

```http
GET /api/logs/stream
Accept: text/event-stream
```

**响应格式：**

```
HTTP/1.1 200 OK
Content-Type: text/event-stream
Cache-Control: no-cache
Connection: keep-alive

data: {"ts":"12:30:45","level":"INFO","msg":"[A1B2C3D4E5F6] Task started"}

data: {"ts":"12:30:46","level":"INFO","msg":"[A1B2C3D4E5F6] Extracting video info..."}

: heartbeat

data: {"ts":"12:30:47","level":"ERROR","msg":"[B2C3D4E5F6A7] OKP failed"}
```

**SSE 事件格式：**

| 字段 | 类型 | 说明 |
|------|------|------|
| `ts` | string | 时间戳 (HH:MM:SS) |
| `level` | string | 日志级别 (DEBUG/INFO/WARNING/ERROR) |
| `msg` | string | 日志消息 |

**心跳机制：**
- 每 0.5 秒发送一次心跳（`: heartbeat`）
- 用于保持连接活跃
- 客户端应忽略心跳消息

**前端 JavaScript 示例：**

```javascript
const eventSource = new EventSource('/api/logs/stream');

eventSource.onmessage = function(event) {
    const data = JSON.parse(event.data);
    
    // 忽略心跳
    if (!data.ts && !data.level && !data.msg) return;
    
    console.log(`[${data.ts}] ${data.level}: ${data.msg}`);
    
    // 根据级别显示不同颜色
    const logEntry = document.createElement('div');
    logEntry.className = `log-${data.level.toLowerCase()}`;
    logEntry.textContent = `[${data.ts}] ${data.msg}`;
    
    document.getElementById('log-container').appendChild(logEntry);
};

eventSource.onerror = function(error) {
    console.error('SSE connection error:', error);
    // 自动重连（浏览器默认行为）
};
```

**断线重连：**
- 浏览器原生支持自动重连
- 重连后会重新发送最近 50 条日志
- 无需额外代码处理

---

## 错误处理

### 统一错误格式

所有错误响应都遵循统一格式：

```json
{
  "detail": "错误描述信息"
}
```

### 常见错误码

#### 400 Bad Request

```json
{
  "detail": "只能上传 .torrent 文件"
}
```

**触发条件：**
- 上传文件格式错误
- 请求体缺少必填字段
- 参数类型错误

---

#### 404 Not Found

```json
{
  "detail": "任务 ABCD12345678 不存在"
}
```

**触发条件：**
- 任务 ID 不存在
- 模板 ID 不存在

---

#### 503 Service Unavailable

```json
{
  "detail": "系统未就绪，队列未初始化"
}
```

**触发条件：**
- 服务刚启动，队列尚未初始化
- Worker 未启动

---

### 业务逻辑错误

除了 HTTP 状态码，某些接口还会返回业务错误：

```json
{
  "ok": false,
  "message": "任务已成功，无需重试"
}
```

---

## 前端集成示例

### JavaScript API 封装

```javascript
class BTAutoPublishAPI {
    constructor(baseURL = '/api') {
        this.baseURL = baseURL;
    }

    async request(method, path, data = null) {
        const url = `${this.baseURL}${path}`;
        const options = {
            method,
            headers: {'Content-Type': 'application/json'}
        };
        
        if (data) {
            options.body = JSON.stringify(data);
        }
        
        try {
            const response = await fetch(url, options);
            
            if (!response.ok) {
                const error = await response.json();
                throw new Error(error.detail || `HTTP ${response.status}`);
            }
            
            return await response.json();
        } catch (error) {
            console.error(`API Error [${method} ${path}]:`, error);
            throw error;
        }
    }

    // ========== 系统状态 ==========
    async getStatus() {
        return this.request('GET', '/status');
    }

    async getConfig() {
        return this.request('GET', '/config');
    }

    // ========== 任务管理 ==========
    async getTasks(params = {}) {
        const query = new URLSearchParams(params).toString();
        return this.request('GET', `/tasks${query ? '?' + query : ''}`);
    }

    async getTask(taskId, full = true) {
        return this.request('GET', `/tasks/${taskId}?full=${full}`);
    }

    async updatePublishInfo(taskId, publishInfo) {
        return this.request('PUT', `/tasks/${taskId}/publish_info`, publishInfo);
    }

    // ========== 任务操作 ==========
    async retryTask(taskId) {
        return this.request('POST', `/tasks/${taskId}/retry`);
    }

    async deleteTask(taskId) {
        return this.request('DELETE', `/tasks/${taskId}`);
    }

    async clearFailedTasks() {
        return this.request('POST', '/tasks/clear_failed');
    }

    // ========== 手动操作 ==========
    async triggerTask(videoPath, publishInfo = null) {
        return this.request('POST', '/tasks/trigger', {
            video_path: videoPath,
            publish_info: publishInfo
        });
    }

    async runOKP(taskId, options = {}) {
        return this.request('POST', `/tasks/${taskId}/okp_run`, {
            mode: options.mode || 'publish',
            auto_confirm: options.autoConfirm !== false,
            sites: options.sites || null
        });
    }

    async autofillTask(taskId) {
        return this.request('GET', `/tasks/${taskId}/autofill`);
    }

    // ========== 日志 ==========
    async getLogs(limit = 200, level = null) {
        const params = {limit};
        if (level) params.level = level;
        const query = new URLSearchParams(params).toString();
        return this.request('GET', `/logs?${query}`);
    }

    connectToLogStream(onMessage, onError) {
        const eventSource = new EventSource(`${this.baseURL}/logs/stream`);
        
        eventSource.onmessage = (event) => {
            const data = JSON.parse(event.data);
            if (onMessage) onMessage(data);
        };
        
        eventSource.onerror = (error) => {
            if (onError) onError(error);
        };
        
        return eventSource; // 返回引用以便关闭
    }

    // ========== 模板系统 ==========
    async getTemplates() {
        return this.request('GET', '/templates');
    }

    async createTemplate(templateData) {
        return this.request('POST', '/templates', templateData);
    }

    async updateTemplate(templateId, templateData) {
        return this.request('PUT', `/templates/${templateId}`, templateData);
    }

    async deleteTemplate(templateId) {
        return this.request('DELETE', `/templates/${templateId}`);
    }

    async applyTemplate(taskId, templateId) {
        return this.request('POST', `/tasks/${taskId}/apply_template/${templateId}`);
    }
}


// 使用示例
const api = new BTAutoPublishAPI();

// 获取任务列表
async function loadTasks() {
    try {
        const result = await api.getTasks({status: 'failed', limit: 20});
        console.log('Failed tasks:', result.tasks);
    } catch (error) {
        console.error('Failed to load tasks:', error.message);
    }
}

// 连接实时日志
function startLogStream() {
    api.connectToLogStream(
        (logEntry) => {
            // 处理日志消息
            console.log(`[${logEntry.ts}] ${logEntry.level}: ${logEntry.msg}`);
            appendToLogUI(logEntry);  // 更新 UI
        },
        (error) => {
            console.error('Log stream error:', error);
        }
    );
}

// 手动触发任务
async function manualTrigger(videoPath) {
    try {
        const result = await api.triggerTask(videoPath);
        alert(`任务已创建: ${result.task_id}`);
    } catch (error) {
        alert(`错误: ${error.message}`);
    }
}
```

---

### cURL 示例

#### 获取系统状态

```bash
curl http://localhost:8080/api/status
```

#### 获取任务列表

```bash
curl "http://localhost:8080/api/tasks?status=failed&limit=10"
```

#### 获取任务详情

```bash
curl http://localhost:8080/api/tasks/A1B2C3D4E5F6?full=true
```

#### 更新发布信息

```bash
curl -X PUT http://localhost:8080/api/tasks/A1B2C3D4E5F6/publish_info \
  -H "Content-Type: application/json" \
  -d '{"title": "[Group] Title [1080p]", "tags": "anime,1080p"}'
```

#### 重试失败任务

```bash
curl -X POST http://localhost:8080/api/tasks/A1B2C3D4E5F6/retry
```

#### 删除任务

```bash
curl -X DELETE http://localhost:8080/api/tasks/A1B2C3D4E5F6
```

#### 手动触发处理

```bash
curl -X POST http://localhost:8080/api/tasks/trigger \
  -H "Content-Type: application/json" \
  -d '{"video_path": "D:/videos/test.mp4"}'
```

#### 执行 OKP 发布

```bash
curl -X POST http://localhost:8080/api/tasks/A1B2C3D4E5F6/okp_run \
  -H "Content-Type: application/json" \
  -d '{"mode": "publish", "auto_confirm": true}'
```

#### 获取实时日志（SSE）

```bash
curl -N http://localhost:8080/api/logs/stream
```

---

## 总结

本 API 设计遵循以下原则：

1. **RESTful 风格** - 使用标准 HTTP 方法和语义化 URL
2. **一致性** - 统一的请求/响应格式
3. **可预测性** - 清晰的错误码和错误信息
4. **可观测性** - 丰富的日志和统计接口
5. **易用性** - 完整的 Swagger 文档和示例

通过这套 API，你可以：
- 📊 构建自定义的管理界面
- 🔌 与其他系统集成
- 🤖 编写自动化脚本
- 📱 开发移动端应用

---

**API 版本：** v2.1  
**最后更新：** 2026-04-05  
**作者：** BT Auto Publishing Team
