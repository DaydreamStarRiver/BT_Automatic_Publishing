"""
BT 自动发布系统 - REST API 路由实现 (v3.0 Standard)
=====================================================

基于 task_schema.py 定义的统一数据模型，
实现完整的 FastAPI RESTful 接口。

设计原则：
  - 前后端统一使用 Task 模型
  - 完整的状态机控制
  - 标准化的错误处理
  - 完善的日志记录

作者: BT Auto Publishing System Team
版本: 3.0.0 Standard
日期: 2026-01-30
"""

from __future__ import annotations

import asyncio
import json
import os
from datetime import datetime
from pathlib import Path
from typing import Optional, List, Dict, Any
from enum import Enum

from fastapi import (
    FastAPI,
    HTTPException,
    Request,
    UploadFile,
    File,
    Query,
    Depends
)
from fastapi.responses import JSONResponse, HTMLResponse
from pydantic import BaseModel, Field

# 导入统一数据模型
from src.core.task_schema import (
    Task,
    TaskStatus,
    PublishMode,
    SiteID,
    PublishInfo,
    MediaInfo,
    PublishConfig,
    VideoMeta,
    TorrentMeta,
    OKPResult,
    CreateTaskRequest,
    UpdateTaskRequest,
    PublishTaskRequest,
    TaskListResponse,
    TaskResponse,
    ApiResponse,
    LogEntry,
    TaskLogResponse,
)

from src.config import get_config, WATCH_DIR, OUTPUT_TORRENT_DIR
from src.logger import setup_logger

logger = setup_logger(__name__)


# ══════════════════════════════════════════════════════════════════════
#  全局状态（由 main.py 注入）
# ══════════════════════════════════════════════════════════════════════

_task_queue = None
_worker = None


def init_api(task_queue, worker):
    """初始化 API（在 main.py 中调用）"""
    global _task_queue, _worker
    _task_queue = task_queue
    _worker = worker
    logger.info("✅ API v3.0 初始化完成")


def _require_queue():
    """检查队列是否已初始化"""
    if _task_queue is None:
        raise HTTPException(
            status_code=503,
            detail="系统未就绪，任务队列未初始化"
        )


# ══════════════════════════════════════════════════════════════════════
#  FastAPI 应用实例
# ══════════════════════════════════════════════════════════════════════

app = FastAPI(
    title="BT 自动发布系统 API",
    version="3.0.0",
    description="""
## BT 自动发布系统 - 统一 REST API (v3.0 Standard)

### 核心特性
- **统一数据结构**: 前后端使用同一套 Task 模型
- **完整状态机**: 严格的状态流转控制
- **RESTful 设计**: 标准 HTTP 方法和状态码
- **类型安全**: Pydantic v2 验证

### 主要功能
1. 任务 CRUD 管理
2. 发布信息编辑
3. 多站点发布控制
4. 实时日志查询
5. 状态监控
""",
    docs_url="/docs",
    redoc_url="/redoc",
)


# ══════════════════════════════════════════════════════════════════════
#  辅助函数
# ══════════════════════════════════════════════════════════════════════

def _task_to_dict(task, full: bool = True) -> Dict[str, Any]:
    """
    将内部 Task 对象转换为字典（兼容新旧模型）

    Args:
        task: 内部 Task 对象（可能是旧版 dataclass 或新版 Pydantic）
        full: 是否返回完整信息
    """
    # 如果已经是 dict，直接返回
    if isinstance(task, dict):
        return task

    # 如果是 Pydantic 模型，直接使用 model_dump()
    if hasattr(task, 'model_dump'):
        data = task.model_dump()
        if not full:
            # 精简模式：只返回基本信息
            return {
                'id': data.get('id'),
                'file_path': data.get('file_path'),
                'status': data.get('status'),
                'retry_count': data.get('retry_count', 0),
                'error_message': data.get('error_message'),
                'created_at': data.get('created_at'),
                'updated_at': data.get('updated_at'),
                'display_title': task.display_title if hasattr(task, 'display_title') else None,
            }
        return data

    # 兼容旧版 dataclass
    if hasattr(task, 'to_dict'):
        return task.to_dict()

    # 兜底：直接返回 __dict__
    return task.__dict__


