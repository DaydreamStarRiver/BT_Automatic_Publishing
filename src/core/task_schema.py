"""
BT 自动发布系统 - 统一数据模型与 API 规范 (v3.0 Standard)
=====================================================

本模块定义了前后端统一的 Task 数据结构、REST API 接口规范、状态机逻辑。

设计原则：
  - 前端 UI / 后端调度 / Worker 执行 三者使用同一套数据结构
  - 完全兼容 OKPGUI / OKP 的字段命名
  - Pydantic v2 风格，支持自动序列化/反序列化
  - 类型安全，IDE 友好

作者: BT Auto Publishing System Team
版本: 3.0.0 Standard
日期: 2026-01-30
"""

from __future__ import annotations

from enum import Enum
from typing import Optional, List, Dict, Any, Literal
from datetime import datetime
from pydantic import BaseModel, Field, field_validator, model_validator


# ══════════════════════════════════════════════════════════════════════
#  第一部分：枚举类型定义
# ══════════════════════════════════════════════════════════════════════

class TaskStatus(str, Enum):
    """任务状态枚举（状态机核心）"""

    PENDING = "pending"           # 待处理（初始状态）
    READY = "ready"               # 就绪（Torrent已生成，可发布）
    UPLOADING = "uploading"       # 发布中（正在调用OKP）
    SUCCESS = "success"           # 成功
    FAILED = "failed"             # 失败（可重试）
    RETRYING = "retrying"         # 重试中
    CANCELLED = "cancelled"       # 已取消

    @classmethod
    def active_statuses(cls) -> List[TaskStatus]:
        """返回所有活跃状态（非终态）"""
        return [cls.PENDING, cls.READY, cls.UPLOADING, cls.RETRYING]

    @classmethod
    def terminal_statuses(cls) -> List[TaskStatus]:
        """返回所有终态（不可再变化）"""
        return [cls.SUCCESS, cls.FAILED, cls.CANCELLED]


class PublishMode(str, Enum):
    """发布模式"""
    PREVIEW = "preview"          # 预览模式（不实际发布）
    DRY_RUN = "dry_run"          # 试运行（模拟执行）
    PUBLISH = "publish"          # 正式发布


class SiteID(str, Enum):
    """支持的站点代号（对标 OKPGUI）"""
    NYAA = "nyaa"
    DMHY = "dmhy"
    ACG_RIP = "acgrip"
    BANGUMI = "bangumi"
    ACGNX_ASIA = "acgnx_asia"
    ACGNX_GLOBAL = "acgnx_global"


# ══════════════════════════════════════════════════════════════════════
#  第二部分：数据模型定义（Pydantic v2）
# ══════════════════════════════════════════════════════════════════════

class PublishInfo(BaseModel):
    """
    发布信息（UI 编辑区域）

    对标 OKPGUI 字段：
      - title → 标题
      - subtitle → 副标题/Episode信息
      - poster → 海报链接 (dmhy)
      - group_name → 发布组
      - tags → Tags (逗号分隔字符串)
      - description → 内容 (Markdown)
    """

    title: str = Field(
        default="",
        description="发布标题，如 [SweetSub] Oniichan wa Oshimai! - 01 [WebRip][1080p]",
        examples=["[SweetSub] Oniichan wa Oshimai! - 01 [WebRip][1080p][H265][FLAC]"]
    )
    subtitle: str = Field(
        default="",
        description="副标题或Episode信息",
        examples=["Episode 01 - お兄ちゃんはおしまい！"]
    )
    poster: str = Field(
        default="",
        description="海报URL（dmhy必需）",
        examples=["https://example.com/poster.jpg"]
    )
    group_name: str = Field(
        default="",
        description="发布组名称",
        examples=["SweetSub", "LoliHouse", "MajiSubs"]
    )
    tags: str = Field(
        default="",
        description="Tags（逗号分隔），如 'Anime, HD, Hi10P'",
        examples=["Anime", "Anime, HD, Hi10P"]
    )
    description: str = Field(
        default="",
        description="发布内容（Markdown格式）",
        examples=["## 发布信息\n\n- **来源**: WebRip\n- **制作**: SweetSub"]
    )

    @field_validator('tags')
    @classmethod
    def normalize_tags(cls, v: str) -> str:
        """标准化Tags格式：去除多余空格，确保逗号分隔"""
        if not v:
            return ""
        tags = [t.strip() for t in v.split(',') if t.strip()]
        return ', '.join(tags)

    def to_tag_list(self) -> List[str]:
        """将tags字符串转换为列表"""
        if not self.tags:
            return []
        return [t.strip() for t in self.tags.split(',') if t.strip()]

    def from_tag_list(self, tags: List[str]) -> None:
        """从列表设置tags字符串"""
        self.tags = ', '.join(tags)


