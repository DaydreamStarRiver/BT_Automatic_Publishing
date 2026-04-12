"""
内容渲染引擎 - Markdown → 各站点格式转换
==========================================

职责：
  - 接收 Markdown 源文本
  - 根据目标站点调用对应适配器渲染
  - 生成 HTML 预览
  - 返回结构化的渲染结果

不负责：
  - UI 交互逻辑
  - 任务管理
"""

import re
from dataclasses import dataclass, field
from typing import Dict, List, Optional

from src.core.site_adapters import get_adapter_for_site, get_supported_sites
from src.logger import setup_logger

logger = setup_logger(__name__)


@dataclass
class RenderResult:
    markdown_source: str = ""
    rendered_content: Dict[str, str] = field(default_factory=dict)
    preview_html: str = ""
    needs_review: bool = False
    errors: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict:
        return {
            "markdown_source": self.markdown_source,
            "rendered_content": self.rendered_content,
            "preview_html": self.preview_html,
            "needs_review": self.needs_review,
            "errors": self.errors,
        }


class ContentRenderer:
    _instance = None

    def __init__(self):
        self.logger = setup_logger(f"{__name__}.ContentRenderer")

    @classmethod
    def get_instance(cls):
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def render_for_sites(
        self,
        markdown: str,
        sites: List[str],
        context: Optional[Dict] = None,
    ) -> RenderResult:
        result = RenderResult(markdown_source=markdown)

        if not markdown or not markdown.strip():
            result.preview_html = ""
            for site in sites:
                result.rendered_content[site] = ""
            return result

        for site in sites:
            try:
                rendered = self.render_for_single_site(markdown, site, context)
                result.rendered_content[site] = rendered
            except Exception as e:
                error_msg = f"站点 {site} 渲染失败: {e}"
                result.errors.append(error_msg)
                result.rendered_content[site] = markdown
                result.needs_review = True
                self.logger.warning(error_msg)

        result.preview_html = self.render_preview_html(markdown)

        if result.errors:
            self.logger.warning(f"渲染过程中有 {len(result.errors)} 个错误")

        return result

    def render_for_single_site(
        self,
        markdown: str,
        site: str,
        context: Optional[Dict] = None,
    ) -> str:
        adapter = get_adapter_for_site(site)
        if not adapter:
            self.logger.warning(f"未找到站点 {site} 的适配器，回退到纯文本")
            from src.core.site_adapters.base_adapter import BaseSiteAdapter
            base = BaseSiteAdapter.__new__(BaseSiteAdapter)
            return base.clean_text(base._markdown_to_plaintext(markdown))

        rendered = adapter.render(markdown, context)
        self.logger.info(f"站点 {site} 渲染完成 (格式: {adapter.supported_format})")
        return rendered

    def render_preview_for_site(
        self,
        markdown: str,
        site: str,
        context: Optional[Dict] = None,
    ) -> Dict:
        adapter = get_adapter_for_site(site)
        if not adapter:
            return {
                "site": site,
                "format": "unknown",
                "content": markdown,
                "error": f"未找到站点 {site} 的适配器",
            }

        try:
            rendered = adapter.render(markdown, context)
            return {
                "site": site,
                "format": adapter.supported_format,
                "format_description": adapter.format_description,
                "content": rendered,
                "error": None,
            }
        except Exception as e:
            return {
                "site": site,
                "format": adapter.supported_format,
                "format_description": adapter.format_description,
                "content": markdown,
                "error": str(e),
            }

    def render_preview_html(self, markdown: str) -> str:
        if not markdown or not markdown.strip():
            return ""

        try:
            import markdown as md_lib
            extensions = ['tables', 'fenced_code', 'nl2br']
            try:
                import markdown.extensions.codehilite
                extensions.append('codehilite')
            except ImportError:
                pass
            html = md_lib.markdown(markdown, extensions=extensions)
            return html
        except ImportError:
            self.logger.debug("markdown 库不可用，使用简易 HTML 渲染")
            return self._simple_markdown_to_html(markdown)

    def _simple_markdown_to_html(self, markdown_text: str) -> str:
        html = markdown_text

        html = re.sub(r'^###\s+(.+)$', r'<h3>\1</h3>', html, flags=re.MULTILINE)
        html = re.sub(r'^##\s+(.+)$', r'<h2>\1</h2>', html, flags=re.MULTILINE)
        html = re.sub(r'^#\s+(.+)$', r'<h1>\1</h1>', html, flags=re.MULTILINE)

        html = re.sub(r'\*\*\*(.+?)\*\*\*', r'<strong><em>\1</em></strong>', html, flags=re.DOTALL)
        html = re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', html, flags=re.DOTALL)
        html = re.sub(r'\*(.+?)\*', r'<em>\1</em>', html, flags=re.DOTALL)
        html = re.sub(r'~~(.+?)~~', r'<del>\1</del>', html, flags=re.DOTALL)
        html = re.sub(r'`(.+?)`', r'<code>\1</code>', html, flags=re.DOTALL)

        html = re.sub(r'!\[([^\]]*)\]\(([^)]+)\)', r'<img src="\2" alt="\1" style="max-width:100%">', html)
        html = re.sub(r'\[([^\]]+)\]\(([^)]+)\)', r'<a href="\2" target="_blank">\1</a>', html)

        html = re.sub(r'^-\s+(.+)$', r'<li>\1</li>', html, flags=re.MULTILINE)
        html = re.sub(r'^>\s+(.+)$', r'<blockquote>\1</blockquote>', html, flags=re.MULTILINE)
        html = re.sub(r'^---+$', '<hr/>', html, flags=re.MULTILINE)

        paragraphs = html.split('\n\n')
        processed = []
        for p in paragraphs:
            p = p.strip()
            if not p:
                continue
            if p.startswith('<'):
                processed.append(p)
            else:
                p = p.replace('\n', '<br>')
                processed.append(f'<p>{p}</p>')

        return '\n'.join(processed)

    def get_all_site_previews(
        self,
        markdown: str,
        context: Optional[Dict] = None,
    ) -> Dict[str, Dict]:
        sites = get_supported_sites()
        previews = {}
        for site in sites:
            previews[site] = self.render_preview_for_site(markdown, site, context)
        return previews