def _get_task_or_404(task_id: str):
    """获取任务或返回404"""
    _require_queue()
    task = _task_queue.persistence.get_task(task_id.upper())
    if not task:
        raise HTTPException(
            status_code=404,
            detail=f"任务 {task_id} 不存在"
        )
    return task


def _log_action(task_id: str, action: str, detail: str = "", level: str = "INFO"):
    """记录操作日志"""
    logger.info(f"[{task_id}] {action} - {detail}")


# ══════════════════════════════════════════════════════════════════════
#  路由：系统状态
# ══════════════════════════════════════════════════════════════════════

@app.get("/api/status", tags=["系统"])
async def get_system_status():
    """获取系统整体状态"""
    try:
        _require_queue()
        stats = _task_queue.get_statistics()

        return ApiResponse(
            success=True,
            data={
                "version": "3.0.0",
                "queue_size": _task_queue.queue_size(),
                "worker_running": _worker is not None and getattr(_worker, "_running", False),
                "watch_dir": str(WATCH_DIR()),
                "output_dir": str(OUTPUT_TORRENT_DIR()),
                "stats": stats,
                "uptime_ts": datetime.now().isoformat(),
                "okp_configured": bool(get_config("okp_cookies_path")) or bool(get_config("okp_setting_path")),
                "supported_sites": [site.value for site in SiteID],
            },
            message="系统运行正常"
        )
    except Exception as e:
        logger.error(f"获取系统状态失败: {e}")
        return ApiResponse(
            success=False,
            error=str(e),
            message="获取系统状态失败"
        )


# ══════════════════════════════════════════════════════════════════════
#  路由：任务管理（CRUD）
# ══════════════════════════════════════════════════════════════════════

@app.get("/api/tasks", response_model=TaskListResponse, tags=["任务"])
async def list_tasks(
    status: Optional[str] = Query(None, description="过滤状态"),
    limit: int = Query(200, ge=1, le=500, description="每页数量"),
    offset: int = Query(0, ge=0, description="偏移量")
):
    """
    获取任务列表

    支持按状态过滤和分页。
    返回任务列表，默认按更新时间倒序。
    """
    _require_queue()

    all_tasks = list(_task_queue.get_all_tasks().values())
    all_tasks.sort(key=lambda t: t.updated_at, reverse=True)

    # 状态过滤
    if status:
        try:
            filter_status = TaskStatus(status)
            all_tasks = [t for t in all_tasks if t.status == filter_status]
        except ValueError:
            pass

    total = len(all_tasks)
    page = all_tasks[offset: offset + limit]

    return TaskListResponse(
        total=total,
        offset=offset,
        limit=limit,
        tasks=[_task_to_dict(t, full=False) for t in page]
    )


@app.get("/api/tasks/{task_id}", response_model=TaskResponse, tags=["任务"])
async def get_task(task_id: str, full: bool = True):
    """
    获取单个任务详情

    - full=true: 返回完整信息（用于编辑页面）
    - full=false: 返回精简信息（用于列表展示）
    """
    task = _get_task_or_404(task_id)

    return TaskResponse(
        task=_task_to_dict(task, full=full),
        message=None
    )


@app.post("/api/tasks", response_model=ApiResponse, tags=["任务"])
async def create_task(request: CreateTaskRequest):
    """
    创建新任务

    通常由文件监控系统（Watcher）自动调用。
    创建后任务状态为 PENDING。
    """
    _require_queue()

    file_path = Path(request.file_path)
    if not file_path.exists():
        raise HTTPException(
            status_code=400,
            detail=f"文件不存在: {request.file_path}"
        )

    # 生成任务ID并创建对象
    from src.core.task_model import Task as LegacyTask
    task = LegacyTask.create_from_file(str(file_path))

    # 加入队列
    success = _task_queue.enqueue(task)
    if not success:
        raise HTTPException(
            status_code=409,
            detail=f"任务已存在: {task.id}（可能已成功完成）"
        )

    _log_action(task.id, "创建任务", f"文件: {file_path.name}")

    return ApiResponse(
        success=True,
        data=_task_to_dict(task),
        message=f"任务创建成功: {task.id}"
    )


