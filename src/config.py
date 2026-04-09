
import yaml
from pathlib import Path

BASE_DIR = Path(__file__).parent.parent
CONFIG_PATH = BASE_DIR / "config.yaml"

DEFAULT_CONFIG = {
    "watch_dir": str(BASE_DIR / "data" / "watch"),
    "output_torrent_dir": str(BASE_DIR / "data" / "torrents"),
    "processed_dir": str(BASE_DIR / "data" / "processed"),
    "log_dir": str(BASE_DIR / "logs"),
    "db_path": str(BASE_DIR / "data" / "processed_files.json"),
    "tracker_urls": [
        "http://open.acgtracker.com:1096/announce",
        "http://nyaa.tracker.wf:7777/announce",
        "http://opentracker.acgnx.se/announce",
        "udp://tr.bangumi.moe:6969/announce",
        "http://tr.bangumi.moe:6969/announce",
        "udp://208.67.16.113:8000/announce",
        "http://208.67.16.113:8000/announce",
        "http://tracker.ktxp.com:6868/announce",
        "http://tracker.ktxp.com:7070/announce",
        "http://t2.popgo.org:7456/annonce",
        "udp://bt.sc-ol.com:2710/announce",
        "http://share.camoe.cn:8080/announce",
        "http://61.154.116.205:8000/announce",
        "http://bt.rghost.net:80/announce",
        "udp://tracker.openbittorrent.com:80/announce",
        "udp://tracker.publicbt.com:80/announce",
        "udp://tracker.prq.to:80/announce",
        "http://open.nyaatorrents.info:6544/announce",
        "http://t.acg.rip:6699/announce",
        "http://tracker.openbittorrent.com:80/announce",
        "http://tracker.publicbt.com:80/announce",
        "http://tracker.prq.to/announce",
        "udp://104.238.198.186:8000/announce",
        "http://104.238.198.186:8000/announce",
        "http://94.228.192.98/announce",
        "http://share.dmhy.org/annonuce",
        "http://tracker.btcake.com/announce",
        "http://btfile.sdo.com:6961/announce",
        "https://t-115.rhcloud.com/only_for_ylbud",
        "http://exodus.desync.com:6969/announce",
        "udp://coppersurfer.tk:6969/announce",
        "http://tracker3.torrentino.com/announce",
        "http://tracker2.torrentino.com/announce",
        "udp://open.demonii.com:1337/announce",
        "udp://tracker.ex.ua:80/announce",
        "http://pubt.net:2710/announce",
        "http://tracker.tfile.me/announce",
        "http://bigfoot1942.sektori.org:6969/announce",
        "http://t.nyaatracker.com/announce",
        "http://bt.sc-ol.com:2710/announce"
    ],
    "okp": {
        "executable": None,
        "cookie_path": None,
        "setting_path": None,
        "working_dir": None,
        "timeout": 300,
        "auto_confirm": True,
        "preview_only": True,
    },
    "okp_path": None,
    "okp_setting_path": None,
    "okp_cookies_path": None,
    "okp_timeout": 300,
    "okp_auto_confirm": True,
    "okp_preview_only": True,
    "video_extensions": [".mkv", ".mp4", ".avi"]
}

_config = None


def load_config():
    global _config
    if _config is not None:
        return _config

    if CONFIG_PATH.exists():
        with open(CONFIG_PATH, "r", encoding="utf-8") as f:
            user_config = yaml.safe_load(f) or {}
        _config = {**DEFAULT_CONFIG, **user_config}
    else:
        _config = DEFAULT_CONFIG.copy()

    if "okp" not in _config or not isinstance(_config["okp"], dict):
        _config["okp"] = dict(DEFAULT_CONFIG["okp"])

    _config["okp"] = {**DEFAULT_CONFIG["okp"], **_config["okp"]}

    _flatten_okp_config(_config)

    for dir_key in ["watch_dir", "output_torrent_dir", "processed_dir", "log_dir"]:
        dir_path = Path(_config[dir_key])
        dir_path.mkdir(parents=True, exist_ok=True)

    return _config


def _flatten_okp_config(cfg):
    okp = cfg.get("okp", {})

    if okp.get("executable") is not None:
        cfg.setdefault("okp_path", okp["executable"])
    if okp.get("cookie_path") is not None:
        cfg.setdefault("okp_cookies_path", okp["cookie_path"])
    if okp.get("setting_path") is not None:
        cfg.setdefault("okp_setting_path", okp["setting_path"])
    if okp.get("timeout") is not None:
        cfg.setdefault("okp_timeout", okp["timeout"])
    if okp.get("auto_confirm") is not None:
        cfg.setdefault("okp_auto_confirm", okp["auto_confirm"])
    if okp.get("preview_only") is not None:
        cfg.setdefault("okp_preview_only", okp["preview_only"])


def get_config(key, default=None):
    cfg = load_config()
    return cfg.get(key, default)


def get_okp_config():
    """
    获取合并后的 OKP 配置 (okp 段优先, 旧版字段兜底)

    Returns:
        dict: {
            "executable": str|None,
            "cookie_path": str|None,
            "setting_path": str|None,
            "working_dir": str|None,
            "timeout": int,
            "auto_confirm": bool,
            "preview_only": bool,
        }
    """
    cfg = load_config()
    okp = cfg.get("okp", {})
    return {
        "executable": okp.get("executable") or cfg.get("okp_path"),
        "cookie_path": okp.get("cookie_path") or cfg.get("okp_cookies_path"),
        "setting_path": okp.get("setting_path") or cfg.get("okp_setting_path"),
        "working_dir": okp.get("working_dir"),
        "timeout": okp.get("timeout") or cfg.get("okp_timeout", 300),
        "auto_confirm": okp.get("auto_confirm") if okp.get("auto_confirm") is not None else cfg.get("okp_auto_confirm", True),
        "preview_only": okp.get("preview_only") if okp.get("preview_only") is not None else cfg.get("okp_preview_only", False),
    }


def get_cookie_status():
    """
    获取 Cookie 文件状态

    Returns:
        dict: {
            "configured": bool,
            "exists": bool,
            "path": str|None,
            "resolved_path": str|None,
            "size_bytes": int|None,
            "modified_at": str|None,
        }
    """
    okp_cfg = get_okp_config()
    cookie_path = okp_cfg.get("cookie_path")

    status = {
        "configured": bool(cookie_path),
        "exists": False,
        "path": cookie_path,
        "resolved_path": None,
        "size_bytes": None,
        "modified_at": None,
    }

    if cookie_path:
        p = Path(cookie_path)
        if not p.is_absolute():
            p = BASE_DIR / p
        status["resolved_path"] = str(p.resolve())

        if p.exists():
            status["exists"] = True
            try:
                stat = p.stat()
                status["size_bytes"] = stat.st_size
                from datetime import datetime
                status["modified_at"] = datetime.fromtimestamp(stat.st_mtime).isoformat()
            except OSError:
                pass

    return status


def WATCH_DIR():
    return Path(get_config("watch_dir"))


def OUTPUT_TORRENT_DIR():
    return Path(get_config("output_torrent_dir"))


def PROCESSED_DIR():
    return Path(get_config("processed_dir"))


def LOG_DIR():
    return Path(get_config("log_dir"))


def DB_PATH():
    return Path(get_config("db_path"))


def TRACKER_URLS():
    return get_config("tracker_urls", [])


def VIDEO_EXTENSIONS():
    return set(get_config("video_extensions"))


def LOG_FILE():
    return LOG_DIR() / "video_scanner.log"
