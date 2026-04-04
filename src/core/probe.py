
from pathlib import Path
from typing import Dict, Optional
import pymediainfo
from src.logger import setup_logger

logger = setup_logger(__name__)

class Probe:
    @staticmethod
    def get_video_info(file_path: Path) -> Optional[Dict]:
        try:
            media_info = pymediainfo.MediaInfo.parse(str(file_path))
            
            video_track = None
            for track in media_info.tracks:
                if track.track_type == "Video":
                    video_track = track
                    break
            
            if not video_track:
                logger.warning(f"未找到视频轨道: {file_path}")
                return None
            
            info = {
                "width": int(video_track.width or 0),
                "height": int(video_track.height or 0),
                "codec": video_track.codec_id or video_track.format or "Unknown",
                "duration_ms": int(float(video_track.duration or 0)),
                "file_size": file_path.stat().st_size
            }
            
            logger.debug(f"提取视频信息成功: {file_path}")
            return info
            
        except Exception as e:
            logger.error(f"提取视频信息失败 {file_path}: {e}")
            return None