@app.put("/api/tasks/{task_id}", response_model=ApiResponse, tags=["任务"])
async def update_task(task_id: str, request: UpdateTaskRequest):
    """
    更新任务（UI 编辑）

    用于更新发布信息和发布配置。
    只允许更新 READY 或 PENDING 状态的任务。
    """
    task = _get_task_or_404(task_id)

    # 状态校验
    if task.status not in [TaskStatus.PENDING, TaskStatus.READY]:
        raise HTTPException(
            status_code=400,
            detail=f"当前状态 {task.status.value} 不允许编辑"
        )

    # 更新发布信息
    if request.publish_info:
        publish_data = request.publish_info.model_dump()
        for key, value in publish_data.items():
            if hasattr(task.publish_info, key):
                setattr(task.publish_info, key, value)

    # 更新发布配置
    if request.publish_config:
        config_data = request.publish_config.model_dump()
        # 注意：这里需要根据实际模型结构调整
        # task.publish_config.sites = config_data.get('sites', [])

    # 保存
    task.updated_at = datetime.now().isoformat()
    _task_queue.persistence.save_task(task)

    _log_action(task_id, "更新任务", "发布信息已修改")

    return ApiResponse(
        success=True,
        message="任务更新成功"
    )


@app.delete("/api/tasks/{task_id}", response_model=ApiResponse, tags=["任务"])
async def delete_task(task_id: str):
    """
    删除任务

    只允许删除终态任务（SUCCESS/FAILED/CANCELLED）。
    """
    task = _get_task_or_404(task_id)

    # 状态校验
    if not task.is_terminal():
        raise HTTPException(
            status_code=400,
            detail=f"只能删除终态任务，当前状态: {task.status.value}"
        )

    # 删除
    _task_queue.persistence.delete_task(task.id)

    _log_action(task_id, "删除任务")

    return ApiResponse(
        success=True,
        message=f"任务 {task_id} 已删除"
    )


# ══════════════════════════════════════════════════════════════════════
#  路由：发布操作（核心）
# ══════════════════════════════════════════════════════════════════════

@app.post("/api/tasks/{task_id}/publish", response_model=ApiResponse, tags=["发布"])
async def publish_task(task_id: str, request: PublishTaskRequest):
    """
    发布任务（核心接口）

    这是整个系统最关键的接口。

    行为流程：
      1. 验证任务状态必须为 READY
      2. 验证 torrent_path 存在
      3. 验证 sites 不为空
      4. 状态转换: READY → UPLOADING
      5. 加入 Worker 队列
      6. 异步执行 OKP
      7. 根据结果更新状态: UPLOADING → SUCCESS/FAILED

    支持三种模式：
      - preview: 仅预览，不实际发布
      - dry_run: 试运行，模拟但不提交
      - publish: 正式发布
    """
    task = _get_task_or_404(task_id)

    # 状态校验
    if task.status != TaskStatus.READY:
        raise HTTPException(
            status_code=400,
            detail=f"任务尚未就绪，当前状态: {task.status.value}"
        )

    # Torrent 校验
    if not task.torrent_path or not Path(task.torrent_path).exists():
        raise HTTPException(
            status_code=400,
            detail="Torrent 文件不存在，请先上传或等待生成"
        )

    # 站点校验
    sites = request.sites or []
    if not sites:
        raise HTTPException(
            status_code=400,
            detail="请至少选择一个发布站点"
        )

    # 执行状态转换
    try:
        task.transition_to(TaskStatus.UPLOADING)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    # 更新配置
    auto_confirm = request.auto_confirm if request.auto_confirm is not None else True

    # 保存状态
    _task_queue.persistence.save_task(task)

    _log_action(
        task_id,
        "开始发布",
        f"模式={request.mode.value}, 站点={sites}, auto_confirm={auto_confirm}"
    )

    # 异步执行
    async def _do_publish():
        try:
            from src.core.executor_okp import OKPExecutor
            okp_path = get_config("okp_path")
            setting_path = get_config("okp_setting_path")
            cookies_path = get_config("okp_cookies_path")
            timeout = get_config("okp_timeout", 300)

            preview_only = request.mode in [PublishMode.PREVIEW, PublishMode.DRY_RUN]

            result = OKPExecutor.run_okp_upload(
                torrent_path=task.torrent_path,
                okp_path=okp_path,
                setting_path=setting_path,
                cookies_path=cookies_path,
                timeout=timeout,
                auto_confirm=auto_confirm,
                preview_only=preview_only,
            )

            # 更新结果
            if result.get('success'):
                task.transition_to(TaskStatus.SUCCESS)
            else:
                task.transition_to(TaskStatus.FAILED, result.get('error'))

            # 保存OKP结果（如果支持）
            if hasattr(task, 'okp_result'):
                task.okp_result = OKPResult(**result)

            _task_queue.persistence.save_task(task)

            _log_action(
                task_id,
                "发布完成",
                f"success={result.get('success')}"
            )

        except Exception as e:
            task.transition_to(TaskStatus.FAILED, str(e))
            _task_queue.persistence.save_task(task)
            _log_action(task_id, "发布失败", str(e), "ERROR")

    # 启动后台任务
    asyncio.create_task(_do_publish())

    mode_label = {
        PublishMode.PREVIEW: "预览",
        PublishMode.DRY_RUN: "试运行",
        PublishMode.PUBLISH: "正式发布"
    }[request.mode]

    return ApiResponse(
        success=True,
        data={
            "task_id": task_id,
            "status": TaskStatus.UPLOADING.value,
            "mode": request.mode.value,
            "sites": sites,
        },
        message=f"{mode_label}任务已启动"
    )


