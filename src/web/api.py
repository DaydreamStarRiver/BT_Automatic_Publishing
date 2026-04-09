"""
BT 自动发布系统 - Web API 模块 (v2.1 Enhanced)
提供 FastAPI REST 接口，供前端面板调用
支持：任务 CRUD、发布信息编辑、OKP 输出查看、SSE 日志流
"""

import asyncio
import json
import os
import re
import time
import uuid
from collections import deque
from datetime import datetime
from pathlib import Path
from threading import Lock
from typing import Optional

from fastapi import FastAPI, HTTPException, Request, UploadFile, File, Form
from fastapi.responses import HTMLResponse, JSONResponse, StreamingResponse
from pydantic import BaseModel

from src.config import get_config, WATCH_DIR, OUTPUT_TORRENT_DIR
from src.core.task_model import Task, TaskStatus, PublishInfo, VideoMeta, TorrentMeta, OKPResult
from src.logger import setup_logger

logger = setup_logger(__name__)

# ─── 全局共享引用（由 main.py 注入）────────────────────────────────────────────
_task_queue = None
_worker = None

# ─── 日志缓冲（最近 500 条，供前端轮询）────────────────────────────────────────
_log_buffer = deque(maxlen=500)
_log_lock = Lock()
_log_sse_clients = []  # SSE 订阅客户端列表

# ─── 模板存储 ─────────────────────────────────────────────────────────────────
_TEMPLATES_FILE = Path(__file__).parent.parent.parent / "data" / "templates.json"
_TEMPLATE_LOCK = Lock()

