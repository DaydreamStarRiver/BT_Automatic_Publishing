from pathlib import Path
from typing import Dict, Optional
from src.logger import setup_logger
from src.core.rule_matcher import RuleMatcher, MatchResult
from src.core.title_normalizer import TitleNormalizer

logger = setup_logger(__name__)

class Normalizer:
    _rule_matcher = None
    _title_normalizer = None

    @classmethod
    def _get_rule_matcher(cls) -> RuleMatcher:
        if cls._rule_matcher is None:
            cls._rule_matcher = RuleMatcher()
        return cls._rule_matcher

    @classmethod
    def _get_title_normalizer(cls) -> TitleNormalizer:
        if cls._title_normalizer is None:
            cls._title_normalizer = TitleNormalizer()
        return cls._title_normalizer

    @staticmethod
    def _get_resolution_label(width: int, height: int) -> str:
        if height >= 2160:
            return "4K"
        elif height >= 1440:
            return "1440p"
        elif height >= 1080:
            return "1080p"
        elif height >= 720:
            return "720p"
        else:
            return "SD"

    @staticmethod
    def _normalize_codec(codec: str) -> str:
        codec_lower = codec.lower()
        if any(x in codec_lower for x in ["h264", "h.264", "avc"]):
            return "H264"
        elif any(x in codec_lower for x in ["h265", "h.265", "hevc"]):
            return "H265"
        elif any(x in codec_lower for x in ["vp9"]):
            return "VP9"
        elif any(x in codec_lower for x in ["av1"]):
            return "AV1"
        return codec

    @staticmethod
    def normalize(file_path: Path, raw_info: Dict) -> Dict:
        resolution = Normalizer._get_resolution_label(raw_info["width"], raw_info["height"])
        codec = Normalizer._normalize_codec(raw_info["codec"])

        task = {
            "file_path": str(file_path.absolute()),
            "title": file_path.stem,
            "resolution": resolution,
            "codec": codec,
            "duration": raw_info["duration_ms"] // 1000,
            "size": raw_info["file_size"]
        }

        logger.info(f"标准化任务: {task['title']} ({task['resolution']}, {task['codec']})")
        return task

    @classmethod
    def normalize_with_rules(cls, file_path: Path, raw_info: Dict) -> Dict:
        base = cls.normalize(file_path, raw_info)

        matcher = cls._get_rule_matcher()
        normalizer = cls._get_title_normalizer()

        match_result = matcher.match(str(file_path), raw_info)
        title = normalizer.generate_title(match_result)
        candidates = normalizer.generate_candidates(match_result)

        base["title"] = title
        base["match_result"] = match_result.to_dict()
        base["title_candidates"] = candidates
        base["needs_review"] = match_result.needs_review
        base["complete_match"] = match_result.complete_match

        if match_result.group_alias:
            base["group_name"] = match_result.group_alias
        if match_result.category:
            base["category"] = match_result.category
        if match_result.source_display:
            base["source"] = match_result.source_display
        if match_result.quality_display:
            base["resolution"] = match_result.quality_display
        if match_result.subtitle_display:
            base["subtitle_type"] = match_result.subtitle_display
        if match_result.video_codec_display:
            base["video_codec_detail"] = match_result.video_codec_display
        if match_result.audio_codec_display:
            base["audio_codec_detail"] = match_result.audio_codec_display
        if match_result.auto_tags:
            base["auto_tags"] = match_result.auto_tags

        logger.info(f"规则匹配标题: {title}")
        if match_result.needs_review:
            logger.warning(f"标题需要人工确认: 缺少字段 {match_result.unmatched_parts}")

        return base
