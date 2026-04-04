import time
from pathlib import Path
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler, FileCreatedEvent
from src.config import WATCH_DIR, VIDEO_EXTENSIONS
from src.logger import setup_logger
from src.core.task_model import Task, TaskStatus

logger = setup_logger(__name__)


class VideoFileHandler(FileSystemEventHandler):
    
    def __init__(self, task_queue):
        super().__init__()
        self.task_queue = task_queue
    
    def on_created(self, event):
        if event.is_directory:
            return
        
        file_path = Path(event.src_path)
        
        if file_path.suffix.lower() not in VIDEO_EXTENSIONS():
            return
        
        logger.info(f"🔍 检测到新视频文件: {file_path}")
        
        time.sleep(1)
        
        if not file_path.exists():
            return
        
        task_id = Task.generate_id(file_path)
        task = Task(
            id=task_id,
            video_path=str(file_path),
            status=TaskStatus.NEW
        )
        
        logger.info(f"📋 创建任务 [{task_id}] - 文件: {file_path.name}")
        
        enqueued = self.task_queue.enqueue(task)
        
        if enqueued:
            logger.info(f"✅ 任务 [{task_id}] 已加入队列，等待 Worker 处理")
        else:
            logger.info(f"⏭️  任务 [{task_id}] 已存在或已完成，跳过")


class Watcher:
    
    def __init__(self, watch_dir=None, task_queue=None):
        self.watch_dir = watch_dir or WATCH_DIR()
        self.task_queue = task_queue
        self.observer = Observer()
        
        if self.task_queue:
            self.event_handler = VideoFileHandler(self.task_queue)
    
    def set_task_queue(self, task_queue):
        self.task_queue = task_queue
        self.event_handler = VideoFileHandler(self.task_queue)
    
    def start(self):
        if not self.task_queue:
            logger.error("❌ 未设置任务队列，Watcher 无法启动")
            return False
        
        self.watch_dir.mkdir(parents=True, exist_ok=True)
        self.observer.schedule(self.event_handler, str(self.watch_dir), recursive=False)
        self.observer.start()
        
        logger.info("=" * 60)
        logger.info("👁️  文件监控启动")
        logger.info(f"   监控目录: {self.watch_dir}")
        logger.info(f"   支持格式: {', '.join(VIDEO_EXTENSIONS())}")
        logger.info("=" * 60)
        
        return True
    
    def stop(self):
        logger.info("停止文件监控...")
        self.observer.stop()
        self.observer.join()
        logger.info("文件监控已停止")