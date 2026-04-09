import time
import threading
from pathlib import Path
from datetime import datetime
from src.logger import setup_logger
from src.core.task_model import (
    Task, TaskStatus, PublishInfo, VideoMeta,
    TorrentMeta, OKPResult, PublishConfig
)
from src.core.task_queue import TaskQueue
from src.core.scanner import Scanner
from src.core.probe import Probe
from src.core.normalizer import Normalizer
from src.core.torrent_builder import TorrentBuilder
from src.core.executor_okp import OKPExecutor
from src.config import TRACKER_URLS, OUTPUT_TORRENT_DIR, get_config

logger = setup_logger(__name__)


class TaskWorker:

    def __init__(self, task_queue):
        self.task_queue = task_queue
        self.scanner = Scanner()
        self.probe = Probe()
        self.normalizer = Normalizer()
        self._running = False
        self._stop_event = threading.Event()

    def start(self):
        self._running = True
        self._stop_event.clear()

        logger.info("=" * 60)
        logger.info("🚀 Worker 启动 - 开始处理任务队列 (v3.0 Enhanced)")
        logger.info("=" * 60)

        worker_thread = threading.Thread(target=self._run_loop, daemon=True)
        worker_thread.start()

        return worker_thread

    def stop(self):
        logger.info("⏹️  正在停止 Worker...")
        self._running = False
        self._stop_event.set()

    def _run_loop(self):
        while self._running:
            try:
                task = self.task_queue.dequeue(block=True, timeout=1.0)

                if task is None:
                    continue

                if self._stop_event.is_set():
                    break

                self._process_task(task)
                self.task_queue.task_done()

            except Exception as e:
                logger.error(f"Worker 循环异常: {e}", exc_info=True)
                time.sleep(1)

        logger.info("🛑 Worker 已停止")

    def _process_task(self, task):
        task_id = task.id

        logger.info("")
        logger.info("╔════════════════════════════════════════════════╗")
        logger.info(f"║  [{task_id}] 🎬 开始处理任务                      ║")
        logger.info("╚════════════════════════════════════════════════╝")
        logger.info(f"  文件: {task.video_path}")
        logger.info(f"  初始状态: {task.status.value} (v3: {TaskStatus.to_v3(task.status)})")
        logger.info("")

        current_status = task.status

        # v3.0: 兼容 NEW 和 PENDING 状态
        if current_status in [TaskStatus.NEW, TaskStatus.PENDING]:
            success = self._handle_new_task(task)
            if not success:
                return

        # v3.0: 兼容 TORRENT_CREATED 和 READY 状态
        if task.status in [TaskStatus.TORRENT_CREATED, TaskStatus.READY] or \
           (success and current_status in [TaskStatus.NEW, TaskStatus.PENDING]):
            self._handle_upload(task)
    
    def _handle_new_task(self, task):
        task_id = task.id

        # v3.0: 使用状态机方法
        logger.info(f"[{task_id}] 状态转换: {TaskStatus.to_v3(task.status)} → torrent_creating")
        try:
            task.transition_to(TaskStatus.TORRENT_CREATING)
        except ValueError as e:
            # 兼容旧逻辑
            task.update_status(TaskStatus.TORRENT_CREATING)
        self.task_queue.persistence.save_task(task)

        video_path = Path(task.video_path)

        if not video_path.exists():
            error_msg = f"视频文件不存在: {video_path}"
            logger.error(f"[{task_id}] ❌ {error_msg}")
            try:
                task.transition_to(TaskStatus.PERMANENT_FAILED, error_msg)
            except ValueError:
                task.update_status(TaskStatus.PERMANENT_FAILED, error_msg)
            self.task_queue.persistence.save_task(task)
            return False

        if self.scanner.is_processed(video_path):
            logger.info(f"[{task_id}] 文件已处理过，跳过")
            try:
                task.transition_to(TaskStatus.SUCCESS, "文件已处理")
            except ValueError:
                task.update_status(TaskStatus.SUCCESS, "文件已处理")
            self.task_queue.persistence.save_task(task)
            return False

        logger.info(f"[{task_id}] 🔍 提取视频信息...")
        raw_info = self.probe.get_video_info(video_path)
        if not raw_info:
            error_msg = "无法提取视频信息"
            logger.error(f"[{task_id}] ❌ {error_msg}")
            try:
                task.transition_to(TaskStatus.PERMANENT_FAILED, error_msg)
            except ValueError:
                task.update_status(TaskStatus.PERMANENT_FAILED, error_msg)
            self.task_queue.persistence.save_task(task)
            return False

        normalized = self.normalizer.normalize(video_path, raw_info)

        # 填充视频元信息
        task.video_meta = VideoMeta(
            width=raw_info["width"],
            height=raw_info["height"],
            codec=normalized["codec"],
            resolution=normalized["resolution"],
            duration_seconds=normalized["duration"],
            file_size=normalized["size"],
        )

        # 预填发布标题（文件名作为默认 title）
        task.publish_info = PublishInfo(title=normalized["title"])
        self.task_queue.persistence.save_task(task)

        logger.info(f"[{task_id}] 📦 生成 Torrent...")
        tracker_urls = TRACKER_URLS()
        output_dir = str(OUTPUT_TORRENT_DIR())

        torrent_path = TorrentBuilder.create_torrent(
            file_path=video_path,
            tracker_urls=tracker_urls,
            output_dir=output_dir
        )

        if not torrent_path:
            error_msg = "Torrent 生成失败"
            logger.error(f"[{task_id}] ❌ {error_msg}")
            try:
                task.transition_to(TaskStatus.PERMANENT_FAILED, error_msg)
            except ValueError:
                task.update_status(TaskStatus.PERMANENT_FAILED, error_msg)
            self.task_queue.persistence.save_task(task)
            return False

        task.torrent_path = str(torrent_path)

        # 填充 Torrent 元信息
        t_info = OKPExecutor._parse_torrent_info(str(torrent_path))
        if t_info:
            task.torrent_meta = TorrentMeta(
                name=t_info.get('name', ''),
                size=t_info.get('size', 0),
                file_count=len(t_info.get('files', [])),
                files=[{'name': f.replace('  📄 ', '').split(' (')[0] if ' 📄 ' in f else f,
                        'size': 0}
                       for f in t_info.get('files', [])[:20]],
                tracker_count=len(t_info.get('trackers', [])),
                tracker_sample=t_info.get('trackers', [])[:5],
            )

        # v3.0: 使用状态机转换到 READY/TORRENT_CREATED
        try:
            task.transition_to(TaskStatus.TORRENT_CREATED)
        except ValueError:
            task.update_status(TaskStatus.TORRENT_CREATED)
        self.task_queue.persistence.save_task(task)

        logger.info(f"[{task_id}] ✅ Torrent 已生成: {torrent_path}")
        self.scanner.mark_processed(video_path)

        return True
    
    def _handle_upload(self, task):
        task_id = task.id

        # v3.0: 使用状态机方法
        logger.info(f"[{task_id}] 状态转换: {TaskStatus.to_v3(task.status)} → uploading")
        try:
            task.transition_to(TaskStatus.UPLOADING)
        except ValueError:
            task.update_status(TaskStatus.UPLOADING)
        self.task_queue.persistence.save_task(task)

        from src.config import get_okp_config
        okp_cfg = get_okp_config()
        okp_path = okp_cfg.get("executable") or get_config("okp_path")
        setting_path = okp_cfg.get("setting_path") or get_config("okp_setting_path")
        cookies_path = okp_cfg.get("cookie_path") or get_config("okp_cookies_path")
        timeout = okp_cfg.get("timeout") or get_config("okp_timeout", 300)

        auto_confirm = getattr(task, 'publish_config', None)
        if auto_confirm and hasattr(auto_confirm, 'auto_confirm'):
            auto_confirm = auto_confirm.auto_confirm
        else:
            auto_confirm = okp_cfg.get("auto_confirm", True)

        preview_only = okp_cfg.get("preview_only", False)

        logger.info(f"[{task_id}] 🚀 调用 OKP 发布...")
        logger.info(f"[{task_id}]    重试次数: {task.retry_count}/{task.max_retries}")

        result = OKPExecutor.run_okp_upload(
            torrent_path=task.torrent_path,
            okp_path=okp_path,
            setting_path=setting_path,
            cookies_path=cookies_path,
            timeout=timeout,
            auto_confirm=auto_confirm,
            preview_only=preview_only
        )

        # v3.0: 增强 OKPResult（包含新字段）
        task.okp_result = OKPResult(
            mode=result.get('mode', 'unknown'),
            success=result.get('success', False),
            returncode=result.get('returncode', 0),
            stdout=result.get('stdout', ''),
            stderr=result.get('stderr', ''),
            error=result.get('error'),
            command=result.get('command', ''),
            # v3.0 新字段
            executed_at=datetime.now().isoformat(),
            site_results=result.get('site_results'),
        )

        if result.get("success") or result.get("mode") == "preview":
            # v3.0: 使用状态机方法
            try:
                task.transition_to(TaskStatus.SUCCESS)
            except ValueError:
                task.update_status(TaskStatus.SUCCESS)
            self.task_queue.persistence.save_task(task)

            mode = result.get('mode', 'unknown')
            logger.info(f"[{task_id}] ✅ 任务完成 - 模式: {mode}")
            logger.info("")
            logger.info("╔════════════════════════════════════════════════╗")
            logger.info(f"║  [{task_id}] ✅ 任务成功完成                       ║")
            logger.info("╚════════════════════════════════════════════════╝")
        else:
            error_msg = result.get('error', '未知错误')

            # v3.0: 尝试转换到 RETRYING，否则 FAILED
            if task.can_retry():
                try:
                    task.transition_to(TaskStatus.RETRYING, error_msg)
                except ValueError:
                    task.update_status(TaskStatus.FAILED, error_msg)
                    task.increment_retry()
            else:
                try:
                    task.transition_to(TaskStatus.FAILED, error_msg)
                except ValueError:
                    task.update_status(TaskStatus.FAILED, error_msg)
                task.increment_retry()

            self.task_queue.persistence.save_task(task)

            logger.warning(f"[{task_id}] ⚠️  任务失败")
            logger.warning(f"[{task_id}]    错误: {error_msg}")
            logger.warning(f"[{task_id}]    重试: {task.retry_count}/{task.max_retries}")

            if task.can_retry():
                retry_delay = min(10 * (task.retry_count + 1), 30)
                logger.info(f"[{task_id}] 🔄 将在 {retry_delay}秒 后重试...")
                self.task_queue.requeue_for_retry(task, delay_seconds=retry_delay)
            else:
                # 超过最大重试次数 → 永久失败
                try:
                    task.transition_to(
                        TaskStatus.PERMANENT_FAILED,
                        f"超过最大重试次数 ({task.max_retries})"
                    )
                except ValueError:
                    task.update_status(
                        TaskStatus.PERMANENT_FAILED,
                        f"超过最大重试次数 ({task.max_retries})"
                    )
                self.task_queue.persistence.save_task(task)
                logger.error(f"[{task_id}] ❌ 任务永久失败")
                logger.error("")
                logger.error("╔════════════════════════════════════════════════╗")
                logger.error(f"║  [{task_id}] ❌ 任务永久失败                       ║")
                logger.error("╚════════════════════════════════════════════════╝")
    
    def print_statistics(self):
        stats = self.task_queue.get_statistics()
        
        logger.info("")
        logger.info("📊 任务统计:")
        logger.info("-" * 40)
        
        status_labels = {
            'new': '🆕 新任务',
            'torrent_creating': '📦 生成Torrent中',
            'torrent_created': '✓ Torrent已生成',
            'uploading': '🚀 上传中',
            'success': '✅ 成功',
            'failed': '⚠️  失败（可重试）',
            'permanent_failed': '❌ 永久失败'
        }
        
        for status, count in sorted(stats.items()):
            label = status_labels.get(status, status)
            logger.info(f"  {label}: {count}")
        
        total = sum(stats.values())
        logger.info("-" * 40)
        logger.info(f"  📋 总计: {total} 个任务")
        logger.info("")