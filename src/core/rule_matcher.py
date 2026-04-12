"""
规则匹配引擎 - 从文件名中提取结构化元数据
============================================

职责：
  - 从原始文件名中识别字幕组、作品名、季数、集数、来源、分辨率、字幕等信息
  - 基于 config/rules.yaml 中的映射规则进行别名转换
  - 返回结构化的匹配结果（MatchResult）

不负责：
  - 标题格式化生成（由 TitleNormalizer 负责）
  - UI 交互逻辑
"""

import re
import yaml
from pathlib import Path
from dataclasses import dataclass, field
from typing import Optional, Dict, List, Any

from src.logger import setup_logger

logger = setup_logger(__name__)

RULES_PATH = Path(__file__).parent.parent.parent / "config" / "rules.yaml"


@dataclass
class MatchResult:
    group_raw: str = ""
    group_alias: str = ""
    series_raw: str = ""
    series_chinese: str = ""
    season_raw: str = ""
    season_display: str = ""
    season_number: int = 0
    episode_raw: str = ""
    episode_display: str = ""
    source_raw: str = ""
    source_display: str = ""
    quality_raw: str = ""
    quality_display: str = ""
    video_codec_raw: str = ""
    video_codec_display: str = ""
    audio_codec_raw: str = ""
    audio_codec_display: str = ""
    subtitle_raw: str = ""
    subtitle_display: str = ""
    original_filename: str = ""
    matched_rules: List[str] = field(default_factory=list)
    unmatched_parts: List[str] = field(default_factory=list)
    complete_match: bool = False
    needs_review: bool = True
    category: str = ""
    auto_tags: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "group_raw": self.group_raw,
            "group_alias": self.group_alias,
            "series_raw": self.series_raw,
            "series_chinese": self.series_chinese,
            "season_raw": self.season_raw,
            "season_display": self.season_display,
            "season_number": self.season_number,
            "episode_raw": self.episode_raw,
            "episode_display": self.episode_display,
            "source_raw": self.source_raw,
            "source_display": self.source_display,
            "quality_raw": self.quality_raw,
            "quality_display": self.quality_display,
            "video_codec_raw": self.video_codec_raw,
            "video_codec_display": self.video_codec_display,
            "audio_codec_raw": self.audio_codec_raw,
            "audio_codec_display": self.audio_codec_display,
            "subtitle_raw": self.subtitle_raw,
            "subtitle_display": self.subtitle_display,
            "original_filename": self.original_filename,
            "matched_rules": self.matched_rules,
            "unmatched_parts": self.unmatched_parts,
            "complete_match": self.complete_match,
            "needs_review": self.needs_review,
            "category": self.category,
            "auto_tags": self.auto_tags,
        }

    @classmethod
    def from_dict(cls, data: Dict) -> "MatchResult":
        if not data:
            return cls()
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})


