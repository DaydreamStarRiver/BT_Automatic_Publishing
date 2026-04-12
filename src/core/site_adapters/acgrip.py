import re
from typing import Optional, Dict
from src.core.site_adapters.base_adapter import BaseSiteAdapter


class ACGripAdapter(BaseSiteAdapter):
    site_name = "acgrip"
    supported_format = "windcode"
    format_description = "WindCode（ACG.RIP）"

    def render(self, markdown: str, context: Optional[Dict] = None) -> str:
        result = self._markdown_to_windcode(markdown)
        return self.clean_text(result)

    def _markdown_to_windcode(self, markdown: str) -> str:
        result = self._markdown_to_bbcode(markdown)
        return result