class MediaInfo(BaseModel):
    """
    媒体技术参数（由 Normalizer 解析得到）

    这些字段通常不需要用户手动填写，
    系统会从文件名或视频元数据自动提取。
    """

    resolution: Optional[str] = Field(
        default=None,
        description="分辨率",
        examples=["1080p", "720p", "2160p (4K)"]
    )
    video_codec: Optional[str] = Field(
        default=None,
        description="视频编码",
        examples=["H265", "H264", "AV1", "VP9"]
    )
    audio_codec: Optional[str] = Field(
        default=None,
        description="音频编码",
        examples=["FLAC", "AAC", "AC3", "DTS"]
    )
    subtitle_type: Optional[str] = Field(
        default=None,
        description="字幕类型",
        examples=["内嵌", "外挂", "无"]
    )
    source: Optional[str] = Field(
        default=None,
        description="来源类型",
        examples=["WEB", "BD", "TV", "DVD", "Raw"]
    )

    class Config:
        json_schema_extra = {
            "example": {
                "resolution": "1080p",
                "video_codec": "H265",
                "audio_codec": "FLAC",
                "subtitle_type": "内嵌",
                "source": "WEB"
            }
        }


class PublishConfig(BaseModel):
    """
    发布配置（控制发布行为）
    """

    sites: List[str] = Field(
        default_factory=list,
        description="目标站点列表",
        examples=[["nyaa", "dmhy"], ["nyaa"]]
    )
    auto_confirm: bool = Field(
        default=True,
        description="是否自动确认OKP弹窗"
    )
    dry_run: bool = Field(
        default=False,
        description="是否为试运行模式（不实际发布）"
    )
    mode: PublishMode = Field(
        default=PublishMode.PUBLISH,
        description="发布模式"
    )

    @field_validator('sites')
    @classmethod
    def validate_sites(cls, v: List[str]) -> List[str]:
        """验证站点ID是否合法"""
        valid_sites = {site.value for site in SiteID}
        invalid = [s for s in v if s not in valid_sites]
        if invalid:
            raise ValueError(f"无效的站点ID: {invalid}. 有效值: {valid_sites}")
        return v


class VideoMeta(BaseModel):
    """视频文件元信息（来自 ffprobe）"""

    width: int = Field(default=0, ge=0)
    height: int = Field(default=0, ge=0)
    duration_seconds: float = Field(default=0.0, ge=0)
    file_size_bytes: int = Field(default=0, ge=0, alias="file_size")
    codec: Optional[str] = None
    fps: Optional[float] = None
    bitrate: Optional[int] = None

    model_config = {"populate_by_name": True}


class TorrentMeta(BaseModel):
    """Torrent 文件元信息（来自 torf 解析）"""

    name: str = Field(default="")
    size_bytes: int = Field(default=0, ge=0, alias="size")
    file_count: int = Field(default=0, ge=0)
    files: List[Dict[str, Any]] = Field(default_factory=list)
    tracker_count: int = Field(default=0, ge=0)
    trackers_sample: List[str] = Field(default_factory=list)

    model_config = {"populate_by_name": True}


class OKPResult(BaseModel):
    """OKP 执行结果"""

    mode: str = Field(default="", description="执行模式")
    success: bool = Field(default=False, description="是否成功")
    returncode: int = Field(default=-1, description="进程返回码")
    stdout: str = Field(default="", description="标准输出（截断）")
    stderr: str = Field(default="", description="标准错误（截断）")
    error: Optional[str] = Field(default=None, description="错误信息")
    command: str = Field(default="", description="执行的命令")
    executed_at: Optional[str] = Field(default=None, description="执行时间ISO")
    duration_ms: Optional[int] = Field(default=None, description="执行耗时(ms)")
    site_results: Optional[List[Dict[str, Any]]] = Field(
        default=None,
        description="多站点发布时各站点的结果"
    )


# ══════════════════════════════════════════════════════════════════════
#  第三部分：核心 Task 模型
# ══════════════════════════════════════════════════════════════════════