class RuleMatcher:
    _instance = None
    _config_cache = None
    _config_mtime = 0.0

    def __init__(self, config_path: Optional[str] = None):
        self.config_path = Path(config_path) if config_path else RULES_PATH
        self.config = self._load_config()
        self.logger = setup_logger(f"{__name__}.RuleMatcher")

    def _load_config(self) -> Dict:
        if not self.config_path.exists():
            logger.warning(f"规则配置文件不存在: {self.config_path}，使用空规则")
            return {}

        try:
            mtime = self.config_path.stat().st_mtime
            if RuleMatcher._config_cache and abs(mtime - RuleMatcher._config_mtime) < 1.0:
                return RuleMatcher._config_cache

            with open(self.config_path, "r", encoding="utf-8") as f:
                config = yaml.safe_load(f) or {}

            RuleMatcher._config_cache = config
            RuleMatcher._config_mtime = mtime
            logger.debug(f"规则配置已加载: {self.config_path}")
            return config
        except Exception as e:
            logger.error(f"加载规则配置失败: {e}")
            return RuleMatcher._config_cache or {}

    def reload_config(self):
        RuleMatcher._config_cache = None
        self.config = self._load_config()

    def match(self, filename: str, metadata: Optional[Dict] = None) -> MatchResult:
        self.config = self._load_config()

        stem = Path(filename).stem if "." in filename else filename
        result = MatchResult(original_filename=stem)

        self._match_group(stem, result)
        self._match_series(stem, result)
        self._match_season(stem, result)
        self._match_episode(stem, result)
        self._match_source(stem, result)
        self._match_quality(stem, result)
        self._match_video_codec(stem, result)
        self._match_audio_codec(stem, result)
        self._match_subtitle(stem, result)
        self._infer_category(stem, result)
        self._infer_tags(stem, result)
        self._evaluate_completeness(result)

        self._log_result(result)
        return result

    def _match_group(self, filename: str, result: MatchResult):
        group_match = re.search(r'\[([^\[\]]{2,40})\]', filename)
        if not group_match:
            return

        raw_group = group_match.group(1).strip()
        skip_patterns = [
            r'^(1080|720|2160|4K|HEVC|H\.?26[45]|AVC|VP9|AV1|AAC|FLAC|AC3|DTS|Opus)$',
            r'^(WebRip|WEB-?DL|WEB|BD|BluRay|BDRip|BDMV|TVRip|HDTV|DVD)$',
            r'^(Hi10P|10bit|8bit|HDR|SDR|DoVi)$',
            r'^\d{1,3}$',
            r'^(ASSx\d|SRTx\d|CHS|CHT|JPTC|GB|BIG5|简繁|简日|繁日)$',
        ]

        for pat in skip_patterns:
            if re.match(pat, raw_group, re.IGNORECASE):
                return

        result.group_raw = raw_group

        aliases = self.config.get("group_aliases", [])
        sorted_aliases = sorted(aliases, key=lambda x: x.get("priority", 0), reverse=True)

        for alias_rule in sorted_aliases:
            pattern = alias_rule.get("pattern", "")
            if not pattern:
                continue
            if re.search(re.escape(pattern), raw_group, re.IGNORECASE):
                result.group_alias = alias_rule.get("alias", raw_group)
                result.matched_rules.append(f"group:{pattern}")
                return

        result.group_alias = raw_group
        result.matched_rules.append(f"group:fallback({raw_group})")

    def _match_series(self, filename: str, result: MatchResult):
        working = filename

        if result.group_raw:
            working = re.sub(r'\[' + re.escape(result.group_raw) + r'\]', '', working).strip()

        working = re.sub(r'\[\d{1,3}\]', '', working)
        working = re.sub(r'\[(?:WebRip|WEB-?DL|WEB|BD|BluRay|BDRip|BDMV|TVRip|HDTV|DVD)\]',
                         '', working, flags=re.IGNORECASE)
        working = re.sub(r'\[(?:HEVC|H\.?26[45]|AVC|VP9|AV1)[^\]]*\]', '', working, flags=re.IGNORECASE)
        working = re.sub(r'\[\d{3,4}[pP]\]', '', working)
        working = re.sub(r'\[(?:AAC|FLAC|AC3|DTS|Opus)[^\]]*\]', '', working, flags=re.IGNORECASE)
        working = re.sub(r'\[(?:ASSx\d|SRTx\d|CHS|CHT|JPTC|GB|BIG5|简繁|简日|繁日)[^\]]*\]',
                         '', working, flags=re.IGNORECASE)
        working = re.sub(r'\bS\d+\b', '', working)
        working = re.sub(r'\s*[·\-–—]\s*$', '', working)
        working = re.sub(r'\s{2,}', ' ', working).strip()

        if not working:
            return

        aliases = self.config.get("series_aliases", [])
        sorted_aliases = sorted(aliases, key=lambda x: x.get("priority", 0), reverse=True)

        for alias_rule in sorted_aliases:
            pattern = alias_rule.get("pattern", "")
            if not pattern:
                continue
            if re.search(re.escape(pattern), filename, re.IGNORECASE):
                result.series_raw = pattern
                result.series_chinese = alias_rule.get("chinese_name", "")
                result.matched_rules.append(f"series:{pattern}")

                if alias_rule.get("season_override"):
                    num_to_cn = {1: "一", 2: "二", 3: "三", 4: "四", 5: "五",
                                 6: "六", 7: "七", 8: "八", 9: "九", 10: "十",
                                 11: "十一", 12: "十二"}
                    result.season_number = alias_rule["season_override"]
                    cn_n = num_to_cn.get(result.season_number, str(result.season_number))
                    result.season_display = f"第{cn_n}季"
                    result.matched_rules.append(f"season:override({alias_rule['season_override']})")
                return

        title_candidate = working
        title_candidate = re.sub(r'\s*[\-\_]\s*\d{1,3}$', '', title_candidate).strip()
        title_candidate = re.sub(r'\[[^\]]*\]', '', title_candidate).strip()
        title_candidate = re.sub(r'\s{2,}', ' ', title_candidate).strip()

        if len(title_candidate) > 2:
            result.series_raw = title_candidate
            result.unmatched_parts.append(f"series:unrecognized({title_candidate})")

    def _match_season(self, filename: str, result: MatchResult):
        if result.season_number > 0:
            return

        mappings = self.config.get("season_mappings", [])
        for rule in mappings:
            pattern = rule.get("pattern", "")
            group_idx = rule.get("group", 1)
            fmt = rule.get("format", "第{n}季")

            m = re.search(pattern, filename, re.IGNORECASE)
            if m:
                try:
                    raw_val = m.group(group_idx)
                    cn_nums = {"一": 1, "二": 2, "三": 3, "四": 4, "五": 5,
                               "六": 6, "七": 7, "八": 8, "九": 9, "十": 10}
                    num_to_cn = {1: "一", 2: "二", 3: "三", 4: "四", 5: "五",
                                 6: "六", 7: "七", 8: "八", 9: "九", 10: "十"}
                    n = cn_nums.get(raw_val, int(raw_val))
                    result.season_raw = m.group(0)
                    result.season_number = n
                    cn_n = num_to_cn.get(n, str(n))
                    result.season_display = fmt.format(n=cn_n)
                    result.matched_rules.append(f"season:{pattern}")
                    return
                except (ValueError, IndexError):
                    continue

    def _match_episode(self, filename: str, result: MatchResult):
        patterns = self.config.get("episode_patterns", [])
        sorted_patterns = sorted(patterns, key=lambda x: x.get("priority", 0), reverse=True)

        for rule in sorted_patterns:
            pattern = rule.get("pattern", "")
            group_idx = rule.get("group", 1)

            m = re.search(pattern, filename, re.IGNORECASE)
            if m:
                try:
                    ep = m.group(group_idx)
                    result.episode_raw = m.group(0)
                    result.episode_display = ep
                    result.matched_rules.append(f"episode:{pattern}")
                    return
                except (IndexError, ValueError):
                    continue

    def _match_source(self, filename: str, result: MatchResult):
        mappings = self.config.get("source_mappings", [])
        for rule in mappings:
            pattern = rule.get("pattern", "")
            if re.search(pattern, filename, re.IGNORECASE):
                result.source_raw = pattern
                result.source_display = rule.get("display", pattern)
                result.matched_rules.append(f"source:{pattern}")
                return

    def _match_quality(self, filename: str, result: MatchResult):
        mappings = self.config.get("quality_mappings", [])
        for rule in mappings:
            pattern = rule.get("pattern", "")
            if re.search(pattern, filename, re.IGNORECASE):
                result.quality_raw = pattern
                result.quality_display = rule.get("display", pattern)
                result.matched_rules.append(f"quality:{pattern}")
                return

    def _match_video_codec(self, filename: str, result: MatchResult):
        codecs_found = []
        mappings = self.config.get("video_codec_mappings", [])
        for rule in mappings:
            pattern = rule.get("pattern", "")
            if re.search(pattern, filename, re.IGNORECASE):
                codecs_found.append(rule.get("display", pattern))

        if codecs_found:
            result.video_codec_raw = ",".join(codecs_found)
            result.video_codec_display = " ".join(codecs_found)
            result.matched_rules.append(f"video_codec:{','.join(codecs_found)}")

    def _match_audio_codec(self, filename: str, result: MatchResult):
        mappings = self.config.get("audio_codec_mappings", [])
        for rule in mappings:
            pattern = rule.get("pattern", "")
            if re.search(pattern, filename, re.IGNORECASE):
                result.audio_codec_raw = pattern
                result.audio_codec_display = rule.get("display", pattern)
                result.matched_rules.append(f"audio_codec:{pattern}")
                return

    def _match_subtitle(self, filename: str, result: MatchResult):
        styles_found = []
        mappings = self.config.get("subtitle_style_mappings", [])

        for rule in mappings:
            pattern = rule.get("pattern", "")
            if re.search(pattern, filename, re.IGNORECASE):
                styles_found.append(rule.get("display", pattern))

        if styles_found:
            result.subtitle_raw = ",".join(styles_found)
            result.subtitle_display = styles_found[0]
            result.matched_rules.append(f"subtitle:{','.join(styles_found)}")
        else:
            if re.search(r'\.ass', filename, re.IGNORECASE):
                result.subtitle_display = "内封字幕"
            elif re.search(r'\.srt', filename, re.IGNORECASE):
                result.subtitle_display = "内封字幕"

    def _infer_category(self, filename: str, result: MatchResult):
        rules = self.config.get("category_rules", [])
        for rule in rules:
            keywords = rule.get("keywords", [])
            if any(re.search(kw, filename, re.IGNORECASE) for kw in keywords):
                result.category = rule.get("category", "")
                return

        if result.series_raw:
            result.category = "Anime"

    def _infer_tags(self, filename: str, result: MatchResult):
        tags = set()
        rules = self.config.get("tag_rules", [])

        for rule in rules:
            condition = rule.get("condition", "")
            rule_tags = rule.get("tags", [])

            try:
                ctx = {
                    "quality": result.quality_display,
                    "source": result.source_display,
                    "video_codec": result.video_codec_display,
                    "audio_codec": result.audio_codec_display,
                    "filename": filename,
                }

                if eval(condition, {"__builtins__": {}}, ctx):
                    tags.update(rule_tags)
            except Exception:
                continue

        result.auto_tags = sorted(tags)

    def _evaluate_completeness(self, result: MatchResult):
        critical_fields = [
            (result.group_alias, "group"),
            (result.series_raw, "series"),
            (result.episode_display, "episode"),
        ]

        missing = [name for val, name in critical_fields if not val]
        result.complete_match = len(missing) == 0
        result.needs_review = len(missing) > 0 or not result.series_chinese

        if missing:
            result.unmatched_parts.append(f"missing:{','.join(missing)}")

    def _log_result(self, result: MatchResult):
        self.logger.info(f"规则匹配结果:")
        self.logger.info(f"  原始文件名: {result.original_filename}")
        self.logger.info(f"  字幕组: {result.group_raw} → {result.group_alias}")
        self.logger.info(f"  作品名: {result.series_raw} → {result.series_chinese}")
        self.logger.info(f"  季数: {result.season_raw} → {result.season_display} (S{result.season_number})")
        self.logger.info(f"  集数: {result.episode_raw} → {result.episode_display}")
        self.logger.info(f"  来源: {result.source_raw} → {result.source_display}")
        self.logger.info(f"  分辨率: {result.quality_raw} → {result.quality_display}")
        self.logger.info(f"  视频编码: {result.video_codec_display}")
        self.logger.info(f"  音频编码: {result.audio_codec_display}")
        self.logger.info(f"  字幕: {result.subtitle_raw} → {result.subtitle_display}")
        self.logger.info(f"  分类: {result.category}")
        self.logger.info(f"  自动标签: {result.auto_tags}")
        self.logger.info(f"  完全匹配: {result.complete_match}")
        self.logger.info(f"  需要人工确认: {result.needs_review}")
        self.logger.info(f"  命中规则: {result.matched_rules}")
        if result.unmatched_parts:
            self.logger.info(f"  未匹配部分: {result.unmatched_parts}")