@app.post("/api/tasks/{task_id}/retry", response_model=ApiResponse, tags=["任务"])
async def retry_task(task_id: str):
    """
    重试失败的任务

    条件：
      - 当前状态必须是 FAILED
      - 重试次数 < 最大重试次数

    行为：
      1. FAILED → RETRYING
      2. retry_count += 1
      3. 自动触发重新发布
    """
    task = _get_task_or_404(task_id)

    # 状态校验
    if task.status != TaskStatus.FAILED:
        raise HTTPException(
            status_code=400,
            detail=f"只有失败的任务可以重试，当前状态: {task.status.value}"
        )

    # 重试次数校验
    if not task.can_retry():
        raise HTTPException(
            status_code=400,
            detail=f"已达最大重试次数 ({task.retry_count}/{task.max_retries})"
        )

    # 执行状态转换
    try:
        task.transition_to(TaskStatus.RETRYING)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    _task_queue.persistence.save_task(task)

    _log_action(
        task_id,
        "重试任务",
        f"第 {task.retry_count + 1}/{task.max_retries} 次"
    )

    # TODO: 触发重新发布逻辑

    return ApiResponse(
        success=True,
        message=f"重试已启动 (第{task.retry_count}/{task.max_retries}次)"
    )


@app.post("/api/tasks/{task_id}/cancel", response_model=ApiResponse, tags=["任务"])
async def cancel_task(task_id: str):
    """
    取消任务

    可以取消任何活跃状态的任务。
    取消后进入 CANCELLED 终态，不可恢复。
    """
    task = _get_task_or_404(task_id)

    # 状态校验
    if not task.is_active():
        raise HTTPException(
            status_code=400,
            detail=f"无法取消终态任务，当前状态: {task.status.value}"
        )

    # 执行取消
    try:
        task.transition_to(TaskStatus.CANCELLED)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    _task_queue.persistence.save_task(task)

    _log_action(task_id, "取消任务")

    return ApiResponse(
        success=True,
        message="任务已取消"
    )


# ══════════════════════════════════════════════════════════════════════
#  路由：Torrent 管理
# ══════════════════════════════════════════════════════════════════════

