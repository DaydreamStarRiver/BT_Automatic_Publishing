
from pathlib import Path
from typing import Dict
from src.logger import setup_logger

logger = setup_logger(__name__)

class Normalizer:
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

