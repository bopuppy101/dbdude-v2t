"""--speech-server's address, from each platform's real speech_server_url, with no audio, GUI or model startup."""
import ast
from pathlib import Path
import re
import unittest

import regex

ROOT = Path(__file__).resolve().parents[1]


def load(platform):
    tree = ast.parse((ROOT / platform / 'dbdude-v2t.py').read_text(encoding='utf-8'))
    node = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == 'speech_server_url')
    ns = dict(re=re, regex=regex)
    exec(compile(ast.Module([node], []), platform, 'exec'), ns)
    return ns['speech_server_url']


class SpeechServerUrlTest(unittest.TestCase):
    def test_each_platform(self):
        for platform in ('macos', 'omarchy', 'windows'):
            url = load(platform)
            with self.subTest(platform=platform):
                self.assertEqual(url('r16'), 'http://r16:8880')
                self.assertEqual(url('192.168.1.16'), 'http://192.168.1.16:8880')
                self.assertEqual(url(' 192.168.1.16:9000 '), 'http://192.168.1.16:9000')
                self.assertEqual(url('https://r16/'), 'https://r16:8880')
                self.assertEqual(url('http://r16:8880'), 'http://r16:8880')
                self.assertEqual(url('LOCAL'), 'http://127.0.0.1:8880')


if __name__ == '__main__':
    unittest.main()
