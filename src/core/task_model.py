"""
BT 自动发布系统 - 任务数据模型 (v2.x → v3.0 兼容层)
=====================================================

本模块定义了任务系统的核心数据结构。

版本演进：
  - v2.x: 原始 dataclass 实现（向后兼容）
  - v3.0: 新增状态机、发布配置等字段

设计原则：
  - 完全向后兼容，旧代码无需修改即可运行
  - 渐进式迁移，新功能通过新字段支持
  - 与 task_schema.py (Pydantic) 双向兼容

作者: BT Auto Publishing System Team
版本: 2.5.0 (兼容 v3.0)
"""

from enum import Enum
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, Dict, Any, List
import hashlib


# ══════════════════════════════════════════════════════════════════════
#  枚举类型（v3.0 增强版）
# ══════════════════════════════════════════════════════════════════════

class TaskStatus(Enum):
    """
    任务状态枚举（v3.0 兼容）

    v2.x 旧状态（保留）:
      - NEW: 初始状态
      - TORRENT_CREATING: Torrent生成中
      - TORRENT_CREATED: Torrent已生成
      - UPLOADING: 上传/发布中
      - SUCCESS: 成功
      - FAILED: 失败
      - PERMANENT_FAILED: 永久失败

    v3.0 新增状态:
      - PENDING: 待处理（等同于 NEW 的语义化别名）
      - READY: 就绪（等同于 TORRENT_CREATED 的增强版）
      - RETRYING: 重试中（从 FAILED 衍生）
      - CANCELLED: 已取消（新增终态）
    """

    # ── v2.x 原有状态（保持不变）──────────────────────────────
    NEW = "new"
    TORRENT_CREATING = "torrent_creating"
    TORRENT_CREATED = "torrent_created"
    UPLOADING = "uploading"
    SUCCESS = "success"
    FAILED = "failed"
    PERMANENT_FAILED = "permanent_failed"

    # ── v3.0 新增状态 ──────────────────────────────────────────────
    PENDING = "pending"           # 待处理（NEW 的语义化别名）
    READY = "ready"               # 就绪（TORRENT_CREATED 的增强版）
    RETRYING = "retrying"         # 重试中
    CANCELLED = "cancelled"       # 已取消（终态）

    @classmethod
    def from_v3(cls, v3_status: str):
        """将 v3.0 状态映射到 v2.x 兼容状态"""
        mapping = {
            "pending": cls.NEW,
            "ready": cls.TORRENT_CREATED,
            "retrying": cls.UPLOADING,  # 复用上传中状态
            "cancelled": cls.PERMANENT_FAILED,  # 映射为永久失败
        }
        return mapping.get(v3_status, cls(v3_status))

    @classmethod
    def to_v3(cls, v2_status):
        """将 v2.x 状态映射到 v3.0 标准状态"""
        if isinstance(v2_status, str):
            v2_status = cls(v2_status)

        mapping = {
            cls.NEW: "pending",
            cls.TORRENT_CREATING: "pending",
            cls.TORRENT_CREATED: "ready",
            cls.UPLOADING: "uploading",
            cls.SUCCESS: "success",
            cls.FAILED: "failed",
            cls.PERMANENT_FAILED: "cancelled",
            # v3.0 状态直接返回
            cls.PENDING: "pending",
            cls.READY: "ready",
            cls.RETRYING: "retrying",
            cls.CANCELLED: "cancelled",
        }
        return mapping.get(v2_status, v2_status.value if hasattr(v2_status, 'value') else str(v2_status))

    @classmethod
    def active_statuses(cls):
        """返回所有活跃状态（非终态）"""
        return [
            cls.NEW, cls.PENDING, cls.TORRENT_CREATING,
            cls.TORRENT_CREATED, cls.READY,
            cls.UPLOADING, cls.RETRYING
        ]

    @classmethod
    def terminal_statuses(cls):
        """返回所有终态"""
        return [cls.SUCCESS, cls.FAILED, cls.PERMANENT_FAILED, cls.CANCELLED]


# ══════════════════════════════════════════════════════════════════════
#  数据模型（dataclass - 向后兼容）
# ══════════════════════════════════════════════════════════════════════

