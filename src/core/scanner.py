
import json
import hashlib
from pathlib import Path
from typing import Set
from src.config import DB_PATH
from src.logger import setup_logger

logger = setup_logger(__name__)

class Scanner:
    def __init__(self):
        self.db_path = DB_PATH()
        self.processed_files: Set[str] = self._load_db()
    
    def _load_db(self) -> Set[str]:
        if self.db_path.exists():
            try:
                with open(self.db_path, "r", encoding="utf-8") as f:
                    return set(json.load(f))
            except Exception as e:
                logger.warning(f"无法加载数据库: {e}")
        return set()
    
    def _save_db(self) -> None:
        with open(self.db_path, "w", encoding="utf-8") as f:
            json.dump(list(self.processed_files), f)
    
    @staticmethod
    def _get_file_hash(file_path: Path) -> str:
        hash_obj = hashlib.md5()
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(8192), b""):
                hash_obj.update(chunk)
        return hash_obj.hexdigest()
    
    def is_processed(self, file_path: Path) -> bool:
        file_hash = self._get_file_hash(file_path)
        return file_hash in self.processed_files
    
    def mark_processed(self, file_path: Path) -> None:
        file_hash = self._get_file_hash(file_path)
        self.processed_files.add(file_hash)
        self._save_db()
        logger.info(f"标记文件已处理: {file_path}")

