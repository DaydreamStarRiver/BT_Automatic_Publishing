import re
from typing import Optional, Dict
from src.core.site_adapters.base_adapter import BaseSiteAdapter


class DMHYAdapter(BaseSiteAdapter):
    site_name = "dmhy"
    supported_format = "bbcode"
    format_description = "BBCode（动漫花园）"

    def render(self, markdown: str, context: Optional[Dict] = None) -> str:
        result = self._markdown_to_dmhy_bbcode(markdown)
        return self.clean_text(result)

    def _markdown_to_dmhy_bbcode(self, markdown: str) -> str:
        result = self._markdown_to_bbcode(markdown)
        return result