def _load_templates() -> dict:
    try:
        if _TEMPLATES_FILE.exists():
            with open(_TEMPLATES_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
    except Exception:
        pass
    return {}

def _save_templates(templates: dict):
    _TEMPLATES_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(_TEMPLATES_FILE, "w", encoding="utf-8") as f:
        json.dump(templates, f, ensure_ascii=False, indent=2)


def init_web(task_queue, worker):
    """在 main.py 中调用，注入队列和 Worker 引用"""
    global _task_queue, _worker
    _task_queue = task_queue
    _worker = worker
    _install_log_interceptor()


def _install_log_interceptor():
    """在根 logger 上加一个 Handler，把日志条目写入内存缓冲"""
    import logging

    class BufferHandler(logging.Handler):
        def emit(self, record):
            entry = {
                "ts": datetime.fromtimestamp(record.created).strftime("%H:%M:%S"),
                "level": record.levelname,
                "msg": record.getMessage(),
            }
            with _log_lock:
                _log_buffer.append(entry)
            for q in list(_log_sse_clients):
                try:
                    q.put_nowait(entry)
                except Exception:
                    pass

    handler = BufferHandler()
    handler.setLevel("DEBUG")
    logging.getLogger().addHandler(handler)


# ─── FastAPI 应用 ─────────────────────────────────────────────────────────────
app = FastAPI(title="BT 自动发布系统", version="2.2.0")


# ── 工具函数 ──────────────────────────────────────────────────────────────────

def _require_queue():
    if _task_queue is None:
        raise HTTPException(status_code=503, detail="系统未就绪，队列未初始化")


def _format_size(size_bytes):
    if size_bytes is None or size_bytes == 0:
        return "-"
    for unit in ["B", "KB", "MB", "GB", "TB"]:
        if abs(size_bytes) < 1024.0:
            return f"{size_bytes:.1f} {unit}"
        size_bytes /= 1024.0
    return f"{size_bytes:.1f} PB"


def _format_duration(seconds):
    if not seconds or seconds <= 0:
        return "-"
    m, s = divmod(int(seconds), 60)
    h, m = divmod(m, 60)
    if h > 0:
        return f"{h}:{m:02d}:{s:02d}"
    return f"{m}:{s:02d}"


def _task_to_dict(task: Task, full: bool = False) -> dict:
    """将 Task 转为字典；full=True 时包含完整元信息和发布信息"""
    video_name = Path(task.video_path).name if task.video_path else "-"

    d = {
        "id": task.id,
        "video_name": video_name,
        "video_path": task.video_path,
        "torrent_path": task.torrent_path,
        "status": task.status.value,
        "retry_count": task.retry_count,
        "max_retries": task.max_retries,
        "error_message": task.error_message,
        "created_at": task.created_at,
        "updated_at": task.updated_at,
    }

    if full:
        d["publish_info"] = task.publish_info.to_dict()
        d["video_meta"] = task.video_meta.to_dict()
        d["torrent_meta"] = task.torrent_meta.to_dict()
        # 格式化显示用的字段
        vm = task.video_meta
        d["video_meta_display"] = {
            "resolution_label": vm.resolution or f"{vm.width}x{vm.height}",
            "codec_label": vm.codec,
            "duration_formatted": _format_duration(vm.duration_seconds),
            "size_formatted": _format_size(vm.file_size),
        }
        tm = task.torrent_meta
        d["torrent_meta_display"] = {
            "size_formatted": _format_size(tm.size),
            "name_display": tm.name or video_name,
        }
        if task.okp_result:
            d["okp_result"] = task.okp_result.to_dict()

    return d


# ══════════════════════════════════════════════════════════════════════
#  路由：系统状态
# ══════════════════════════════════════════════════════════════════════

@app.get("/api/status")
def get_status():
    """返回系统整体状态"""
    _require_queue()
    stats = _task_queue.get_statistics()
    from src.config import get_okp_config, get_cookie_status
    okp_cfg = get_okp_config()
    cookie_status = get_cookie_status()
    return {
        "ok": True,
        "queue_size": _task_queue.queue_size(),
        "worker_running": _worker is not None and getattr(_worker, "_running", False),
        "watch_dir": str(WATCH_DIR()),
        "stats": stats,
        "uptime_ts": datetime.now().isoformat(),
        "okp_configured": bool(okp_cfg.get("executable")) or bool(okp_cfg.get("cookie_path")) or bool(okp_cfg.get("setting_path")),
        "okp_executable": okp_cfg.get("executable"),
        "auto_confirm": okp_cfg.get("auto_confirm", True),
        "preview_mode": okp_cfg.get("preview_only", False),
        "cookie_configured": cookie_status["configured"],
        "cookie_exists": cookie_status["exists"],
        "cookie_path": cookie_status.get("resolved_path") or cookie_status.get("path"),
    }


# ══════════════════════════════════════════════════════════════════════
#  路由：任务列表 / 详情
# ══════════════════════════════════════════════════════════════════════

@app.get("/api/tasks")
def list_tasks(status: Optional[str] = None, limit: int = 200, offset: int = 0):
    """获取任务列表"""
    _require_queue()
    all_tasks = list(_task_queue.get_all_tasks().values())
    all_tasks.sort(key=lambda t: t.updated_at, reverse=True)

    if status:
        try:
            filter_status = TaskStatus(status)
            all_tasks = [t for t in all_tasks if t.status == filter_status]
        except ValueError:
            pass

    total = len(all_tasks)
    page = all_tasks[offset: offset + limit]
    return {
        "total": total,
        "offset": offset,
        "limit": limit,
        "tasks": [_task_to_dict(t) for t in page],
    }


@app.get("/api/tasks/{task_id}")
def get_task(task_id: str, full: bool = True):
    """
    获取单个任务详情。
    ?full=true 返回完整元信息 + 发布信息 + OKP 结果（用于发布面板）
    ?full=false 仅返回基本信息（用于列表）
    """
    _require_queue()
    task = _task_queue.persistence.get_task(task_id.upper())
    if not task:
        raise HTTPException(status_code=404, detail=f"任务 {task_id} 不存在")
    return _task_to_dict(task, full=full)


# ══════════════════════════════════════════════════════════════════════
#  路由：发布信息管理
# ══════════════════════════════════════════════════════════════════════

class PublishInfoBody(BaseModel):
    title: str = ""
    subtitle: str = ""
    tags: str = ""
    description: str = ""
    about: str = ""
    poster: str = ""
    group_name: str = ""
    # v2.2 新增
    category: str = ""
    source: str = ""
    video_codec: str = ""
    audio_codec: str = ""
    subtitle_type: str = ""


class OKPRunBody(BaseModel):
    mode: str = "preview"   # "preview" | "publish" | "dry_run"
    auto_confirm: bool = True
    sites: Optional[list[str]] = None   # 选中的站点列表（用于多站点串行发布）


@app.put("/api/tasks/{task_id}/publish_info")
def update_publish_info(task_id: str, body: PublishInfoBody):
    """更新任务的发布信息（标题/标签/简介等）"""
    _require_queue()
    task = _task_queue.persistence.get_task(task_id.upper())
    if not task:
        raise HTTPException(status_code=404, detail=f"任务 {task_id} 不存在")

    task.publish_info = PublishInfo(
        title=body.title,
        subtitle=body.subtitle,
        tags=body.tags,
        description=body.description,
        about=body.about,
        poster=body.poster,
        group_name=body.group_name,
        category=body.category,
        source=body.source,
        video_codec=body.video_codec,
        audio_codec=body.audio_codec,
        subtitle_type=body.subtitle_type,
    )
    _task_queue.persistence.save_task(task)
    logger.info(f"[{task_id}] 发布信息已更新: title={body.title}, tags={body.tags}")

    return {"ok": True, "message": "发布信息已保存"}


@app.post("/api/tasks/{task_id}/preview")
def preview_publish(task_id: str):
    """
    预览任务的发布信息。
    返回 torrent 解析信息 + 发布信息的组合预览（不实际调用 OKP）。
    """
    _require_queue()
    task = _task_queue.persistence.get_task(task_id.upper())
    if not task:
        raise HTTPException(status_code=404, detail=f"任务 {task_id} 不存在")

    # 如果已有 torrent，解析它获取文件列表等信息
    torrent_info = None
    if task.torrent_path and Path(task.torrent_path).exists():
        from src.core.executor_okp import OKPExecutor
        torrent_info = OKPExecutor._parse_torrent_info(task.torrent_path)

    return {
        "ok": True,
        "mode": "preview",
        "publish_info": task.publish_info.to_dict(),
        "video_meta": task.video_meta.to_dict(),
        "torrent_info": torrent_info,
        "message": "预览模式 — 未执行实际发布",
    }


@app.post("/api/tasks/{task_id}/okp_run")
def run_okp_manually(task_id: str, body: OKPRunBody):
    """
    手动触发 OKP 执行（可指定 preview / publish / dry_run 模式）。

    发布面板中的「预览」「发布」按钮均调用此接口：
      mode=preview    → OKP preview_only=True，不实际发布
      mode=dry_run    → OKP preview_only=True，不实际发布
      mode=publish    → 实际执行 OKP 发布（多站点串行）

    body.sites 传入选中的站点列表，实现多站点串行发布。
    """
    import threading as _threading

    _require_queue()
    task = _task_queue.persistence.get_task(task_id.upper())
    if not task:
        raise HTTPException(status_code=404, detail=f"任务 {task_id} 不存在")

    if not task.torrent_path:
        raise HTTPException(status_code=400, detail="该任务尚未生成 Torrent，无法发布")

    if not Path(task.torrent_path).exists():
        raise HTTPException(status_code=400, detail=f"Torrent 文件不存在: {task.torrent_path}")

    preview_only = body.mode in ("preview", "dry_run")
    mode_label = {"preview": "预览模式", "dry_run": "试运行模式", "publish": "正式发布"}[body.mode]
    sites = body.sites or []
    is_multi = len(sites) > 1

    logger.info(f"[{task_id}] 手动触发 OKP — 模式: {mode_label}, sites={sites}, auto_confirm={body.auto_confirm}")

    def _do_run():
        try:
            from src.core.executor_okp import OKPExecutor
            from src.config import get_okp_config
            okp_cfg = get_okp_config()
            okp_path = okp_cfg.get("executable") or get_config("okp_path")
            setting_path = okp_cfg.get("setting_path") or get_config("okp_setting_path")
            cookies_path = okp_cfg.get("cookie_path") or get_config("okp_cookies_path")
            timeout = okp_cfg.get("timeout") or get_config("okp_timeout", 300)

            # ── 多站点串行发布 ──────────────────────────────────────────────
            if is_multi and not preview_only:
                site_results = []
                all_success = True

                for i, site in enumerate(sites):
                    logger.info(f"[{task_id}] === 正在发布站点 [{i+1}/{len(sites)}]: {site} ===")
                    task.update_status(TaskStatus.UPLOADING, f"发布 {site}中 ({i+1}/{len(sites)})...")
                    _task_queue.persistence.save_task(task)

                    result = OKPExecutor.run_okp_upload(
                        torrent_path=task.torrent_path,
                        okp_path=okp_path,
                        setting_path=setting_path,
                        cookies_path=cookies_path,
                        timeout=timeout,
                        auto_confirm=body.auto_confirm,
                        preview_only=False,
                    )

                    site_ok = result.get("success", False)
                    site_results.append({"site": site, "success": site_ok, "error": result.get("error")})
                    if not site_ok:
                        all_success = False
                        logger.warning(f"[{task_id}] 站点 {site} 发布失败: {result.get('error')}")

                # 汇总结果
                failed_sites = [r for r in site_results if not r["success"]]
                if all_success:
                    task.update_status(TaskStatus.SUCCESS)
                    summary = f"全部 {len(sites)} 个站点发布成功"
                else:
                    task.update_status(TaskStatus.FAILED, f"{len(failed_sites)}/{len(sites)} 站点失败")
                    summary = f"失败站点: {', '.join(r['site'] for r in failed_sites)}"

                task.okp_result = OKPResult(
                    mode="multi_site",
                    success=all_success,
                    returncode=0,
                    stdout=json.dumps(site_results, ensure_ascii=False),
                    stderr="",
                    error=summary if failed_sites else None,
                    command="",
                )
                _task_queue.persistence.save_task(task)
                logger.info(f"[{task_id}] 多站点发布完成: {summary}")

            # ── 单站点 / 预览模式 ───────────────────────────────────────────
            else:
                status_label = f"OKP {mode_label}" + (f" ({sites[0]})" if sites else "")
                task.update_status(TaskStatus.UPLOADING, f"{status_label}中...")
                _task_queue.persistence.save_task(task)

                result = OKPExecutor.run_okp_upload(
                    torrent_path=task.torrent_path,
                    okp_path=okp_path,
                    setting_path=setting_path,
                    cookies_path=cookies_path,
                    timeout=timeout,
                    auto_confirm=body.auto_confirm,
                    preview_only=preview_only,
                )

                task.okp_result = OKPResult(
                    mode=result.get("mode", body.mode),
                    success=result.get("success", False),
                    returncode=result.get("returncode", 0),
                    stdout=result.get("stdout", ""),
                    stderr=result.get("stderr", ""),
                    error=result.get("error"),
                    command=result.get("command", ""),
                )

                if result.get("success"):
                    task.update_status(TaskStatus.SUCCESS)
                else:
                    task.update_status(TaskStatus.FAILED, result.get("error") or "OKP 执行失败")

                _task_queue.persistence.save_task(task)
                logger.info(f"[{task_id}] OKP {mode_label}完成: success={result.get('success')}")

        except Exception as e:
            logger.error(f"[{task_id}] OKP 执行异常: {e}", exc_info=True)
            task.okp_result = OKPResult(
                mode="exception",
                success=False,
                returncode=-1,
                stdout="",
                stderr="",
                error=str(e),
                command="",
            )
            task.update_status(TaskStatus.PERMANENT_FAILED, str(e))
            _task_queue.persistence.save_task(task)

    t = _threading.Thread(target=_do_run, daemon=True)
    t.start()

    return {
        "ok": True,
        "message": f"OKP {mode_label}已启动（{len(sites) if is_multi else 1}个站点）",
        "mode": body.mode,
        "preview_only": preview_only,
        "sites": sites,
    }


@app.get("/api/tasks/{task_id}/autofill")
def autofill_task(task_id: str):
    """
    自动填充任务的发布信息。
    从视频文件的文件名 + 视频元数据中智能解析并填充 PublishInfo 字段。
    前端「✨ 自动填充」按钮调用此接口。
    """
    import traceback, re
    from pathlib import Path as _Path

    _require_queue()
    task = _task_queue.persistence.get_task(task_id.upper())
    if not task:
        raise HTTPException(status_code=404, detail=f"任务 {task_id} 不存在")

    try:
        video_path = Path(task.video_path)
        filename = video_path.stem

        fills = {}
        sources = {}

        # ── 1. VideoMeta 技术参数 ──
        vm = task.video_meta
        if vm is not None:
            if getattr(vm, 'resolution', None):
                fills["resolution"] = vm.resolution; sources["resolution"] = "video_meta"
            if getattr(vm, 'codec', None):
                fills["video_codec"] = vm.codec; sources["video_codec"] = "video_meta"

        # ── 2. 文件名正则解析 ──
        fn = filename

        # 发布组名
        group_match = re.search(r'[[(]([A-Za-z0-9&_.\- ]{2,30})[)\]]', fn)
        if group_match:
            gname = group_match.group(1).strip()
            if gname and not re.match(
                r'^(1080|720|2160|4K|HEVC|H264|H265|AVC|VP9|AV1|AAC|FLAC|AC3'
                r'|DTS|WEB|BD|BluRay|TV|DVD|Hi10P|HDR|SDR)$', gname, re.I):
                fills["group_name"] = gname; sources["group_name"] = "filename_regex"

        # 来源检测
        for pat, sv in [("WEB-DL","WEB"),("WEB","Web"),("BDRip","BD"),("BDrip","BD"),
                        ("BluRay","BD"),("BDMV","BD"),("TVRip","TV")]:
            if re.search(pat, fn, re.I): fills["source"] = sv; break

        # 分辨率
        for pat, val in [(r'\b2160[pP]|4K\b','4K'),(r'\b1080[pP]\b','1080p'),
                         (r'\b720[pP]\b','720p'),(r'\b480[pPiI]\b','480p')]:
            if re.search(pat, fn): fills["resolution"] = val; sources["resolution"] = "filename"; break

        # 视频编码
        for pat, val in [(r'\bHEVC\b','H265'),(r'\bh\.?265\b','H265'),
                         (r'\bAVC\b','H264'),(r'\bh\.?264\b','H264')]:
            if re.search(pat, fn, re.I): fills["video_codec"] = val.split('(')[0]; break

        # 音频编码
        for pat, val in [(r'\bFLAC\b','FLAC'),(r'\bAAC\b','AAC'),
                         (r'\bAC3\b','AC3'),(r'\bDTS(?:[-\s]?HD)?\b','DTS')]:
            if re.search(pat, fn, re.I): fills["audio_codec"] = val; break

        # 字幕类型
        for pat, val in [(r'(?:内嵌|Internal)','内嵌'),(r'(?:外挂|External)','外挂')]:
            if re.search(pat, fn, re.I): fills["subtitle_type"] = val; break

        # 分类启发式
        if any(re.search(kw, fn, re.I) for kw in ['anime','EP','Episode']):
            fills["category"] = "Anime"
        elif any(re.search(kw, fn, re.I) for kw in ['music','PV','MV','OP','ED']):
            fills["category"] = "Music"

        # 标题清理
        title_candidate = fn
        if "group_name" in fills:
            title_candidate = re.sub(r'[[]' + re.escape(fills["group_name"]) + r'[\]]', '', title_candidate).strip()
        title_candidate = re.sub(r'\s*[\[\(](?:1080p|720p|[hx]\.?26[45]|hevc|aac|flac'
                                r'|ac3|web[- ]?(?:dl)?|bd(?:rip)?|hi10p|hdr|dovi'
                                r'|internal|ep\d+)[\]\)]', '', title_candidate,
                                flags=re.IGNORECASE).strip()
        title_candidate = re.sub(r'^[\s\-\._]+|[\s\-\._]+$', '', title_candidate)
        if len(title_candidate) > 2: fills["title"] = title_candidate

        # Tags 默认值
        if "category" in fills and "tags" not in fills:
            fills["tags"] = fills["category"]

        # ── 3. 应用到 Task（只覆盖空字段）──
        updated_fields = []
        pi = task.publish_info
        for field, value in fills.items():
            if hasattr(pi, field):
                current_val = getattr(pi, field) or ""
                if not str(current_val).strip():
                    setattr(pi, field, value)
                    updated_fields.append(field)

        if updated_fields:
            _task_queue.persistence.save_task(task)
            logger.info(f"[{task_id}] AutoFill 填充 {len(updated_fields)} 字段: {updated_fields}")

        return {
            "ok": True,
            "filled_fields": updated_fields,
            "fills": fills,
            "sources": sources,
            "message": f"填充了 {len(updated_fields)} 个字段" if updated_fields else "所有字段已有值",
        }

    except Exception as e:
        logger.error(f"[{task_id}] AutoFill 异常: {e}\n{traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=f"AutoFill 错误: {e}")


# ══════════════════════════════════════════════════════════════════════
#  路由：任务操作（原有）
# ══════════════════════════════════════════════════════════════════════

@app.post("/api/tasks/{task_id}/retry")
def retry_task(task_id: str):
    """手动重试某个任务"""
    _require_queue()
    task = _task_queue.persistence.get_task(task_id.upper())
    if not task:
        raise HTTPException(status_code=404, detail=f"任务 {task_id} 不存在")
    if task.status == TaskStatus.SUCCESS:
        raise HTTPException(status_code=400, detail="任务已成功，无需重试")

    task.retry_count = 0
    task.update_status(TaskStatus.FAILED, "手动触发重试")
    _task_queue.persistence.save_task(task)
    _task_queue._queue.put(task)

    logger.info(f"[{task.id}] 手动触发重试")
    return {"ok": True, "message": f"任务 {task_id} 已重新加入队列"}


@app.delete("/api/tasks/{task_id}")
def delete_task(task_id: str):
    """删除单个任务记录"""
    _require_queue()
    task = _task_queue.persistence.get_task(task_id.upper())
    if not task:
        raise HTTPException(status_code=404, detail=f"任务 {task_id} 不存在")

    _task_queue.persistence.delete_task(task_id.upper())
    logger.info(f"[{task_id}] 任务记录已删除（手动）")
    return {"ok": True, "message": f"任务 {task_id} 已删除"}


# ══════════════════════════════════════════════════════════════════════
#  路由：种子上传
# ══════════════════════════════════════════════════════════════════════

@app.post("/api/tasks/{task_id}/upload_torrent")
def upload_torrent_file(task_id: str, file: UploadFile = File(...)):
    """
    上传 .torrent 文件到任务。
    文件保存在 data/torrents/ 目录下。
    """
    _require_queue()
    task = _task_queue.persistence.get_task(task_id.upper())
    if not task:
        raise HTTPException(status_code=404, detail=f"任务 {task_id} 不存在")

    if not file.filename.endswith(".torrent"):
        raise HTTPException(status_code=400, detail="只能上传 .torrent 文件")

    # 保存到 data/torrents/
    out_dir = OUTPUT_TORRENT_DIR()
    Path(out_dir).mkdir(parents=True, exist_ok=True)
    safe_name = f"{task_id}_{uuid.uuid4().hex[:6]}_{file.filename}"
    out_path = Path(out_dir) / safe_name

    try:
        content = file.file.read()
        # 简单验证：torrent 文件以 "d8:" 开头（bencode 格式）
        if not content.startswith(b"d8:"):
            raise HTTPException(status_code=400, detail="无效的 torrent 文件格式")
        with open(out_path, "wb") as f:
            f.write(content)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"保存种子文件失败: {e}")

    task.torrent_path = str(out_path)

    # 解析种子信息
    t_info = OKPExecutor._parse_torrent_info(str(out_path))
    if t_info:
        task.torrent_meta = TorrentMeta(
            name=t_info.get("name", ""),
            size=t_info.get("size", 0),
            file_count=len(t_info.get("files", [])),
            files=[{"name": f, "size": 0} for f in t_info.get("files", [])[:20]],
            tracker_count=len(t_info.get("trackers", [])),
            tracker_sample=t_info.get("trackers", [])[:5],
        )

    # 如果任务还处于 NEW 状态，跳过 Torrent 生成直接进入待发布
    if task.status == TaskStatus.NEW:
        task.update_status(TaskStatus.TORRENT_CREATED)

    _task_queue.persistence.save_task(task)
    logger.info(f"[{task_id}] 种子上传成功: {out_path.name} ({len(content)} bytes)")

    return {
        "ok": True,
        "message": f"种子文件已上传: {file.filename}",
        "torrent_path": str(out_path),
        "torrent_meta": task.torrent_meta.to_dict() if t_info else None,
    }


class ManualTriggerBody(BaseModel):
    video_path: str
    publish_info: Optional[PublishInfoBody] = None  # 可选地同时传入发布信息


@app.post("/api/tasks/trigger")
def trigger_task(body: ManualTriggerBody):
    """手动触发处理一个视频文件，可附带发布信息"""
    _require_queue()
    video_path = Path(body.video_path)
    if not video_path.exists():
        raise HTTPException(status_code=400, detail=f"文件不存在: {body.video_path}")

    task_id = Task.generate_id(str(video_path.resolve()))
    existing = _task_queue.persistence.get_task(task_id)
    if existing and existing.status == TaskStatus.SUCCESS:
        raise HTTPException(status_code=400, detail="该文件已成功发布，若要重新发布请先删除旧记录")

    task = Task(
        id=task_id,
        video_path=str(video_path.resolve()),
    )

    # 如果提供了发布信息，直接设置
    if body.publish_info:
        pi = body.publish_info
        task.publish_info = PublishInfo(
            title=pi.title or video_path.stem,
            subtitle=pi.subtitle,
            tags=pi.tags,
            description=pi.description,
            about=pi.about,
            poster=pi.poster,
            group_name=pi.group_name,
            category=pi.category,
            source=pi.source,
            video_codec=pi.video_codec,
            audio_codec=pi.audio_codec,
            subtitle_type=pi.subtitle_type,
        )

    _task_queue.enqueue(task)
    logger.info(f"[{task_id}] 手动触发任务 - 文件: {video_path.name}")
    return {"ok": True, "task_id": task_id, "message": "任务已加入队列"}


@app.post("/api/tasks/clear_failed")
def clear_failed():
    """清除所有永久失败的任务记录"""
    _require_queue()
    all_tasks = _task_queue.persistence.get_all_tasks()
    cleared = 0
    for tid, t in all_tasks.items():
        if t.status == TaskStatus.PERMANENT_FAILED:
            _task_queue.persistence.delete_task(tid)
            cleared += 1
    logger.info(f"清除 {cleared} 个永久失败任务记录")
    return {"ok": True, "cleared": cleared}


# ══════════════════════════════════════════════════════════════════════
#  路由：OKP 输出查看
# ══════════════════════════════════════════════════════════════════════

@app.get("/api/tasks/{task_id}/okp_output")
def get_okp_output(task_id: str):
    """
    获取某个任务的 OKP 执行输出（完整 stdout/stderr）。
    用于前端日志查看器展示 OKP 原始输出。
    """
    _require_queue()
    task = _task_queue.persistence.get_task(task_id.upper())
    if not task:
        raise HTTPException(status_code=404, detail=f"任务 {task_id} 不存在")

    if not task.okp_result:
        return {"has_output": False, "stdout": "", "stderr": "", "error": "该任务尚无 OKP 执行记录"}

    return {
        "has_output": True,
        "mode": task.okp_result.mode,
        "success": task.okp_result.success,
        "returncode": task.okp_result.returncode,
        "stdout": task.okp_result.stdout,
        "stderr": task.okp_result.stderr,
        "error": task.okp_result.error,
        "command": task.okp_result.command,
    }


# ══════════════════════════════════════════════════════════════════════
#  路由：日志
# ══════════════════════════════════════════════════════════════════════

@app.get("/api/logs")
def get_logs(limit: int = 200, level: Optional[str] = None):
    """获取最近的日志条目"""
    with _log_lock:
        logs = list(_log_buffer)

    if level:
        level_upper = level.upper()
        logs = [l for l in logs if l["level"] == level_upper]

    return {"total": len(logs), "logs": logs[-limit:]}


@app.get("/api/logs/stream")
async def stream_logs(request: Request):
    """SSE 实时日志流"""
    client_queue = asyncio.Queue()

    sync_q = __import__("queue").Queue()
    _log_sse_clients.append(sync_q)

    async def event_generator():
        loop = asyncio.get_event_loop()
        try:
            with _log_lock:
                recent = list(_log_buffer)[-50:]
            for entry in recent:
                yield f"data: {json.dumps(entry, ensure_ascii=False)}\n\n"

            while True:
                if await request.is_disconnected():
                    break
                try:
                    entry = await loop.run_in_executor(None, lambda: sync_q.get(timeout=0.5))
                    yield f"data: {json.dumps(entry, ensure_ascii=False)}\n\n"
                except Exception:
                    yield ": heartbeat\n\n"
        finally:
            if sync_q in _log_sse_clients:
                _log_sse_clients.remove(sync_q)

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@app.get("/api/logs/file")
def get_log_file(lines: int = 500):
    """读取日志文件尾部"""
    from src.config import LOG_FILE
    log_path = LOG_FILE()
    if not Path(log_path).exists():
        return {"lines": []}
    try:
        with open(log_path, "r", encoding="utf-8", errors="replace") as f:
            all_lines = f.readlines()
        tail = all_lines[-lines:]
        return {"lines": [l.rstrip() for l in tail]}
    except Exception as e:
        return {"lines": [], "error": str(e)}


# ══════════════════════════════════════════════════════════════════════
#  路由：配置
# ══════════════════════════════════════════════════════════════════════

@app.get("/api/config")
def get_web_config():
    """返回当前配置（脱敏）"""
    from src.config import load_config
    cfg = load_config()
    safe_cfg = {}
    for k, v in cfg.items():
        if isinstance(v, (str, int, float, bool, list)):
            safe_cfg[k] = v
        elif v is None:
            safe_cfg[k] = None
    return safe_cfg


# ══════════════════════════════════════════════════════════════════════
#  路由：站点配置（从 setting.toml / config.yaml 推断）
# ══════════════════════════════════════════════════════════════════════

@app.get("/api/sites")
def get_site_status():
    """
    返回可配置的站点列表和各站点的状态。
    基于 OKP 支持的站点 + 当前 cookies/setting 的可用性推断。
    """
    _require_queue()

    sites = [
        {"id": "nyaa", "name": "Nyaa.si", "url": "https://nyaa.si"},
        {"id": "dmhy", "name": "动漫花园", "url": "https://share.dmhy.org"},
        {"id": "acgrip", "name": "ACG.RIP", "url": "https://acg.rip"},
        {"id": "bangumi", "name": "萌番组", "url": "https://bangumi.moe"},
        {"id": "acgnx_asia", "name": "AcgnX Asia", "url": "https://share.acgnx.se"},
        {"id": "acgnx_global", "name": "AcgnX Global", "url": "https://www.acgnx.se"},
    ]

    from src.config import get_okp_config, get_cookie_status
    okp_cfg = get_okp_config()
    cookie_status = get_cookie_status()
    has_cookies = cookie_status["exists"]
    setting_path = okp_cfg.get("setting_path")
    has_setting = bool(setting_path and Path(setting_path).exists()) if setting_path else False

    for site in sites:
        site["configured"] = has_cookies or has_setting
        site["cookies_ok"] = has_cookies
        site["setting_ok"] = has_setting

    return {
        "sites": sites,
        "global_cookies_ok": has_cookies,
        "global_setting_ok": has_setting,
        "cookies_path": cookie_status.get("resolved_path") or cookie_status.get("path"),
        "setting_path": str(setting_path) if setting_path else None,
        "okp_executable": okp_cfg.get("executable"),
        "okp_working_dir": okp_cfg.get("working_dir"),
    }


@app.get("/api/cookie_status")
def get_cookie_status_api():
    """
    返回 Cookie 文件的详细状态信息。
    用于前端面板显示 Cookie 配置状态。
    """
    from src.config import get_cookie_status, get_okp_config
    cookie_status = get_cookie_status()
    okp_cfg = get_okp_config()
    cookie_status["okp_executable"] = okp_cfg.get("executable")
    cookie_status["okp_working_dir"] = okp_cfg.get("working_dir")
    return cookie_status


# ══════════════════════════════════════════════════════════════════════
#  路由：模板系统
# ══════════════════════════════════════════════════════════════════════

class TemplateBody(BaseModel):
    name: str
    description: str = ""
    category: str = ""
    publish_info: Optional[PublishInfoBody] = None


@app.get("/api/templates")
def list_templates():
    """返回所有已保存的发布模板"""
    templates = _load_templates()
    return {"ok": True, "templates": list(templates.values())}


@app.post("/api/templates")
def create_template(body: TemplateBody):
    """创建新模板（从当前表单保存）"""
    with _TEMPLATE_LOCK:
        templates = _load_templates()
        tid = uuid.uuid4().hex[:8]
        template = {
            "id": tid,
            "name": body.name,
            "description": body.description,
            "category": body.category,
            "publish_info": body.publish_info.model_dump() if body.publish_info else {},
            "created_at": datetime.now().isoformat(),
        }
        templates[tid] = template
        _save_templates(templates)
    logger.info(f"[模板] 已创建: {body.name} ({tid})")
    return {"ok": True, "template": template}


@app.put("/api/templates/{template_id}")
def update_template(template_id: str, body: TemplateBody):
    """更新指定模板"""
    with _TEMPLATE_LOCK:
        templates = _load_templates()
        if template_id not in templates:
            raise HTTPException(status_code=404, detail=f"模板 {template_id} 不存在")
        templates[template_id].update({
            "name": body.name,
            "description": body.description,
            "category": body.category,
            "publish_info": body.publish_info.model_dump() if body.publish_info else {},
        })
        _save_templates(templates)
        tmpl = templates[template_id]
    return {"ok": True, "template": tmpl}


@app.delete("/api/templates/{template_id}")
def delete_template(template_id: str):
    """删除指定模板"""
    with _TEMPLATE_LOCK:
        templates = _load_templates()
        if template_id not in templates:
            raise HTTPException(status_code=404, detail=f"模板 {template_id} 不存在")
        name = templates[template_id]["name"]
        del templates[template_id]
        _save_templates(templates)
    return {"ok": True, "message": f"模板 '{name}' 已删除"}


@app.post("/api/tasks/{task_id}/apply_template/{template_id}")
def apply_template(task_id: str, template_id: str):
    """
    将指定模板的应用到任务（填充发布信息，只覆盖空字段）。
    """
    _require_queue()
    task = _task_queue.persistence.get_task(task_id.upper())
    if not task:
        raise HTTPException(status_code=404, detail=f"任务 {task_id} 不存在")

    templates = _load_templates()
    if template_id not in templates:
        raise HTTPException(status_code=404, detail=f"模板 {template_id} 不存在")

    tmpl = templates[template_id]
    pi_data = tmpl.get("publish_info", {})
    pi = PublishInfo(
        title=pi_data.get("title", ""),
        subtitle=pi_data.get("subtitle", ""),
        tags=pi_data.get("tags", ""),
        description=pi_data.get("description", ""),
        about=pi_data.get("about", ""),
        poster=pi_data.get("poster", ""),
        group_name=pi_data.get("group_name", ""),
        category=pi_data.get("category", ""),
        source=pi_data.get("source", ""),
        video_codec=pi_data.get("video_codec", ""),
        audio_codec=pi_data.get("audio_codec", ""),
        subtitle_type=pi_data.get("subtitle_type", ""),
    )

    # 只填充空字段
    current = task.publish_info
    filled = []
    for field in ["title", "subtitle", "tags", "description", "about", "poster",
                  "group_name", "category", "source", "video_codec", "audio_codec", "subtitle_type"]:
        cur_val = getattr(current, field) or ""
        if not str(cur_val).strip():
            new_val = getattr(pi, field) or ""
            if new_val:
                setattr(current, field, new_val)
                filled.append(field)

    _task_queue.persistence.save_task(task)
    logger.info(f"[{task_id}] 应用模板 '{tmpl['name']}': 填充了 {filled}")
    return {
        "ok": True,
        "message": f"模板 '{tmpl['name']}' 已应用，填充了 {len(filled)} 个字段",
        "filled_fields": filled,
    }


# ══════════════════════════════════════════════════════════════════════
#  路由：前端页面
# ══════════════════════════════════════════════════════════════════════

@app.get("/", response_class=HTMLResponse)
def index():
    """返回 Web 面板主页"""
    html_path = Path(__file__).parent / "panel.html"
    if html_path.exists():
        return HTMLResponse(content=html_path.read_text(encoding="utf-8"))
    return HTMLResponse(content="<h1>面板文件不存在</h1>", status_code=500)
