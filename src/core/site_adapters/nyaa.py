import re
from typing import Optional, Dict
from src.core.site_adapters.base_adapter import BaseSiteAdapter


class NyaaAdapter(BaseSiteAdapter):
    site_name = "nyaa"
    supported_format = "plaintext"
    format_description = "纯文本（Nyaa 不支持富文本）"

    def render(self, markdown: str, context: Optional[Dict] = None) -> str:
        result = self._markdown_to_nyaa_about(markdown)
        return self.clean_text(result)

    def _markdown_to_nyaa_about(self, markdown: str) -> str:
        result = self._markdown_to_plaintext(markdown)

        result = re.sub(r'^#\s+.+$', '', result, flags=re.MULTILINE)

        result = re.sub(r'^=\s+(.+)\s+=$', r'= \1 =', result, flags=re.MULTILINE)
        result = re.sub(r'^==\s+(.+)\s+==$', r'== \1 ==', result, flags=re.MULTILINE)

        result = re.sub(r'^>\s+(.+)$', r'\1', result, flags=re.MULTILINE)
        result = re.sub(r'^---+$', '', result, flags=re.MULTILINE)

        return result
