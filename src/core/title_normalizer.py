"""
标题归一化生成器 - 将匹配结果转换为标准化发布标题
====================================================

职责：
  - 接收 RuleMatcher 的 MatchResult
  - 根据配置的标题格式模板生成标准化标题
  - 生成候选标题列表（当信息不完整时）
  - 支持多种格式模板和自定义格式

不负责：
  - 文件名解析（由 RuleMatcher 负责）
  - UI 交互逻辑
"""

import re
import yaml
from pathlib import Path
from typing import Dict, List, Optional

from src.core.rule_matcher import MatchResult
from src.logger import setup_logger

logger = setup_logger(__name__)

RULES_PATH = Path(__file__).parent.parent.parent / "config" / "rules.yaml"


class TitleNormalizer:
    _config_cache = None
    _config_mtime = 0.0

    def __init__(self, config_path: Optional[str] = None):
        self.config_path = Path(config_path) if config_path else RULES_PATH
        self.config = self._load_config()
        self.logger = setup_logger(f"{__name__}.TitleNormalizer")

    def _load_config(self) -> Dict:
        if not self.config_path.exists():
            return {}

        try:
            mtime = self.config_path.stat().st_mtime
            if TitleNormalizer._config_cache and abs(mtime - TitleNormalizer._config_mtime) < 1.0:
                return TitleNormalizer._config_cache

            with open(self.config_path, "r", encoding="utf-8") as f:
                config = yaml.safe_load(f) or {}

            TitleNormalizer._config_cache = config
            TitleNormalizer._config_mtime = mtime
            return config
        except Exception as e:
            logger.error(f"加载标题格式配置失败: {e}")
            return TitleNormalizer._config_cache or {}

    def generate_title(self, match_result: MatchResult) -> str:
        self.config = self._load_config()

        if match_result.series_chinese:
            fmt = self.config.get("title_format",
                                  "[{group}] {chinese_title} {season} / {original_title} [{episode}][{source}][{quality}][{subtitles}]")
        elif match_result.series_raw:
            fmt = self.config.get("title_format_no_chinese",
                                  "[{group}] {original_title} [{episode}][{source}][{quality}][{subtitles}]")
        else:
            return match_result.original_filename

        variables = self._build_variables(match_result)
        title = self._format_title(fmt, variables)
        title = self._clean_title(title)

        self.logger.info(f"生成标题: {title}")
        return title

    def generate_candidates(self, match_result: MatchResult) -> List[Dict]:
        candidates = []

        primary = self.generate_title(match_result)
        candidates.append({
            "title": primary,
            "source": "rule_match",
            "confidence": "high" if match_result.complete_match else "medium",
            "description": self._describe_match(match_result),
        })

        if match_result.series_chinese and match_result.series_raw:
            fmt_no_season = "[{group}] {chinese_title} / {original_title} [{episode}][{source}][{quality}][{subtitles}]"
            variables = self._build_variables(match_result)
            variables["season"] = ""
            title_no_season = self._format_title(fmt_no_season, variables)
            title_no_season = self._clean_title(title_no_season)
            if title_no_season != primary:
                candidates.append({
                    "title": title_no_season,
                    "source": "variant_no_season",
                    "confidence": "medium",
                    "description": "不含季数的变体",
                })

        if match_result.season_number > 0:
            fmt_season_num = "[{group}] {chinese_title} S{season_number} / {original_title} [{episode}][{source}][{quality}][{subtitles}]"
            variables = self._build_variables(match_result)
            variables["season_number"] = str(match_result.season_number)
            title_s_num = self._format_title(fmt_season_num, variables)
            title_s_num = self._clean_title(title_s_num)
            if title_s_num != primary:
                candidates.append({
                    "title": title_s_num,
                    "source": "variant_season_number",
                    "confidence": "medium",
                    "description": "使用 S{n} 季数格式",
                })

        if not match_result.complete_match:
            candidates.append({
                "title": match_result.original_filename,
                "source": "fallback_original",
                "confidence": "low",
                "description": "原始文件名（规则匹配不完整）",
            })

        return candidates

    def _build_variables(self, mr: MatchResult) -> Dict:
        group = mr.group_alias or mr.group_raw or ""
        chinese_title = mr.series_chinese or ""
        original_title = mr.series_raw or ""
        season = mr.season_display or ""
        season_number = str(mr.season_number) if mr.season_number else ""
        episode = mr.episode_display or ""
        source = mr.source_display or ""
        quality = mr.quality_display or ""
        subtitles = mr.subtitle_display or ""

        if original_title and season_number:
            if re.search(r'\bS' + re.escape(season_number) + r'\b', original_title, re.IGNORECASE):
                original_with_season = original_title
            else:
                original_with_season = f"{original_title} S{season_number}"
        else:
            original_with_season = original_title

        return {
            "group": group,
            "chinese_title": chinese_title,
            "original_title": original_with_season if season_number else original_title,
            "original_title_raw": original_title,
            "season": season,
            "season_number": season_number,
            "episode": episode,
            "source": source,
            "quality": quality,
            "subtitles": subtitles,
            "video_codec": mr.video_codec_display or "",
            "audio_codec": mr.audio_codec_display or "",
        }

    def _format_title(self, fmt: str, variables: Dict) -> str:
        result = fmt
        for key, value in variables.items():
            placeholder = "{" + key + "}"
            result = result.replace(placeholder, str(value) if value else "")
        return result

    def _clean_title(self, title: str) -> str:
        title = re.sub(r'\[\s*\]', '', title)
        title = re.sub(r'\s{2,}', ' ', title)
        title = re.sub(r'\s*/\s*', ' / ', title)
        title = re.sub(r'\[\s+', '[', title)
        title = re.sub(r'\s+\]', ']', title)
        title = re.sub(r'^\s+|\s+$', '', title)
        title = re.sub(r'\s+/', '/', title)
        title = re.sub(r'/\s+', '/', title)
        title = re.sub(r'\s+]', ']', title)
        title = re.sub(r'\[\s+', '[', title)
        title = re.sub(r'\s{2,}', ' ', title)
        title = title.strip()
        title = re.sub(r'\s*/\s*', ' / ', title)
        return title

    def _describe_match(self, mr: MatchResult) -> str:
        parts = []
        if mr.group_alias:
            parts.append(f"组: {mr.group_alias}")
        if mr.series_chinese:
            parts.append(f"作品: {mr.series_chinese}")
        elif mr.series_raw:
            parts.append(f"作品: {mr.series_raw}(未匹配中文)")
        if mr.season_display:
            parts.append(f"季: {mr.season_display}")
        if mr.episode_display:
            parts.append(f"集: {mr.episode_display}")
        if mr.source_display:
            parts.append(f"来源: {mr.source_display}")
        if mr.quality_display:
            parts.append(f"分辨率: {mr.quality_display}")
        if mr.subtitle_display:
            parts.append(f"字幕: {mr.subtitle_display}")

        if mr.needs_review:
            missing = []
            if not mr.group_alias:
                missing.append("组名")
            if not mr.series_chinese:
                missing.append("中文标题")
            if not mr.episode_display:
                missing.append("集数")
            if missing:
                parts.append(f"⚠️ 缺少: {', '.join(missing)}")

        return " | ".join(parts)