@app.post("/api/tasks/{task_id}/torrent", response_model=ApiResponse, tags=["Torrent"])
async def upload_torrent(
    task_id: str,
    file: UploadFile = File(..., description=".torrent 文件")
):
    """
    上传 Torrent 文件

    用于手动上传或替换 Torrent 文件。

    行为：
      1. 保存文件到 output 目录
      2. 解析 Torrent 元信息
      3. 更新 torrent_path 和 torrent_meta
      4. 如果是 PENDING 状态且已有 torrent → READY
    """
    task = _get_task_or_404(task_id)

    # 验证文件类型
    if not file.filename.endswith('.torrent'):
        raise HTTPException(
            status_code=400,
            detail="只支持 .torrent 文件"
        )

    # 读取文件内容
    content = await file.read()

    # 保存到输出目录
    output_dir = Path(OUTPUT_TORRENT_DIR())
    output_dir.mkdir(parents=True, exist_ok=True)

    torrent_filename = f"{task_id.upper()}.torrent"
    torrent_path = output_dir / torrent_filename

    with open(torrent_path, 'wb') as f:
        f.write(content)

    # 解析 Torrent 信息
    try:
        import torf
        torrent = torf.Torrent.from_file(str(torrent_path))

        torrent_meta = TorrentMeta(
            name=torrent.name,
            size=torrent.size,
            file_count=len(torrent.files),
            files=[
                {"name": f.path, "size": f.size}
                for f in list(torrent.files)[:10]
            ],
            tracker_count=len(torrent.trackers),
            trackers_sample=list(torrent.trackers)[:3] if torrent.trackers else []
        )

        # 更新任务
        task.torrent_path = str(torrent_path)
        task.torrent_meta = torrent_meta

        # 状态转换：如果之前没有torrent，现在有了
        if task.status == TaskStatus.PENDING:
            task.transition_to(TaskStatus.READY)

        _task_queue.persistence.save_task(task)

        _log_action(
            task_id,
            "上传Torrent",
            f"文件: {file.filename}, 大小: {torrent.size:,} bytes"
        )

        return ApiResponse(
            success=True,
            data={
                "torrent_path": str(torrent_path),
                "torrent_meta": torrent_meta.model_dump(),
                "new_status": task.status.value
            },
            message="Torrent 上传成功"
        )

    except Exception as e:
        # 清理失败的文件
        if torrent_path.exists():
            torrent_path.unlink()

        raise HTTPException(
            status_code=500,
            detail=f"解析 Torrent 失败: {str(e)}"
        )


# ══════════════════════════════════════════════════════════════════════
#  路由：日志查询
# ══════════════════════════════════════════════════════════════════════

@app.get("/api/tasks/{task_id}/logs", response_model=TaskLogResponse, tags=["日志"])
async def get_task_logs(
    task_id: str,
    level: Optional[str] = Query(None, description="日志级别过滤"),
    limit: int = Query(100, ge=1, le=1000, description="返回数量")
):
    """
    获取任务相关日志

    支持按级别过滤（INFO/WARN/ERROR/DEBUG）。
    """
    task = _get_task_or_404(task_id)

    # TODO: 从日志系统查询该任务的日志
    # 这里先返回空列表作为占位

    logs = []

    return TaskLogResponse(
        task_id=task_id.upper(),
        logs=logs,
        total=len(logs)
    )


# ══════════════════════════════════════════════════════════════════════
#  路由：站点管理
# ══════════════════════════════════════════════════════════════════════

