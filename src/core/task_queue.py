import queue
import threading
from src.logger import setup_logger
from src.core.task_model import Task, TaskStatus
from src.core.task_persistence import TaskPersistence

logger = setup_logger(__name__)


class TaskQueue:
    
    def __init__(self, persistence=None):
        self._queue = queue.Queue()
        self._lock = threading.Lock()
        self.persistence = persistence or TaskPersistence()
        self._recover_pending_tasks()
    
    def _recover_pending_tasks(self):
        pending_tasks = self.persistence.get_pending_tasks()
        if pending_tasks:
            logger.info(f"恢复 {len(pending_tasks)} 个未完成任务到队列")
            for task_id, task in pending_tasks.items():
                if task.status == TaskStatus.FAILED and task.can_retry():
                    logger.info(f"[{task.id}] 恢复失败任务 - 重试 {task.retry_count + 1}/{task.max_retries}")
                    self._queue.put(task)
                elif task.status in [TaskStatus.NEW, TaskStatus.TORRENT_CREATING, 
                                     TaskStatus.TORRENT_CREATED, TaskStatus.UPLOADING]:
                    logger.info(f"[{task.id}] 恢复中断任务 - 状态: {task.status.value}")
                    if task.status != TaskStatus.NEW:
                        task.update_status(TaskStatus.FAILED, "程序中断，重新排队")
                    self._queue.put(task)
    
    def enqueue(self, task):
        with self._lock:
            existing = self.persistence.get_task(task.id)
            if existing and existing.status == TaskStatus.SUCCESS:
                logger.info(f"[{task.id}] 任务已成功完成，跳过")
                return False
            
            self._queue.put(task)
            self.persistence.save_task(task)
            logger.info(f"[{task.id}] 任务已加入队列 - 状态: {task.status.value}")
            return True
    
    def dequeue(self, block=True, timeout=None):
        try:
            task = self._queue.get(block=block, timeout=timeout)
            return task
        except queue.Empty:
            return None
    
    def task_done(self):
        self._queue.task_done()
    
    def requeue_for_retry(self, task, delay_seconds=10):
        import time
        
        logger.info(f"[{task.id}] 将在 {delay_seconds} 秒后重新加入队列 (重试 {task.retry_count + 1}/{task.max_retries})")
        
        def delayed_enqueue():
            time.sleep(delay_seconds)
            task.update_status(TaskStatus.FAILED, f"等待重试 ({task.retry_count + 1}/{task.max_retries})")
            self._queue.put(task)
            self.persistence.save_task(task)
            logger.info(f"[{task.id}] 任务已重新入队")
        
        retry_thread = threading.Thread(target=delayed_enqueue, daemon=True)
        retry_thread.start()
    
    def queue_size(self):
        return self._queue.qsize()
    
    def get_all_tasks(self):
        return self.persistence.get_all_tasks()
    
    def get_statistics(self):
        return self.persistence.get_task_count_by_status()