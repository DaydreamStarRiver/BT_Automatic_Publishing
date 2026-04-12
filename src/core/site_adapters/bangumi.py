from typing import Optional, Dict
from src.core.site_adapters.base_adapter import BaseSiteAdapter


class BangumiAdapter(BaseSiteAdapter):
    site_name = "bangumi"
    supported_format = "markdown"
    format_description = "Markdown（萌番组原生支持）"

    def render(self, markdown: str, context: Optional[Dict] = None) -> str:
        return self.clean_text(markdown)