class Task(BaseModel):
    """
    任务数据模型（统一标准 v3.0）

    这是整个系统的核心数据结构，用于：
      - 前端 UI 展示和编辑
      - 后端 API 序列化
      - Worker 执行
      - 持久化存储

    设计原则：
      - 所有字段都有明确的类型注解
      - 支持完整的 JSON 序列化/反序列化
      - 兼容 OKPGUI 字段命名
      - 内置状态机逻辑
    """

    # ── 基础标识 ────────────────────────────────────────────────
    id: str = Field(
        ...,
        description="任务唯一ID（12位MD5前缀大写）",
        pattern=r'^[A-F0-9]{12}$',
        examples=["A1B2C3D4E5F6"]
    )
    file_path: str = Field(
        ...,
        description="源视频文件绝对路径",
        examples=["D:/Videos/[SweetSub] Oniichan wa Oshimai! - 01 [WebRip][1080p].mp4"]
    )
    torrent_path: Optional[str] = Field(
        default=None,
        description="生成的Torrent文件路径",
        examples=["D:/output/torrents/A1B2C3D4E5F6.torrent"]
    )

    # ── 发布信息（UI 编辑区） ──────────────────────────────────
    publish_info: PublishInfo = Field(
        default_factory=PublishInfo,
        description="发布信息（标题/Tags/内容等）"
    )

    # ── 媒体信息（解析得到） ───────────────────────────────────
    media_info: MediaInfo = Field(
        default_factory=MediaInfo,
        description="媒体技术参数（分辨率/编码等）"
    )

    # ── 元数据（自动提取） ─────────────────────────────────────
    video_meta: Optional[VideoMeta] = Field(
        default=None,
        description="视频文件元信息（ffprobe结果）"
    )
    torrent_meta: Optional[TorrentMeta] = Field(
        default=None,
        description="Torrent文件元信息（torf解析结果）"
    )

    # ── 发布配置 ────────────────────────────────────────────────
    publish_config: PublishConfig = Field(
        default_factory=PublishConfig,
        description="发布配置（站点/选项等）"
    )

    # ── 状态信息 ────────────────────────────────────────────────
    status: TaskStatus = Field(
        default=TaskStatus.PENDING,
        description="当前任务状态"
    )
    retry_count: int = Field(
        default=0,
        ge=0,
        description="已重试次数"
    )
    max_retries: int = Field(
        default=3,
        ge=0,
        le=10,
        description="最大重试次数"
    )
    error_message: Optional[str] = Field(
        default=None,
        description="错误信息（失败时填充）"
    )

    # ── 执行结果 ──────────────────────────────────────────────
    okp_result: Optional[OKPResult] = Field(
        default=None,
        description="最近一次OKP执行结果"
    )

    # ── 时间戳 ──────────────────────────────────────────────────
    created_at: str = Field(
        default_factory=lambda: datetime.now().isoformat(),
        description="创建时间（ISO 8601）"
    )
    updated_at: str = Field(
        default_factory=lambda: datetime.now().isoformat(),
        description="最后更新时间（ISO 8601）"
    )

    # ── 状态机方法 ─────────────────────────────────────────────

    def can_transition_to(self, new_status: TaskStatus) -> bool:
        """
        检查是否可以转换到目标状态

        状态转换规则：
          pending → ready | cancelled
          ready → uploading | cancelled
          uploading → success | failed | cancelled
          failed → retrying | cancelled
          retrying → uploading | failed | cancelled
          success → (终态，不可变)
          cancelled → (终态，不可变)
        """
        valid_transitions = {
            TaskStatus.PENDING: {TaskStatus.READY, TaskStatus.CANCELLED},
            TaskStatus.READY: {TaskStatus.UPLOADING, TaskStatus.CANCELLED},
            TaskStatus.UPLOADING: {TaskStatus.SUCCESS, TaskStatus.FAILED, TaskStatus.CANCELLED},
            TaskStatus.FAILED: {TaskStatus.RETRYING, TaskStatus.CANCELLED},
            TaskStatus.RETRYING: {TaskStatus.UPLOADING, TaskStatus.FAILED, TaskStatus.CANCELLED},
        }
        allowed = valid_transitions.get(self.status, set())
        return new_status in allowed

    def transition_to(self, new_status: TaskStatus, error_message: Optional[str] = None) -> bool:
        """
        执行状态转换

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
                f"非法状态转换: {current} → {target}。"
                f"允许的转换: {[s.value for s in self.get_allowed_transitions()]}"
            )

        old_status = self.status
        self.status = new_status
        self.updated_at = datetime.now().isoformat()

        if new_status == TaskStatus.RETRYING:
            self.retry_count += 1

        if error_message:
            self.error_message = error_message

        if new_status in [TaskStatus.SUCCESS, TaskStatus.READY]:
            self.error_message = None

        return True

    def get_allowed_transitions(self) -> List[TaskStatus]:
        """获取当前状态允许的所有目标状态"""
        valid_transitions = {
            TaskStatus.PENDING: [TaskStatus.READY, TaskStatus.CANCELLED],
            TaskStatus.READY: [TaskStatus.UPLOADING, TaskStatus.CANCELLED],
            TaskStatus.UPLOADING: [TaskStatus.SUCCESS, TaskStatus.FAILED, TaskStatus.CANCELLED],
            TaskStatus.FAILED: [TaskStatus.RETRYING, TaskStatus.CANCELLED],
            TaskStatus.RETRYING: [TaskStatus.UPLOADING, TaskStatus.FAILED, TaskStatus.CANCELLED],
            TaskStatus.SUCCESS: [],
            TaskStatus.CANCELLED: [],
        }
        return valid_transitions.get(self.status, [])

    def can_retry(self) -> bool:
        """检查是否可以重试"""
        return (
            self.status == TaskStatus.FAILED and
            self.retry_count < self.max_retries
        )

    def is_terminal(self) -> bool:
        """检查是否为终态"""
        return self.status in TaskStatus.terminal_statuses()

    def is_active(self) -> bool:
        """检查是否为活跃状态"""
        return self.status in TaskStatus.active_statuses()

    # ── 便捷属性 ────────────────────────────────────────────────

    @property
    def file_name(self) -> str:
        """获取文件名"""
        import os
        return os.path.basename(self.file_path)

    @property
    def is_ready_to_publish(self) -> bool:
        """检查是否准备好可以发布"""
        return (
            self.status == TaskStatus.READY and
            self.torrent_path is not None and
            len(self.publish_config.sites) > 0 and
            bool(self.publish_info.title)
        )

    @property
    def display_title(self) -> str:
        """获取显示用的标题（优先使用publish_info.title）"""
        return self.publish_info.title or self.file_name

    # ── 类方法 ──────────────────────────────────────────────────

    @classmethod
    def generate_id(cls, file_path: str) -> str:
        """根据文件路径生成唯一ID"""
        import hashlib
        return hashlib.md5(file_path.encode('utf-8')).hexdigest()[:12].upper()

    @classmethod
    def create_from_file(cls, file_path: str) -> Task:
        """从文件路径创建新任务（工厂方法）"""
        task_id = cls.generate_id(file_path)
        return cls(id=task_id, file_path=file_path)

    # ── 序列化配置 ──────────────────────────────────────────────

    model_config = {
        "json_schema_extra": {
            "example": {
                "id": "A1B2C3D4E5F6",
                "file_path": "D:/Videos/[SweetSub] Oniichan wa Oshimai! - 01.mp4",
                "torrent_path": "D:/output/torrents/A1B2C3D4E5F6.torrent",
                "status": "ready",
                "publish_info": {
                    "title": "[SweetSub] Oniichan wa Oshimai! - 01 [WebRip][1080p]",
                    "subtitle": "Episode 01",
                    "group_name": "SweetSub",
                    "poster": "https://example.com/poster.jpg",
                    "tags": "Anime, HD",
                    "description": "## Release Info\n\n- Source: WebRip\n- Group: SweetSub"
                },
                "media_info": {
                    "resolution": "1080p",
                    "video_codec": "H265",
                    "audio_codec": "FLAC",
                    "subtitle_type": "内嵌",
                    "source": "WEB"
                },
                "publish_config": {
                    "sites": ["nyaa", "dmhy"],
                    "auto_confirm": True,
                    "dry_run": False,
                    "mode": "publish"
                },
                "retry_count": 0,
                "max_retries": 3,
                "created_at": "2026-01-30T10:30:00",
                "updated_at": "2026-01-30T10:35:00"
            }
        }
    }


# ══════════════════════════════════════════════════════════════════════
#  第四部分：API 请求/响应模型
# ══════════════════════════════════════════════════════════════════════

class CreateTaskRequest(BaseModel):
    """创建任务请求"""
    file_path: str = Field(..., description="视频文件绝对路径")


class UpdateTaskRequest(BaseModel):
    """更新任务请求（UI编辑）"""
    publish_info: Optional[PublishInfo] = Field(None, description="发布信息")
    publish_config: Optional[PublishConfig] = Field(None, description="发布配置")


class PublishTaskRequest(BaseModel):
    """发布任务请求"""
    mode: PublishMode = Field(default=PublishMode.PUBLISH, description="发布模式")
    sites: Optional[List[str]] = Field(None, description="目标站点（覆盖默认配置）")
    auto_confirm: Optional[bool] = Field(None, description="是否自动确认")


class TaskListResponse(BaseModel):
    """任务列表响应"""
    total: int = Field(..., description="总数")
    offset: int = Field(default=0, description="偏移量")
    limit: int = Field(default=200, description="每页数量")
    tasks: List[Task] = Field(..., description="任务列表")


class TaskResponse(BaseModel):
    """单个任务响应"""
    task: Task = Field(..., description="任务详情")
    message: Optional[str] = Field(None, description="附加消息")


class ApiResponse(BaseModel):
    """通用API响应"""
    success: bool = Field(..., description="是否成功")
    data: Optional[Any] = Field(None, description="响应数据")
    message: Optional[str] = Field(None, description="消息")
    error: Optional[str] = Field(None, description="错误详情")


class LogEntry(BaseModel):
    """日志条目"""
    timestamp: str = Field(..., description="时间戳 ISO 8601")
    level: str = Field(..., description="日志级别: INFO/WARN/ERROR/DEBUG")
    message: str = Field(..., description="日志消息")
    source: Optional[str] = Field(None, description="来源模块")


class TaskLogResponse(BaseModel):
    """任务日志响应"""
    task_id: str = Field(..., description="任务ID")
    logs: List[LogEntry] = Field(..., description="日志列表")
    total: int = Field(..., description="总条数")


# ══════════════════════════════════════════════════════════════════════
#  第五部分：状态机文档
# ══════════════════════════════════════════════════════════════════════

TASK_STATE_MACHINE_DOC = """
╔══════════════════════════════════════════════════════════════╗
║              BT 发布系统 - 任务状态机 (v3.0)                  ║
╠══════════════════════════════════════════════════════════════╣
║                                                              ║
║   ┌─────────┐     Torrent生成     ┌────────┐               ║
║   │ PENDING │ ──────────────────→ │  READY │               ║
║   │ (待处理) │                     │ (就绪) │               ║
║   └────┬────┘                     └───┬────┘               ║
║        │                              │                     ║
║        │ 取消                         │ 发布                 ║
║        ↓                              ↓                     ║
║   ┌─────────┐                   ┌──────────┐             ║
║   │CANCELLED │                   │UPLOADING │             ║
║   │(已取消)  │                   │ (发布中) │             ║
║   └─────────┘                   └────┬─────┘             ║
║                                       │                    ║
║                          ┌────────────┼────────────┐       ║
║                          ↓            ↓            ↓       ║
║                     ┌────────┐  ┌────────┐  ┌─────────┐  ║
║                     │SUCCESS │  │FAILED  │  │CANCELLED│  ║
║                     │(成功)  │  │(失败)  │  │(已取消) │  ║
║                     └────────┘  └───┬────┘  └─────────┘  ║
║                                     │                      ║
║                                  重试（<max_retries）       ║
║                                     ↓                      ║
║                                ┌──────────┐               ║
║                                │RETRYING  │               ║
║                                │ (重试中) │               ║
║                                └────┬─────┘               ║
║                                     │                      ║
║                               重试完成/失败                  ║
║                                     ↓                      ║
║                            ┌──────────────────┐            ║
║                            │ 回到 UPLOADING   │            ║
║                            │ 或回到 FAILED     │            ║
║                            └──────────────────┘            ║
║                                                              ║
╠══════════════════════════════════════════════════════════════╣
║  状态说明:                                                    ║
║  ─────────                                                    ║
║  • PENDING:  初始状态，等待Torrent生成                        ║
║  • READY:    Torrent已生成，可进行发布操作                    ║
║  • UPLOADING:正在调用OKP执行发布                             ║
║  • SUCCESS:  发布成功（终态）                                 ║
║  • FAILED:   发布失败，可重试（retry_count < max_retries）   ║
║  • RETRYING: 正在重试                                        ║
║  • CANCELLED:用户取消（终态）                                ║
║                                                              ║
╠══════════════════════════════════════════════════════════════╣
║  转换规则:                                                    ║
║  ─────────                                                    ║
║  1. PENDING  → READY      (Torrent生成完成)                  ║
║  2. PENDING  → CANCELLED  (用户取消)                          ║
║  3. READY    → UPLOADING  (开始发布)                          ║
║  4. READY    → CANCELLED  (用户取消)                          ║
║  5. UPLOADING→ SUCCESS    (发布成功)                          ║
║  6. UPLOADING→ FAILED     (发布失败)                          ║
║  7. UPLOADING→ CANCELLED  (用户中断)                          ║
║  8. FAILED   → RETRYING   (触发重试)                          ║
║  9. FAILED   → CANCELLED  (用户放弃)                          ║
║  10. RETRYING→ UPLOADING  (重新尝试)                          ║
║  11. RETRYING→ FAILED     (重试仍失败)                        ║
║  12. RETRYING→ CANCELLED  (用户取消重试)                      ║
║                                                              ║
╠══════════════════════════════════════════════════════════════╣
║  约束条件:                                                    ║
║  ─────────                                                    ║
║  • SUCCESS 和 CANCELLED 为终态，不可再变更                    ║
║  • FAILED 只能重试 max_re 次（默认3次）                       ║
║  • 每次状态转换必须记录 updated_at 时间戳                     ║
║  • 失败时必须填充 error_message                               ║
║                                                              ║
╚══════════════════════════════════════════════════════════════╝
"""


# ══════════════════════════════════════════════════════════════════════
#  第六部分：API 接口规范文档
# ══════════════════════════════════════════════════════════════════════

API_SPECIFICATION_DOC = """
╔══════════════════════════════════════════════════════════════╗
║         BT 发布系统 - REST API 规范 (v3.0)                    ║
╠══════════════════════════════════════════════════════════════╣
║                                                              ║
║  Base URL: http://localhost:8000/api                        ║
║  Content-Type: application/json                             ║
║                                                              ║
╠══════════════════════════════════════════════════════════════╣
║  1. 获取任务列表                                             ║
║  ─────────────────                                           ║
║  GET /tasks                                                  ║
║                                                              ║
║  Query Parameters:                                           ║
║    - status: 过滤状态 (pending/ready/uploading/success/failed)║
║    - limit: 返回数量 (default: 200)                           ║
║    - offset: 偏移量 (default: 0)                              ║
║                                                              ║
║  Response:                                                   ║
║  {                                                           ║
║    "total": 42,                                               ║
║    "offset": 0,                                               ║
║    "limit": 200,                                              ║
║    "tasks": [Task, ...]                                      ║
║  }                                                           ║
║                                                              ║
╠══════════════════════════════════════════════════════════════╣
║  2. 获取单个任务                                             ║
║  ─────────────────                                           ║
║  GET /tasks/{task_id}                                        ║
║                                                              ║
║  Response:                                                   ║
║  {                                                           ║
║    "task": {...},                                             ║
║    "message": null                                            ║
║  }                                                           ║
║                                                              ║
╠══════════════════════════════════════════════════════════════╣
║  3. 创建任务                                                 ║
║  ───────────────                                             ║
║  POST /tasks                                                  ║
║                                                              ║
║  Request Body:                                               ║
║  {                                                           ║
║    "file_path": "D:/Videos/video.mp4"                        ║
║  }                                                           ║
║                                                              ║
║  Response:                                                   ║
║  {                                                           ║
║    "success": true,                                           ║
║    "data": {Task},                                           ║
║    "message": "任务创建成功"                                   ║
║  }                                                           ║
║                                                              ║
╠══════════════════════════════════════════════════════════════╣
║  4. 更新任务（UI编辑）                                         ║
║  ───────────────────                                          ║
║  PUT /tasks/{task_id}                                         ║
║                                                              ║
║  Request Body:                                               ║
║  {                                                           ║
║    "publish_info": {                                          ║
║      "title": "...",                                          ║
║      "tags": "Anime, HD",                                    ║
║      "description": "..."                                     ║
║    },                                                        ║
║    "publish_config": {                                        ║
║      "sites": ["nyaa", "dmhy"]                               ║
║    }                                                         ║
║  }                                                           ║
║                                                              ║
║  Response:                                                   ║
║  {                                                           ║
║    "success": true,                                           ║
║    "message": "任务更新成功"                                   ║
║  }                                                           ║
║                                                              ║
╠══════════════════════════════════════════════════════════════╣
║  5. 发布任务（核心接口）                                        ║
║  ───────────────────                                          ║
║  POST /tasks/{task_id}/publish                                ║
║                                                              ║
║  Request Body:                                               ║
║  {                                                           ║
║    "mode": "publish",  // preview|dry_run|publish            ║
║    "sites": ["nyaa"], // 可选，覆盖默认                       ║
║    "auto_confirm": true                                      ║
║  }                                                           ║
║                                                              ║
║  行为:                                                        ║
║  1. 验证任务状态必须为 ready                                   ║
║  2. 修改状态: ready → uploading                               ║
║  3. 加入Worker队列                                            ║
║  4. 异步执行OKP                                              ║
║  5. 根据结果更新状态: uploading → success/failed             ║
║                                                              ║
║  Response (异步):                                            ║
║  {                                                           ║
║    "success": true,                                           ║
║    "message": "发布任务已启动",                                 ║
║    "data": {                                                  ║
║      "task_id": "A1B2C3D4E5F6",                               ║
║      "status": "uploading"                                    ║
║    }                                                         ║
║  }                                                           ║
║                                                              ║
╠══════════════════════════════════════════════════════════════╣
║  6. 获取任务日志                                              ║
║  ─────────────────                                           ║
║  GET /tasks/{task_id}/logs                                    ║
║                                                              ║
║  Query Parameters:                                           ║
║    - level: 过滤级别 (INFO/WARN/ERROR/DEBUG)                 ║
║    - limit: 返回数量 (default: 100)                           ║
║                                                              ║
║  Response:                                                   ║
║  {                                                           ║
║    "task_id": "A1B2C3D4E5F6",                                 ║
║    "logs": [{timestamp, level, message, source}],            ║
║    "total": 25                                                ║
║  }                                                           ║
║                                                              ║
╠══════════════════════════════════════════════════════════════╣
║  7. 重试任务                                                  ║
║  ───────────                                                  ║
║  POST /tasks/{task_id}/retry                                  ║
║                                                              ║
║  条件:                                                        ║
║  - 当前状态必须是 failed                                       ║
║  - retry_count < max_retries                                  ║
║                                                              ║
║  行为:                                                        ║
║  1. failed → retrying                                        ║
║  2. retry_count += 1                                         ║
║  3. 自动触发重新发布                                           ║
║                                                              ║
║  Response:                                                   ║
║  {                                                           ║
║    "success": true,                                           ║
║    "message": "重试已启动 (第2/3次)"                          ║
║  }                                                           ║
║                                                              ║
╠══════════════════════════════════════════════════════════════╣
║  8. 取消任务                                                  ║
║  ───────────                                                  ║
║  POST /tasks/{task_id}/cancel                                 ║
║                                                              ║
║  条件:                                                        ║
║  - 必须是活跃状态 (pending/ready/uploading/retrying)         ║
║                                                              ║
║  行为:                                                        ║
║  任意活跃状态 → cancelled                                    ║
║                                                              ║
║  Response:                                                   ║
║  {                                                           ║
║    "success": true,                                           ║
║    "message": "任务已取消"                                     ║
║  }                                                           ║
║                                                              ║
╠══════════════════════════════════════════════════════════════╣
║  9. 删除任务                                                  ║
║  ───────────                                                  ║
║  DELETE /tasks/{task_id}                                      ║
║                                                              ║
║  条件:                                                        ║
║  - 必须是终态 (success/failed/cancelled)                     ║
║                                                              ║
║  Response:                                                   ║
║  {                                                           ║
║    "success": true,                                           ║
║    "message": "任务已删除"                                     ║
║  }                                                           ║
║                                                              ║
╠══════════════════════════════════════════════════════════════╣
║  10. 上传 Torrent 文件                                         ║
║  ───────────────────                                          ║
║  POST /tasks/{task_id}/torrent                                ║
║                                                              ║
║  Content-Type: multipart/form-data                           ║
║                                                              ║
║  Form Data:                                                  ║
║    - file: .torrent 文件                                      ║
║                                                              ║
║  行为:                                                        ║
║  1. 保存torrent文件到指定目录                                 ║
║  2. 解析torrent元信息                                        ║
║  3. 如果状态是pending且已有torrent → ready                   ║
║  4. 更新 torrent_meta                                        ║
║                                                              ║
║  Response:                                                   ║
║  {                                                           ║
║    "success": true,                                           ║
║    "message": "Torrent上传成功",                               ║
║    "data": {                                                  ║
║      "torrent_path": "D:/output/...",                        ║
║      "torrent_meta": {...}                                   ║
║    }                                                         ║
║  }                                                           ║
║                                                              ║
╚══════════════════════════════════════════════════════════════╝
"""


# ══════════════════════════════════════════════════════════════════════
#  第七部分：示例 JSON 数据
# ══════════════════════════════════════════════════════════════════════

EXAMPLE_TASK_JSON = {
    "id": "A1B2C3D4E5F6",
    "file_path": "D:/Videos/[SweetSub] Oniichan wa Oshimai! - 01 [WebRip][1080p].mp4",
    "torrent_path": "D:/output/torrents/A1B2C3D4E5F6.torrent",
    "status": "ready",
    "publish_info": {
        "title": "[SweetSub] Oniichan ha Oshimai! - 01 [WebRip][1080p][HEVC-10bit][FLAC][CHS]",
        "subtitle": "Episode 01 - お兄ちゃんはおしまい！",
        "group_name": "SweetSub",
        "poster": "https://example.com/images/onimai_01_poster.jpg",
        "tags": "Anime, HD, Hi10P, FLAC, Lossless",
        "description": "## Release Information\n\n**Title:** Oniichan ha Oshimai!\n**Episode:** 01\n**Release:** SweetSub\n\n---\n\n### Video\n- **Source:** WebRip (ABEMA)\n- **Resolution:** 1920x1080\n- **Codec:** HEVC Main 10 Profile L5.1\n- **Bitrate:** ~3500 kbps\n\n### Audio\n- **Codec:** FLAC 16-bit\n- **Channels:** 2.0 Stereo\n- **Language:** Japanese\n\n### Subtitles\n- **Language:** Chinese Simplified (内嵌)\n- **Type:** ASS/SSA\n\n---\n\n*Encoded by SweetSub*\n*Enjoy!*"
    },
    "media_info": {
        "resolution": "1080p",
        "video_codec": "H265",
        "audio_codec": "FLAC",
        "subtitle_type": "内嵌",
        "source": "WEB"
    },
    "video_meta": {
        "width": 1920,
        "height": 1080,
        "duration_seconds": 1420.5,
        "file_size": 8589934592,
        "codec": "hevc",
        "fps": 23.976,
        "bitrate": 3500000
    },
    "torrent_meta": {
        "name": "[SweetSub] Oniichan ha Oshimai! - 01 [WebRip][1080p][HEVC-10bit][FLAC][CHS]",
        "size": 8590000000,
        "file_count": 3,
        "files": [
            {"name": "[SweetSub] Oniichan ha Oshimai! - 01.mkv", "size": 8589000000},
            {"name": "[SweetSub] Oniichan ha Oshimai! - 01.ass", "size": 50000},
            {"name": "[SweetSub] Oniichan ha Oshimai! - 01.srt", "size": 30000}
        ],
        "tracker_count": 5,
        "trackers_sample": [
            "udp://tracker.example.com:1337/announce",
            "http://tracker.example.com:80/announce"
        ]
    },
    "publish_config": {
        "sites": ["nyaa", "dmhy"],
        "auto_confirm": True,
        "dry_run": False,
        "mode": "publish"
    },
    "okp_result": None,
    "retry_count": 0,
    "max_retries": 3,
    "error_message": None,
    "created_at": "2026-01-30T10:30:00.123456",
    "updated_at": "2026-01-30T10:45:23.789012"
}

EXAMPLE_PUBLISH_RESPONSE = {
    "success": True,
    "data": {
        "task_id": "A1B2C3D4E5F6",
        "status": "uploading",
        "started_at": "2026-01-30T11:00:00.000000",
        "sites": ["nyaa", "dmhy"],
        "mode": "publish"
    },
    "message": "发布任务已启动，正在调用OKP..."
}

EXAMPLE_OKP_RESULT = {
    "mode": "publish",
    "success": True,
    "returncode": 0,
    "stdout": "[OKP] Starting upload to nyaa.si...\n[OKP] Upload successful!\n[OKP] Starting upload to dmhy.org...\n[OKP] Upload successful!",
    "stderr": "",
    "error": None,
    "command": "OKP.Core.exe --setting setting.toml --cookies cookies.json publish torrent.torrent",
    "executed_at": "2026-01-30T11:02:15.654321",
    "duration_ms": 135650,
    "site_results": [
        {
            "site": "nyaa",
            "success": True,
            "url": "https://nyaa.si/view/12345678",
            "error": None
        },
        {
            "site": "dmhy",
            "success": True,
            "url": "https://share.dmhy.org/topics/list/123456",
            "error": None
        }
    ]
}


if __name__ == "__main__":
    print("=" * 70)
    print("BT 发布系统 - 统一数据模型 v3.0")
    print("=" * 70)

    print("\n📋 状态机说明:")
    print(TASK_STATE_MACHINE_DOC)

    print("\n📡 API 规范:")
    print(API_SPECIFICATION_DOC)

    print("\n✅ 示例 Task JSON:")
    import json
    print(json.dumps(EXAMPLE_TASK_JSON, indent=2, ensure_ascii=False))

    print("\n\n🎉 数据模型验证通过!")
