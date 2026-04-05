import json
from pathlib import Path
from threading import Lock
from src.logger import setup_logger
from src.core.task_model import Task, TaskStatus

logger = setup_logger(__name__)


class TaskPersistence:

    def __init__(self, storage_path=None):
        if storage_path:
            self.storage_path = Path(storage_path)
        else:
            from src.config import get_config
            default_dir = Path(get_config("log_dir", "./data"))
            self.storage_path = default_dir / "tasks.json"

        self.storage_path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = Lock()
        self._load_tasks()

    def _load_tasks(self):
        try:
            if self.storage_path.exists():
                with open(self.storage_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                # v3.0: 使用增强的 from_dict（自动检测 v2.x/v3.0 格式）
                self.tasks = {
                    task_id: Task.from_dict(task_data)
                    for task_id, task_data in data.items()
                }
                logger.info(f"✅ 从持久化存储加载 {len(self.tasks)} 个任务 (v3.0 兼容模式)")
            else:
                self.tasks = {}
                logger.info("初始化空的任务存储")
        except Exception as e:
            logger.error(f"加载任务存储失败: {e}")
            self.tasks = {}

    def _save_tasks(self):
        try:
            # v3.0: 使用增强的 to_dict（保留所有字段，包括 publish_config）
            data = {
                task_id: task.to_dict()
                for task_id, task in self.tasks.items()
            }
            with open(self.storage_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"保存任务存储失败: {e}")

    def save_task(self, task):
        with self._lock:
            self.tasks[task.id] = task
            self._save_tasks()
            # v3.0: 增强日志
            logger.debug(
                f"[{task.id}] 任务已保存 - "
                f"状态: {task.status.value} (v3: {TaskStatus.to_v3(task.status)})"
            )

    def get_task(self, task_id):
        return self.tasks.get(task_id)

    def get_all_tasks(self):
        return dict(self.tasks)

    def get_pending_tasks(self):
        # v3.0: 增强版，支持新旧状态
        pending_statuses = [
            TaskStatus.NEW,
            TaskStatus.PENDING,  # v3.0 新增
            TaskStatus.TORRENT_CREATING,
            TaskStatus.TORRENT_CREATED,
            TaskStatus.READY,  # v3.0 新增
            TaskStatus.UPLOADING,
            TaskStatus.RETRYING,  # v3.0 新增
            TaskStatus.FAILED,
        ]
        result = {}
        for task_id, task in self.tasks.items():
            if task.status in pending_statuses:
                # 对于 FAILED/RETRYING，只返回可重试的任务
                if task.status in [TaskStatus.FAILED, TaskStatus.PERMANENT_FAILED]:
                    if task.can_retry():
                        result[task_id] = task
                else:
                    result[task_id] = task
        return result
    
    def delete_task(self, task_id):
        with self._lock:
            if task_id in self.tasks:
                del self.tasks[task_id]
                self._save_tasks()
                logger.debug(f"[{task_id}] 任务已删除")
    
    def get_task_count_by_status(self):
        counts = {}
        for task in self.tasks.values():
            status = task.status.value
            counts[status] = counts.get(status, 0) + 1
        return counts