@dataclass
class PublishInfo:
    """发布信息（对标 OKPGUI / OKP setting.toml 字段）"""

    title: str = ""                    # 发布标题 (display_name)
    subtitle: str = ""                  # 副标题
    tags: str = ""                      # 分类标签，逗号分隔
    description: str = ""               # 正文内容 (Markdown)
    about: str = ""                     # 关于/联系方式 (Nyaa 专用)
    poster: str = ""                    # 海报链接 (dmhy 专用)
    group_name: str = ""                # 发布小组名

    # v2.2 新增：媒体参数字段
    category: str = ""                  # 分类
    source: str = ""                     # 来源
    video_codec: str = ""                # 视频编码
    audio_codec: str = ""                # 音频编码
    subtitle_type: str = ""             # 字幕类型

    def to_dict(self):
        return {
            'title': self.title,
            'subtitle': self.subtitle,
            'tags': self.tags,
            'description': self.description,
            'about': self.about,
            'poster': self.poster,
            'group_name': self.group_name,
            'category': self.category,
            'source': self.source,
            'video_codec': self.video_codec,
            'audio_codec': self.audio_codec,
            'subtitle_type': self.subtitle_type,
        }

    @classmethod
    def from_dict(cls, data):
        if not data:
            return cls()
        return cls(
            title=data.get('title', ''),
            subtitle=data.get('subtitle', ''),
            tags=data.get('tags', ''),
            description=data.get('description', ''),
            about=data.get('about', ''),
            poster=data.get('poster', ''),
            group_name=data.get('group_name', ''),
            category=data.get('category', ''),
            source=data.get('source', ''),
            video_codec=data.get('video_codec', ''),
            audio_codec=data.get('audio_codec', ''),
            subtitle_type=data.get('subtitle_type', ''),
        )

    def to_tag_list(self) -> List[str]:
        """将 tags 字符串转换为列表"""
        if not self.tags:
            return []
        return [t.strip() for t in self.tags.split(',') if t.strip()]

    def from_tag_list(self, tags: List[str]):
        """从列表设置 tags 字符串"""
        self.tags = ', '.join(tags)


@dataclass
class VideoMeta:
    """视频文件元信息（来自 Probe + Normalizer）"""
    width: int = 0
    height: int = 0
    codec: str = ""
    resolution: str = ""               # 1080p / 720p / 4K 等
    duration_seconds: int = 0
    file_size: int = 0

    def to_dict(self):
        return {
            'width': self.width,
            'height': self.height,
            'codec': self.codec,
            'resolution': self.resolution,
            'duration_seconds': self.duration_seconds,
            'file_size': self.file_size,
        }

    @classmethod
    def from_dict(cls, data):
        if not data:
            return cls()
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})


@dataclass
class TorrentMeta:
    """Torrent 文件元信息（来自 torf 解析）"""
    name: str = ""
    size: int = 0
    file_count: int = 0
    files: list = field(default_factory=list)   # [{name, size}, ...]
    tracker_count: int = 0
    tracker_sample: list = field(default_factory=list)  # 前3个 tracker

    def to_dict(self):
        return {
            'name': self.name,
            'size': self.size,
            'file_count': self.file_count,
            'files': self.files,
            'tracker_count': self.tracker_count,
            'tracker_sample': self.tracker_sample,
        }

    @classmethod
    def from_dict(cls, data):
        if not data:
            return cls()
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})


@dataclass
class OKPResult:
    """OKP 执行结果详情（v3.0 增强）"""
    mode: str = ""                       # preview / publish / error / timeout / exception
    success: bool = False
    returncode: int = 0
    stdout: str = ""
    stderr: str = ""
    error: Optional[str] = None
    command: str = ""

    # v3.0 新增字段
    executed_at: Optional[str] = None   # 执行时间 ISO
    duration_ms: Optional[int] = None     # 执行耗时(ms)
    site_results: Optional[list] = None   # 多站点结果

    def to_dict(self):
        d = {
            'mode': self.mode,
            'success': self.success,
            'returncode': self.returncode,
            'stdout': self.stdout[:5000] if self.stdout else "",
            'stderr': self.stderr[:2000] if self.stderr else "",
            'error': self.error,
            'command': self.command,
        }
        # v3.0 新字段
        if self.executed_at:
            d['executed_at'] = self.executed_at
        if self.duration_ms is not None:
            d['duration_ms'] = self.duration_ms
        if self.site_results:
            d['site_results'] = self.site_results
        return d

    @classmethod
    def from_dict(cls, data):
        if not data:
            return cls()
        result = cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})
        # v3.0 新字段
        result.executed_at = data.get('executed_at')
        result.duration_ms = data.get('duration_ms')
        result.site_results = data.get('site_results')
        return result


