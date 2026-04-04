
from pathlib import Path
from typing import List
import torf
from src.logger import setup_logger

logger = setup_logger(__name__)


class TorrentBuilder:
    @staticmethod
    def create_torrent(
        file_path,
        tracker_urls,
        output_dir
    ):
        try:
            file_path = Path(file_path)
            output_dir = Path(output_dir)
            output_dir.mkdir(parents=True, exist_ok=True)
            
            output_path = output_dir / f"{file_path.stem}.torrent"
            
            logger.info(f"开始生成 torrent 文件: {file_path.name}")
            logger.info(f"Tracker 数量: {len(tracker_urls)} 个")
            logger.info(f"输出路径: {output_path}")
            
            tracker_list = [[url] for url in tracker_urls]
            
            torrent = torf.Torrent(
                path=str(file_path),
                trackers=tracker_list,
                private=False
            )
            
            torrent.generate(callback=lambda *args, **kwargs: None)
            torrent.write(str(output_path))
            
            logger.info(f"Torrent 生成成功: {output_path}")
            return str(output_path)
            
        except Exception as e:
            logger.error(f"Torrent 生成失败: {e}", exc_info=True)
            return None

