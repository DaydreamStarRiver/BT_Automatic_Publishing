
from src.logger import setup_logger
from src.config import (
    TRACKER_URLS,
    OUTPUT_TORRENT_DIR,
    get_config
)
from src.core.torrent_builder import TorrentBuilder
from src.core.executor_okp import OKPExecutor

logger = setup_logger(__name__)


class Planner:
    @staticmethod
    def process_task(task):
        logger.info("")
        logger.info("╔══════════════════════════════════════════════════╗")
        logger.info("║           🎬 新视频文件检测到 - 开始处理          ║")
        logger.info("╚══════════════════════════════════════════════════╝")
        logger.info("")
        
        logger.info("📹 视频信息:")
        logger.info(f"  文件: {task['title']}")
        logger.info(f"  路径: {task['file_path']}")
        logger.info(f"  分辨率: {task['resolution']}")
        logger.info(f"  编码: {task['codec']}")
        logger.info(f"  时长: {task['duration']}秒 ({task['duration'] // 60}分{task['duration'] % 60}秒)")
        logger.info(f"  大小: {_format_size(task['size'])}")
        logger.info("")
        
        torrent_path = Planner._create_torrent(task)
        if not torrent_path:
            logger.error("❌ Torrent 生成失败，跳过 OKP 处理")
            return
        
        okp_result = Planner._run_okp(torrent_path)
        
        mode = okp_result.get('mode', 'unknown')
        
        if mode == 'preview':
            logger.info("📋 预览模式完成 - 未执行发布")
        elif okp_result["success"]:
            logger.info("✅ 发布任务处理完成")
        else:
            error_msg = okp_result.get('error', '未知错误')
            logger.error(f"❌ 任务处理失败: {error_msg}")
    
    @staticmethod
    def _create_torrent(task):
        logger.info("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
        logger.info("📦 步骤 1/2: 生成 Torrent 文件")
        logger.info("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
        
        file_path = task["file_path"]
        tracker_urls = TRACKER_URLS()
        output_dir = str(OUTPUT_TORRENT_DIR())
        
        torrent_path = TorrentBuilder.create_torrent(
            file_path=file_path,
            tracker_urls=tracker_urls,
            output_dir=output_dir
        )
        
        if torrent_path:
            logger.info(f"✓ Torrent 已生成: {torrent_path}")
        else:
            logger.error("✗ Torrent 生成失败")
        
        return torrent_path
    
    @staticmethod
    def _run_okp(torrent_path):
        logger.info("")
        logger.info("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
        logger.info("🚀 步骤 2/2: 调用 OKP 发布")
        logger.info("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
        
        okp_path = get_config("okp_path")
        setting_path = get_config("okp_setting_path")
        cookies_path = get_config("okp_cookies_path")
        timeout = get_config("okp_timeout", 300)
        auto_confirm = get_config("okp_auto_confirm", True)
        preview_only = get_config("okp_preview_only", False)
        
        result = OKPExecutor.run_okp_upload(
            torrent_path=torrent_path,
            okp_path=okp_path,
            setting_path=setting_path,
            cookies_path=cookies_path,
            timeout=timeout,
            auto_confirm=auto_confirm,
            preview_only=preview_only
        )
        
        return result


def _format_size(size_bytes):
    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if abs(size_bytes) < 1024.0:
            return f"{size_bytes:.2f} {unit}"
        size_bytes /= 1024.0
    return f"{size_bytes:.2f} PB"

