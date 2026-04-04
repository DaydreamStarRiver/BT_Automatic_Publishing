#!/usr/bin/env python3
import signal
import sys
import threading

from src.logger import setup_logger
from src.core.task_queue import TaskQueue
from src.core.task_worker import TaskWorker
from src.core.watcher import Watcher
from src.config import get_config


def _check_web_deps():
    """检查 Web 面板依赖是否可用，返回 (ok, missing_list)"""
    missing = []
    for mod in ["fastapi", "uvicorn"]:
        try:
            __import__(mod)
        except ImportError:
            missing.append(mod)
    return len(missing) == 0, missing


def start_web_server(task_queue, worker):
    """在独立线程中启动 FastAPI Web 面板"""
    logger = setup_logger(__name__)

    ok, missing = _check_web_deps()
    if not ok:
        logger.warning(
            f"⚠️  Web 面板依赖缺失: {', '.join(missing)}。"
            f"当前 Python: {sys.executable}\n"
            f"   请运行: pip install fastapi uvicorn\n"
            f"   或:       pip install -r requirements.txt"
        )
        return

    try:
        import uvicorn
        from src.web.api import app, init_web

        init_web(task_queue, worker)
        host = get_config("web_host", "0.0.0.0")
        port = get_config("web_port", 8080)
        logger.info(f"🌐 Web 面板启动 → http://{host}:{port}")
        uvicorn.run(app, host=host, port=port, log_level="warning")
    except Exception as e:
        logger.error(f"❌ Web 面板启动失败: {e}")


def main():
    logger = setup_logger()
    
    logger.info("")
    logger.info("╔════════════════════════════════════════════════════════════╗")
    logger.info("║     🎬 BT 自动发布系统 v2.1 - Web 面板版                     ║")
    logger.info("╚════════════════════════════════════════════════════════════╝")
    logger.info("")
    logger.info("功能特性:")
    logger.info("  ✅ 任务队列管理")
    logger.info("  ✅ 状态机驱动流程")
    logger.info("  ✅ 自动重试机制")
    logger.info("  ✅ 断点恢复支持")
    logger.info("  ✅ 持久化存储")
    
    # 检查 Web 依赖并显示对应状态
    web_ok, web_missing = _check_web_deps()
    if web_ok:
        logger.info("  ✅ Web 管理面板")
    else:
        logger.info(f"  ⚠️  Web 管理面板（依赖缺失: {', '.join(web_missing)}）")
    
    logger.info("")
    logger.info("按 Ctrl+C 停止程序")
    logger.info("")
    
    task_queue = TaskQueue()
    worker = TaskWorker(task_queue)
    watcher = Watcher(task_queue=task_queue)

    # 启动 Web 面板（独立线程，daemon=True，主进程退出时自动销毁）
    web_enabled = get_config("web_enabled", True)
    if web_enabled and web_ok:
        web_thread = threading.Thread(target=start_web_server, args=(task_queue, worker), daemon=True)
        web_thread.start()
        # 等 1 秒让 uvicorn 就绪，然后打印访问地址
        import time as _time
        _time.sleep(1.5)
        host = get_config("web_host", "0.0.0.0")
        port = get_config("web_port", 8080)
        display_host = "localhost" if host == "0.0.0.0" else host
        logger.info(f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
        logger.info(f"  🌐  Web 面板地址: http://{display_host}:{port}")
        logger.info(f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
        logger.info("")
    elif web_enabled and not web_ok:
        logger.warning(f"⚠️  Web 面板已启用但依赖不足，跳过启动。请先安装: pip install {' '.join(web_missing)}")
    
    def signal_handler(signum, frame):
        logger.info("")
        logger.info("⏹️  收到停止信号，正在优雅关闭...")
        worker.stop()
        watcher.stop()
        worker.print_statistics()
        logger.info("👋 系统已停止")
        sys.exit(0)
    
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    started = watcher.start()
    if not started:
        logger.error("❌ 系统启动失败")
        return
    
    worker_thread = worker.start()
    
    try:
        while True:
            import time
            time.sleep(1)
    except KeyboardInterrupt:
        signal_handler(None, None)


if __name__ == "__main__":
    main()
