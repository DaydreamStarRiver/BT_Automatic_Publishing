
import subprocess
import shutil
import re
from pathlib import Path
from src.logger import setup_logger

logger = setup_logger(__name__)


class OKPExecutor:

    @staticmethod
    def _find_okp_executable(okp_path=None):
        if okp_path and Path(okp_path).exists():
            return str(Path(okp_path).resolve())

        possible_names = [
            "OKP.Core.exe",
            "OKP.exe",
            "OKP.Core"
        ]

        search_paths = [
            Path.cwd(),
            Path(__file__).parent.parent.parent,
            Path(__file__).parent.parent.parent / "tools",
        ]

        for search_dir in search_paths:
            for name in possible_names:
                candidate = search_dir / name
                if candidate.exists():
                    logger.info(f"找到 OKP 可执行文件: {candidate}")
                    return str(candidate.resolve())

        for name in possible_names:
            found = shutil.which(name)
            if found:
                logger.info(f"在系统 PATH 中找到 OKP: {found}")
                return found

        return None

    @staticmethod
    def _resolve_cookie_path(cookie_path):
        """
        解析 cookie 文件路径并验证

        Returns:
            tuple: (resolved_path: str|None, error: str|None)
        """
        if not cookie_path:
            return None, "未配置 cookie 文件路径"

        p = Path(cookie_path)
        if not p.is_absolute():
            from src.config import BASE_DIR
            p = BASE_DIR / p

        resolved = p.resolve()

        if not resolved.exists():
            return str(resolved), f"cookie 文件不存在: {resolved}"

        if resolved.stat().st_size == 0:
            return str(resolved), f"cookie 文件为空: {resolved}"

        return str(resolved), None

    @staticmethod
    def _get_working_dir(okp_executable, configured_working_dir=None):
        """
        确定 OKP 的工作目录

        优先级:
        1. 配置中指定的 working_dir
        2. OKP 可执行文件所在目录 (确保 OKP 能找到 setting.toml)

        Returns:
            str: 工作目录的绝对路径
        """
        if configured_working_dir:
            p = Path(configured_working_dir)
            if p.exists():
                return str(p.resolve())
            logger.warning(f"配置的 OKP 工作目录不存在: {configured_working_dir}, 使用默认")

        if okp_executable:
            okp_dir = Path(okp_executable).parent
            if okp_dir.exists():
                return str(okp_dir.resolve())

        return str(Path.cwd().resolve())

    @staticmethod
    def _decode_output(raw_bytes):
        encodings_to_try = ['utf-8', 'gbk', 'gb2312', 'gb18030', 'latin-1']

        for encoding in encodings_to_try:
            try:
                decoded = raw_bytes.decode(encoding)
                if not decoded.startswith('\ufffd'):
                    return decoded, encoding
            except (UnicodeDecodeError, UnicodeEncodeError):
                continue

        try:
            return raw_bytes.decode('utf-8', errors='replace'), 'utf-8-replace'
        except Exception:
            return "[无法解码的输出]", 'unknown'

    @staticmethod
    def _parse_torrent_info(torrent_path):
        try:
            import torf
            from pathlib import Path

            if isinstance(torrent_path, Path):
                torrent_path_str = str(torrent_path)
            elif isinstance(torrent_path, str):
                torrent_path_str = torrent_path
                torrent_path = Path(torrent_path)
            else:
                logger.warning(f"不支持的 torrent_path 类型: {type(torrent_path)}")
                return None

            if not torrent_path.exists():
                logger.warning(f"Torrent 文件不存在: {torrent_path}")
                return None

            torrent = torf.Torrent.read(torrent_path_str)

            info = {
                'name': getattr(torrent, 'name', 'Unknown'),
                'size': getattr(torrent, 'size', 0),
                'files': [],
                'trackers': []
            }

            if hasattr(torrent, 'files') and torrent.files:
                for f in torrent.files:
                    try:
                        file_size = getattr(f, 'size', 0)
                        size_str = _format_size(file_size)

                        if hasattr(f, 'name'):
                            file_display = f.name
                        else:
                            file_display = str(f)

                        info['files'].append(f"  📄 {file_display} ({size_str})")
                    except Exception as fe:
                        logger.debug(f"处理文件信息时出错: {fe}")
                        continue
            else:
                info['files'].append(f"  📄 {info['name']} ({_format_size(info['size'])})")

            if hasattr(torrent, 'trackers') and torrent.trackers:
                for tracker_list in torrent.trackers[:3]:
                    if tracker_list and len(tracker_list) > 0:
                        info['trackers'].append(str(tracker_list[0]))

            return info

        except ImportError:
            logger.error("无法导入 torf 库，请确保已安装: pip install torf")
            return None
        except FileNotFoundError:
            logger.warning(f"Torrent 文件未找到: {torrent_path}")
            return None
        except PermissionError:
            logger.warning(f"无权限读取 Torrent 文件: {torrent_path}")
            return None
        except Exception as e:
            error_type = type(e).__name__
            logger.warning(f"解析 Torrent 信息失败 [{error_type}]: {e}")
            logger.debug(f"详细错误信息:", exc_info=True)
            return None

    @staticmethod
    def run_okp_upload(
        torrent_path,
        okp_path=None,
        setting_path=None,
        cookies_path=None,
        timeout=300,
        auto_confirm=True,
        preview_only=False
    ):
        torrent_path = Path(torrent_path).resolve()

        if not torrent_path.exists():
            error_msg = f"Torrent 文件不存在: {torrent_path}"
            logger.error(error_msg)
            return {
                "success": False,
                "error": error_msg,
                "returncode": -1,
                "stdout": "",
                "stderr": "",
                "mode": "error"
            }

        logger.info("")
        logger.info("╔════════════════════════════════════════════════════════════╗")
        logger.info("║              🔶 BT 发布任务 - 开始处理                    ║")
        logger.info("╚════════════════════════════════════════════════════════════╝")
        logger.info("")

        logger.info("📦 Torrent 文件信息:")
        logger.info(f"  路径: {torrent_path}")
        logger.info(f"  大小: {_format_size(torrent_path.stat().st_size)}")
        logger.info("")

        torrent_info = OKPExecutor._parse_torrent_info(torrent_path)

        if torrent_info:
            logger.info("📋 内容详情:")
            logger.info(f"  标题: {torrent_info['name']}")
            logger.info(f"  总大小: {_format_size(torrent_info['size'])}")
            logger.info(f"  文件列表 ({len(torrent_info['files'])} 个文件):")
            for file_info in torrent_info['files'][:10]:
                logger.info(file_info)
            if len(torrent_info['files']) > 10:
                logger.info(f"  ... 还有 {len(torrent_info['files']) - 10} 个文件")
            if torrent_info['trackers']:
                logger.info(f"  Tracker (前3个):")
                for tracker in torrent_info['trackers']:
                    logger.info(f"    • {tracker}")
            logger.info("")

        if preview_only:
            logger.info("=" * 60)
            logger.info("⚠️  预览模式 (preview_only=True)")
            logger.info("   仅展示信息，不执行发布操作")
            logger.info("=" * 60)
            logger.info("")

            return {
                "success": True,
                "returncode": 0,
                "stdout": "",
                "stderr": "",
                "mode": "preview",
                "info": {
                    "torrent_name": torrent_info.get('name') if torrent_info else None,
                    "torrent_size": torrent_info.get('size') if torrent_info else None,
                    "file_count": len(torrent_info.get('files', [])) if torrent_info else 0
                },
                "message": "预览完成，未执行发布"
            }

        resolved_okp_path = OKPExecutor._find_okp_executable(okp_path)

        if not resolved_okp_path:
            error_msg = (
                "❌ 找不到 OKP 可执行文件\n\n"
                "请确保以下之一：\n"
                "  1. 在 config.yaml 的 okp.executable 中正确设置路径\n"
                "  2. 将 OKP.Core.exe 或 OKP.exe 放入项目根目录或 tools/ 目录\n"
                "  3. 将 OKP 添加到系统 PATH 环境变量\n\n"
                "下载地址: https://github.com/AmusementClub/OKP"
            )
            logger.error(error_msg)
            return {
                "success": False,
                "error": error_msg,
                "returncode": -4,
                "stdout": "",
                "stderr": "",
                "mode": "error"
            }

        from src.config import get_okp_config
        okp_cfg = get_okp_config()
        working_dir = OKPExecutor._get_working_dir(
            resolved_okp_path,
            okp_cfg.get("working_dir")
        )

        cmd = [resolved_okp_path, str(torrent_path)]

        if setting_path and Path(setting_path).exists():
            cmd.extend(["-s", str(Path(setting_path).resolve())])
        elif okp_cfg.get("setting_path"):
            sp = Path(okp_cfg["setting_path"])
            if not sp.is_absolute():
                from src.config import BASE_DIR
                sp = BASE_DIR / sp
            if sp.exists():
                cmd.extend(["-s", str(sp.resolve())])

        resolved_cookie, cookie_error = OKPExecutor._resolve_cookie_path(cookies_path)

        if resolved_cookie and not cookie_error:
            cmd.extend(["--cookies", resolved_cookie])
            logger.info(f"🍪 Cookie 文件: {resolved_cookie}")
        elif cookies_path:
            logger.warning(f"⚠️ Cookie 问题: {cookie_error}")
            logger.warning("   OKP 将尝试在工作目录中查找 cookies.txt")
        else:
            logger.warning("⚠️ 未配置 Cookie 文件 (okp.cookie_path)")
            logger.warning("   OKP 将尝试在工作目录中查找 cookies.txt")

        if auto_confirm:
            cmd.extend(["-y"])
            mode_display = "自动发布模式 (auto_confirm=True)"
        else:
            mode_display = "交互式确认模式 (auto_confirm=False)"

        logger.info("⚙️  执行配置:")
        logger.info(f"  模式: {mode_display}")
        logger.info(f"  OKP 路径: {resolved_okp_path}")
        logger.info(f"  工作目录: {working_dir}")
        if setting_path:
            logger.info(f"  配置文件: {setting_path}")
        if resolved_cookie:
            logger.info(f"  Cookie 文件: {resolved_cookie}")
        elif cookies_path:
            logger.info(f"  Cookie 状态: ⚠️ {cookie_error}")
        else:
            logger.info(f"  Cookie 状态: ❌ 未配置")
        logger.info("")
        logger.info("💻 执行命令:")
        logger.info(f"  {' '.join(cmd)}")
        logger.info("")

        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                timeout=timeout,
                cwd=working_dir
            )

            stdout_text, stdout_encoding = OKPExecutor._decode_output(result.stdout)
            stderr_text, stderr_encoding = OKPExecutor._decode_output(result.stderr)

            output = {
                "success": result.returncode == 0,
                "returncode": result.returncode,
                "stdout": stdout_text,
                "stderr": stderr_text,
                "encoding": {"stdout": stdout_encoding, "stderr": stderr_encoding},
                "error": None,
                "mode": "publish",
                "command": " ".join(cmd)
            }

            if not output["success"] and OKPExecutor._is_cookie_error(stdout_text, stderr_text):
                cookie_hint = "登录失败，请检查 cookies.txt 是否过期或格式是否正确"
                output["error"] = cookie_hint
                logger.error(f"  🍪 Cookie 错误: {cookie_hint}")

            logger.info("-" * 60)
            logger.info("📊 执行结果:")
            logger.info(f"  返回码: {result.returncode}")
            logger.info(f"  输出编码: STDOUT={stdout_encoding}, STDERR={stderr_encoding}")
            logger.info("")

            if output["success"]:
                logger.info("  ✅ 状态: 发布成功")

                okp_output_lines = OKPExecutor._extract_key_info(stdout_text)
                if okp_output_lines:
                    logger.info("  📝 OKP 输出摘要:")
                    for line in okp_output_lines:
                        logger.info(f"     {line}")

                if len(stdout_text) > 2000:
                    logger.info(f"\n  📄 完整输出已保存到日志文件 (长度: {len(stdout_text)} 字符)")
                elif stdout_text.strip():
                    logger.debug(f"  完整输出:\n{stdout_text}")

            else:
                logger.error("  ❌ 状态: 发布失败")
                if not output["error"]:
                    output["error"] = f"返回码 {result.returncode}"

                if stderr_text.strip():
                    error_summary = OKPExecutor._extract_error_info(stderr_text)
                    logger.error("\n  ⚠️  错误摘要:")
                    for line in error_summary:
                        logger.error(f"     {line}")

                if stdout_text.strip() and result.returncode != 0:
                    output_summary = OKPExecutor._extract_key_info(stdout_text)
                    if output_summary:
                        logger.warning("\n  📌 输出摘要:")
                        for line in output_summary:
                            logger.warning(f"     {line}")

            logger.info("")
            logger.info("╔════════════════════════════════════════════════════════════╗")
            if output["success"]:
                logger.info("║              ✅ BT 发布任务 - 完成                         ║")
            else:
                logger.info("║              ❌ BT 发布任务 - 失败                         ║")
            logger.info("╚════════════════════════════════════════════════════════════╝")
            logger.info("")

            return output

        except subprocess.TimeoutExpired:
            error_msg = f"⏰ OKP 执行超时 (限制: {timeout}秒)"
            logger.error(error_msg)
            logger.error("")
            logger.error("提示: 大型文件或网络慢时可能需要更长时间，可增加 okp.timeout 配置")
            return {
                "success": False,
                "error": error_msg,
                "returncode": -2,
                "stdout": "",
                "stderr": "",
                "mode": "timeout"
            }
        except Exception as e:
            error_msg = f"❌ OKP 执行异常: {str(e)}"
            logger.error(error_msg, exc_info=True)
            return {
                "success": False,
                "error": error_msg,
                "returncode": -3,
                "stdout": "",
                "stderr": "",
                "mode": "exception"
            }

    @staticmethod
    def _is_cookie_error(stdout_text, stderr_text):
        """检测 OKP 输出中是否包含 cookie/登录相关的错误"""
        combined = (stdout_text + "\n" + stderr_text).lower()
        cookie_error_keywords = [
            'login fail',
            'login failed',
            'cookie',
            'cookies',
            'unauthorized',
            'not logged',
            'not authenticated',
            'authentication fail',
            'session expired',
            'cookie过期',
            '登录失败',
            '未登录',
        ]
        return any(kw in combined for kw in cookie_error_keywords)

    @staticmethod
    def _extract_key_info(text):
        lines = []
        keywords = [
            r'标题|title|display_name',
            r'站点|site|发布|publish',
            r'登录|login|成功|success',
            r'失败|fail|错误|error',
            r'完成|complete|finish',
            r'跳过|skip',
            r'cookie|Cookie',
        ]

        for line in text.split('\n'):
            stripped = line.strip()
            if not stripped:
                continue
            if any(re.search(kw, stripped, re.IGNORECASE) for kw in keywords):
                lines.append(stripped[:100])
                if len(lines) >= 8:
                    break

        return lines

    @staticmethod
    def _extract_error_info(text):
        lines = []
        for line in text.split('\n'):
            stripped = line.strip()
            if stripped and len(stripped) > 5:
                lines.append(stripped[:120])
                if len(lines) >= 6:
                    break
        return lines


def _format_size(size_bytes):
    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if abs(size_bytes) < 1024.0:
            return f"{size_bytes:.2f} {unit}"
        size_bytes /= 1024.0
    return f"{size_bytes:.2f} PB"
