from enum import Enum
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, Dict, Any
import hashlib


class TaskStatus(Enum):
    NEW = "new"
    TORRENT_CREATING = "torrent_creating"
    TORRENT_CREATED = "torrent_created"
    UPLOADING = "uploading"
    SUCCESS = "success"
    FAILED = "failed"
    PERMANENT_FAILED = "permanent_failed"


@dataclass
class PublishInfo:
    """发布信息（对标 OKPGUI / OKP setting.toml 字段）"""
    title: str = ""                    # 发布标题 (display_name)
    subtitle: str = ""                  # 副标题
    tags: str = ""                      # 分类标签，如 "Anime" 或 "Anime, Collection"（逗号分隔）
    description: str = ""               # 正文内容 (Markdown)
    about: str = ""                     # 关于/联系方式 (Nyaa 专用)
    poster: str = ""                    # 海报链接 (dmhy 专用)
    group_name: str = ""                # 发布小组名
    # v2.2 新增：对标 OKPGUI 额外字段
    category: str = ""                  # 分类，如 Anime / Music / Raw
    source: str = ""                     # 来源，如 WEB / BD / TV / DVD
    video_codec: str = ""                # 视频编码，如 H264 / H265 / VP9
    audio_codec: str = ""                # 音频编码，如 AAC / FLAC / AC3
    subtitle_type: str = ""             # 字幕类型，如 内嵌 / 外挂 / 无

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
    """OKP 执行结果详情"""
    mode: str = ""                       # preview / publish / error / timeout / exception
    success: bool = False
    returncode: int = 0
    stdout: str = ""
    stderr: str = ""
    error: Optional[str] = None
    command: str = ""

    def to_dict(self):
        return {
            'mode': self.mode,
            'success': self.success,
            'returncode': self.returncode,
            'stdout': self.stdout[:5000] if self.stdout else "",     # 截断避免过大
            'stderr': self.stderr[:2000] if self.stderr else "",
            'error': self.error,
            'command': self.command,
        }

    @classmethod
    def from_dict(cls, data):
        if not data:
            return cls()
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})


@dataclass
class Task:
    id: str
    video_path: str
    torrent_path: Optional[str] = None
    status: TaskStatus = TaskStatus.NEW
    retry_count: int = 0
    max_retries: int = 3
    error_message: Optional[str] = None
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    updated_at: str = field(default_factory=lambda: datetime.now().isoformat())

    # ── v2.1 新增字段 ──
    publish_info: PublishInfo = field(default_factory=PublishInfo)
    video_meta: VideoMeta = field(default_factory=VideoMeta)
    torrent_meta: TorrentMeta = field(default_factory=TorrentMeta)
    okp_result: Optional[OKPResult] = None

    @staticmethod
    def generate_id(video_path):
        return hashlib.md5(str(video_path).encode()).hexdigest()[:12].upper()

    def to_dict(self):
        d = {
            'id': self.id,
            'video_path': self.video_path,
            'torrent_path': self.torrent_path,
            'status': self.status.value,
            'retry_count': self.retry_count,
            'max_retries': self.max_retries,
            'error_message': self.error_message,
            'created_at': self.created_at,
            'updated_at': self.updated_at,
            'publish_info': self.publish_info.to_dict(),
            'video_meta': self.video_meta.to_dict(),
            'torrent_meta': self.torrent_meta.to_dict(),
        }
        if self.okp_result:
            d['okp_result'] = self.okp_result.to_dict()
        return d

    @classmethod
    def from_dict(cls, data):
        task = cls(
            id=data['id'],
            video_path=data['video_path'],
            torrent_path=data.get('torrent_path'),
            status=TaskStatus(data['status']),
            retry_count=data.get('retry_count', 0),
            max_retries=data.get('max_retries', 3),
            error_message=data.get('error_message'),
            created_at=data['created_at'],
            updated_at=data['updated_at'],
        )
        task.publish_info = PublishInfo.from_dict(data.get('publish_info'))
        task.video_meta = VideoMeta.from_dict(data.get('video_meta'))
        task.torrent_meta = TorrentMeta.from_dict(data.get('torrent_meta'))
        if data.get('okp_result'):
            task.okp_result = OKPResult.from_dict(data.get('okp_result'))
        return task

    def update_status(self, new_status, error_message=None):
        self.status = new_status
        self.updated_at = datetime.now().isoformat()
        if error_message:
            self.error_message = error_message

    def can_retry(self):
        return (self.status == TaskStatus.FAILED and
                self.retry_count < self.max_retries)

    def increment_retry(self):
        self.retry_count += 1
        self.updated_at = datetime.now().isoformat()
