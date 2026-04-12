from abc import ABC, abstractmethod
from typing import Optional, Dict
import re


class BaseSiteAdapter(ABC):
    site_name: str = "base"
    supported_format: str = "text"
    format_description: str = "纯文本"

    @abstractmethod
    def render(self, markdown: str, context: Optional[Dict] = None) -> str:
        pass

    def clean_text(self, text: str) -> str:
        text = text.replace('\r\n', '\n')
        text = re.sub(r'\n{3,}', '\n\n', text)
        return text.strip()

    def _markdown_to_bbcode(self, markdown: str) -> str:
        result = markdown

        result = re.sub(r'\*\*\*(.+?)\*\*\*', r'[b][i]\1[/i][/b]', result, flags=re.DOTALL)
        result = re.sub(r'\*\*(.+?)\*\*', r'[b]\1[/b]', result, flags=re.DOTALL)
        result = re.sub(r'\*(.+?)\*', r'[i]\1[/i]', result, flags=re.DOTALL)
        result = re.sub(r'~~(.+?)~~', r'[s]\1[/s]', result, flags=re.DOTALL)
        result = re.sub(r'`(.+?)`', r'[code]\1[/code]', result, flags=re.DOTALL)

        result = re.sub(r'^###\s+(.+)$', r'[h3]\1[/h3]', result, flags=re.MULTILINE)
        result = re.sub(r'^##\s+(.+)$', r'[h2]\1[/h2]', result, flags=re.MULTILINE)
        result = re.sub(r'^#\s+(.+)$', r'[h1]\1[/h1]', result, flags=re.MULTILINE)

        result = re.sub(r'^-\s+\[x\]\s+(.+)$', r'[x] \1', result, flags=re.MULTILINE)
        result = re.sub(r'^-\s+\[\s?\]\s+(.+)$', r'[ ] \1', result, flags=re.MULTILINE)
        result = re.sub(r'^-\s+(.+)$', r'[*]\1', result, flags=re.MULTILINE)

        result = self._wrap_list_items(result)

        result = re.sub(r'!\[([^\]]*)\]\(([^)]+)\)', r'[img]\2[/img]', result)
        result = re.sub(r'\[([^\]]+)\]\(([^)]+)\)', r'[url=\2]\1[/url]', result)

        result = re.sub(r'^>\s+(.+)$', r'[quote]\1[/quote]', result, flags=re.MULTILINE)
        result = re.sub(r'^---+$', '[hr]', result, flags=re.MULTILINE)

        return result

    @staticmethod
    def _wrap_list_items(text: str) -> str:
        lines = text.split('\n')
        result = []
        in_list = False
        for line in lines:
            if line.startswith('[*]'):
                if not in_list:
                    result.append('[list]')
                    in_list = True
                result.append(line)
            else:
                if in_list:
                    result.append('[/list]')
                    in_list = False
                result.append(line)
        if in_list:
            result.append('[/list]')
        return '\n'.join(result)

    def _markdown_to_plaintext(self, markdown: str) -> str:
        result = markdown

        result = re.sub(r'\*\*\*(.+?)\*\*\*', r'\1', result, flags=re.DOTALL)
        result = re.sub(r'\*\*(.+?)\*\*', r'\1', result, flags=re.DOTALL)
        result = re.sub(r'\*(.+?)\*', r'\1', result, flags=re.DOTALL)
        result = re.sub(r'~~(.+?)~~', r'\1', result, flags=re.DOTALL)
        result = re.sub(r'`(.+?)`', r'\1', result, flags=re.DOTALL)

        result = re.sub(r'^###\s+(.+)$', r'== \1 ==', result, flags=re.MULTILINE)
        result = re.sub(r'^##\s+(.+)$', r'= \1 =', result, flags=re.MULTILINE)
        result = re.sub(r'^#\s+.+$', '', result, flags=re.MULTILINE)

        result = re.sub(r'!\[([^\]]*)\]\([^)]+\)', '', result)
        result = re.sub(r'\[([^\]]+)\]\([^)]+\)', r'\1', result)

        result = re.sub(r'^>\s+(.+)$', r'\1', result, flags=re.MULTILINE)
        result = re.sub(r'^---+$', '', result, flags=re.MULTILINE)

        result = re.sub(r'^-\s+\[x\]\s+(.+)$', r'[x] \1', result, flags=re.MULTILINE)
        result = re.sub(r'^-\s+\[\s?\]\s+(.+)$', r'[ ] \1', result, flags=re.MULTILINE)
        result = re.sub(r'^-\s+(.+)$', r'- \1', result, flags=re.MULTILINE)

        return result