@app.get("/api/sites", tags=["站点"])
async def get_sites_status():
    """
    获取支持的站点列表及其状态

    返回每个站点的：
      - ID、名称、URL
      - Cookie 配置状态
      - 是否可用
    """
    _require_queue()

    sites = [
        {
            "id": SiteID.NYAA.value,
            "name": "Nyaa.si",
            "url": "https://nyaa.si",
            "icon": "🔵"
        },
        {
            "id": SiteID.DMHY.value,
            "name": "动漫花园",
            "url": "https://share.dmhy.org",
            "icon": "🌸"
        },
        {
            "id": SiteID.ACG_RIP.value,
            "name": "ACG.RIP",
            "url": "https://acg.rip",
            "icon": "🟢"
        },
        {
            "id": SiteID.BANGUMI.value,
            "name": "萌番组",
            "url": "https://bangumi.moe",
            "icon": "🟣"
        },
        {
            "id": SiteID.ACGNX_ASIA.value,
            "name": "AcgnX Asia",
            "url": "https://share.acgnx.se",
            "icon": "🟡"
        },
        {
            "id": SiteID.ACGNX_GLOBAL.value,
            "name": "AcgnX Global",
            "url": "https://www.acgnx.se",
            "icon": "🟠"
        },
    ]

    # 检测 Cookie 配置状态
    cookies_path = get_config("okp_cookies_path")
    setting_path = get_config("okp_setting_path")

    has_cookies = bool(cookies_path and Path(cookies_path).exists()) if cookies_path else False
    has_setting = bool(setting_path and Path(setting_path).exists()) if setting_path else False

    for site in sites:
        site["configured"] = has_cookies or has_setting
        site["cookies_ok"] = has_cookies
        site["setting_ok"] = has_setting

    return {
        "sites": sites,
        "global_cookies_ok": has_cookies,
        "global_setting_ok": has_setting,
        "cookies_path": str(cookies_path) if cookies_path else None,
        "setting_path": str(setting_path) if setting_path else None,
    }


# ══════════════════════════════════════════════════════════════════════
#  路由：模板管理（保持向后兼容）
# ══════════════════════════════════════════════════════════════════════

_TEMPLATES_FILE = Path(__file__).parent.parent.parent / "data" / "templates.json"


@app.get("/api/templates", tags=["模板"])
async def list_templates():
    """获取所有已保存的发布模板"""
    try:
        if _TEMPLATES_FILE.exists():
            with open(_TEMPLATES_FILE, 'r', encoding='utf-8') as f:
                templates = json.load(f)
        else:
            templates = {}

        return {
            "ok": True,
            "templates": list(templates.values()),
            "total": len(templates)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/templates", tags=["模板"])
async def create_template(request: dict):
    """创建新模板"""
    try:
        if _TEMPLATES_FILE.exists():
            with open(_TEMPLATES_FILE, 'r', encoding='utf-8') as f:
                templates = json.load(f)
        else:
            templates = {}

        import uuid
        template_id = uuid.uuid4().hex[:8]

        template = {
            "id": template_id,
            "name": request.get('name', ''),
            "description": request.get('description', ''),
            "category": request.get('category', ''),
            "publish_info": request.get('publish_info', {}),
            "created_at": datetime.now().isoformat(),
        }

        templates[template_id] = template

        _TEMPLATES_FILE.parent.mkdir(parents=True, exist_ok=True)
        with open(_TEMPLATES_FILE, 'w', encoding='utf-8') as f:
            json.dump(templates, f, ensure_ascii=False, indent=2)

        return {"ok": True, "template": template}

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ══════════════════════════════════════════════════════════════════════
#  错误处理
# ══════════════════════════════════════════════════════════════════════

@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    """自定义 HTTP 异常响应"""
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "success": False,
            "error": exc.detail,
            "message": exc.detail
        }
    )


@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    """通用异常处理器"""
    logger.error(f"未处理的异常: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={
            "success": False,
            "error": "服务器内部错误",
            "message": str(exc)
        }
    )


# ══════════════════════════════════════════════════════════════════════
#  启动事件
# ══════════════════════════════════════════════════════════════════════

@app.on_event("startup")
async def startup_event():
    """应用启动时执行"""
    logger.info("🚀 BT 发布系统 API v3.0 启动中...")


@app.on_event("shutdown")
async def shutdown_event():
    """应用关闭时执行"""
    logger.info("🛑 BT 发布系统 API v3.0 已停止")


if __name__ == "__main__":
    import uvicorn
    print("=" * 70)
    print("BT 发布系统 - API 服务 (v3.0)")
    print("=" * 70)
    print("\n📚 API 文档:")
    print("   Swagger UI: http://localhost:8000/docs")
    print("   ReDoc:      http://localhost:8000/redoc\n")

    uvicorn.run(app, host="0.0.0.0", port=8000, reload=True)