@dataclass
class PublishConfig:
    """
    发布配置（v3.0 新增）

    控制发布行为的配置项。
    在 v2.x 中这些信息分散在各个地方，
    v3.0 统一为此结构体。
    """

    sites: List[str] = field(default_factory=list)  # 目标站点列表
    auto_confirm: bool = True                       # 是否自动确认OKP弹窗
    dry_run: bool = False                            # 是否试运行模式
    mode: str = "publish"                             # 发布模式: preview/dry_run/publish

    def to_dict(self):
        return {
            'sites': self.sites,
            'auto_confirm': self.auto_confirm,
            'dry_run': self.dry_run,
            'mode': self.mode,
        }

    @classmethod
    def from_dict(cls, data):
        if not data:
            return cls()
        return cls(
            sites=data.get('sites', []),
            auto_confirm=data.get('auto_confirm', True),
            dry_run=data.get('dry_run', False),
            mode=data.get('mode', 'publish'),
        )


# ══════════════════════════════════════════════════════════════════════
#  核心 Task 模型（v3.0 增强）
# ══════════════════════════════════════════════════════════════════════

@dataclass
class Task:
    """
    任务数据模型（v3.0 兼容版）

    改进点：
      1. 新增 publish_config 字段
      2. 新增状态机方法
      3. 新增便捷属性
      4. 完全向后兼容 v2.x
    """

    # ── 基础标识 ────────────────────────────────────────────────
    id: str
    video_path: str
    torrent_path: Optional[str] = None

    # ── 状态信息 ────────────────────────────────────────────────
    status: TaskStatus = TaskStatus.NEW
    retry_count: int = 0
    max_retries: int = 3
    error_message: Optional[str] = None

    # ── 时间戳 ──────────────────────────────────────────────────
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    updated_at: str = field(default_factory=lambda: datetime.now().isoformat())

    # ── v2.1 原有字段（保持不变）──────────────────────────────
    publish_info: PublishInfo = field(default_factory=PublishInfo)
    video_meta: VideoMeta = field(default_factory=VideoMeta)
    torrent_meta: TorrentMeta = field(default_factory=TorrentMeta)
    okp_result: Optional[OKPResult] = None

    # ── v3.0 新增字段 ──────────────────────────────────────────
    publish_config: PublishConfig = field(default_factory=PublishConfig)

    @staticmethod
    def generate_id(video_path):
        return hashlib.md5(str(video_path).encode()).hexdigest()[:12].upper()

    # ═══ 序列化方法 ═══

    def to_dict(self, v3_mode: bool = False):
        """
        转换为字典

        Args:
            v3_mode: 是否使用 v3.0 格式输出
                   - False (默认): v2.x 兼容格式
                   - True:  v3.0 标准格式
        """
        base = {
            'id': self.id,
            'file_path': self.video_path,  # v3.0 使用 file_path
            'video_path': self.video_path,  # v2.x 兼容
            'torrent_path': self.torrent_path,

            # 状态（根据模式选择格式）
            'status': TaskStatus.to_v3(self.status) if v3_mode else self.status.value,

            'retry_count': self.retry_count,
            'max_retries': self.max_retries,
            'error_message': self.error_message,
            'created_at': self.created_at,
            'updated_at': self.updated_at,

            # 子对象
            'publish_info': self.publish_info.to_dict(),
            'video_meta': self.video_meta.to_dict(),
            'torrent_meta': self.torrent_meta.to_dict(),
        }

        # 可选字段
        if self.okp_result:
            base['okp_result'] = self.okp_result.to_dict()

        # v3.0 新增字段
        if v3_mode:
            base['publish_config'] = self.publish_config.to_dict()
            # 移除 v2.x 兼容字段
            base.pop('video_path', None)

        return base

    @classmethod
    def from_dict(cls, data):
        """从字典创建任务（自动检测 v2.x 或 v3.0 格式）"""
        # 兼容 v3.0 的 file_path 字段
        video_path = data.get('video_path') or data.get('file_path')

        task = cls(
            id=data['id'],
            video_path=video_path,
            torrent_path=data.get('torrent_path'),
            status=TaskStatus(data['status']),
            retry_count=data.get('retry_count', 0),
            max_retries=data.get('max_retries', 3),
            error_message=data.get('error_message'),
            created_at=data.get('created_at'),
            updated_at=data.get('updated_at'),
        )

        # 子对象
        task.publish_info = PublishInfo.from_dict(data.get('publish_info'))
        task.video_meta = VideoMeta.from_dict(data.get('video_meta'))
        task.torrent_meta = TorrentMeta.from_dict(data.get('torrent_meta'))

        if data.get('okp_result'):
            task.okp_result = OKPResult.from_dict(data.get('okp_result'))

        # v3.0 新字段
        if data.get('publish_config'):
            task.publish_config = PublishConfig.from_dict(data.get('publish_config'))

        return task

    # ═══ 状态管理方法 ═══

    def update_status(self, new_status, error_message=None):
        """
        更新状态（v2.x 兼容方法）

        注意：v3.0 推荐使用 transition_to() 方法
        """
        self.status = new_status
        self.updated_at = datetime.now().isoformat()
        if error_message:
            self.error_message = error_message

    def can_transition_to(self, new_status: TaskStatus) -> bool:
        """
        v3.0 新增：检查是否可以转换到目标状态

        状态转换规则：
          pending/new → ready/torrent_created
          ready → uploading
          uploading → success/failed
          failed → retrying/uploading（重试时）
          retrying → uploading/failed
          任意活跃状态 → cancelled
        """
        valid_transitions = {
            # 从初始状态
            TaskStatus.NEW: {TaskStatus.TORRENT_CREATING, TaskStatus.TORRENT_CREATED, TaskStatus.PENDING, TaskStatus.READY, TaskStatus.CANCELLED},
            TaskStatus.PENDING: {TaskStatus.TORRENT_CREATING, TaskStatus.TORRENT_CREATED, TaskStatus.READY, TaskStatus.CANCELLED},

            # 从就绪状态
            TaskStatus.TORRENT_CREATED: {TaskStatus.UPLOADING, TaskStatus.READY, TaskStatus.CANCELLED},
            TaskStatus.READY: {TaskStatus.UPLOADING, TaskStatus.CANCELLED},

            # 从执行状态
            TaskStatus.UPLOADING: {TaskStatus.SUCCESS, TaskStatus.FAILED, TaskStatus.CANCELLED},

            # 从失败状态
            TaskStatus.FAILED: {TaskStatus.RETRYING, TaskStatus.CANCELLED},
            TaskStatus.PERMANENT_FAILED: set(),  # 终态

            # 从重试状态
            TaskStatus.RETRYING: {TaskStatus.UPLOADING, TaskStatus.FAILED, TaskStatus.CANCELLED},

            # 终态不可变
            TaskStatus.SUCCESS: set(),
            TaskStatus.CANCELLED: set(),
        }
        allowed = valid_transitions.get(self.status, set())
        return new_status in allowed

    def transition_to(self, new_status: TaskStatus, error_message: Optional[str] = None) -> bool:
        """
        v3.0 新增：执行状态转换（带验证）

        Args:
            new_status: 目标状态
            error_message: 错误信息（可选）

        Returns:
            是否成功转换

        Raises:
            ValueError: 如果状态转换非法
        """
        if not self.can_transition_to(new_status):
            current = self.status.value
            target = new_status.value
            raise ValueError(
                f"非法状态转换: {current} → {target}"
            )

        old_status = self.status
        self.status = new_status
        self.updated_at = datetime.now().isoformat()

        # 特殊处理
        if new_status == TaskStatus.RETRYING:
            self.retry_count += 1

        if new_status in [TaskStatus.SUCCESS, TaskStatus.READY, TaskStatus.TORRENT_CREATED]:
            self.error_message = None  # 成功时清除错误

        if error_message:
            self.error_message = error_message

        return True

    def get_allowed_transitions(self) -> List[TaskStatus]:
        """v3.0 新增：获取当前状态允许的所有目标状态"""
        all_statuses = list(TaskStatus)
        return [s for s in all_statuses if self.can_transition_to(s)]

    # ═══ 便捷属性和方法 ═══

    def can_retry(self) -> bool:
        """检查是否可以重试"""
        return (
            self.status in [TaskStatus.FAILED, TaskStatus.PERMANENT_FAILED] and
            self.retry_count < self.max_retries
        )

    def increment_retry(self):
        """增加重试计数"""
        self.retry_count += 1
        self.updated_at = datetime.now().isoformat()

    def is_terminal(self) -> bool:
        """v3.0 新增：检查是否为终态"""
        return self.status in TaskStatus.terminal_statuses()

    def is_active(self) -> bool:
        """v3.0 新增：检查是否为活跃状态"""
        return self.status in TaskStatus.active_statuses()

    @property
    def file_name(self) -> str:
        """获取文件名"""
        import os
        return os.path.basename(self.video_path)

    @property
    def display_title(self) -> str:
        """获取显示用的标题（优先使用 publish_info.title）"""
        return self.publish_info.title or self.file_name

    @property
    def is_ready_to_publish(self) -> bool:
        """v3.0 新增：检查是否准备好可以发布"""
        return (
            self.status in [TaskStatus.READY, TaskStatus.TORRENT_CREATED] and
            self.torrent_path is not None and
            len(self.publish_config.sites) > 0 and
            bool(self.publish_info.title)
        )

    @classmethod
    def create_from_file(cls, file_path: str):
        """v3.0 新增：工厂方法，从文件路径创建任务"""
        task_id = cls.generate_id(file_path)
        return cls(id=task_id, video_path=file_path)
