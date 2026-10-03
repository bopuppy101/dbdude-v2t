"""Exercise real platform text functions without audio, GUI, or model startup."""
import ast
import importlib.util
from pathlib import Path
import sys
import unittest

import regex

ROOT = Path(__file__).resolve().parents[1]


def load_pipeline(platform):
    directory = ROOT / platform
    spec = importlib.util.spec_from_file_location('formatting', directory / 'text_formatting.py')
    formatter = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(formatter)
    mappings = {'dot': '.', 'bang': '!', 'question mark': '?', 'exclamation point': '!'}
    names = regex.compile(r'\b(' + '|'.join(mappings) + r')\b', regex.I)
    ns = dict(regex=regex, re=regex, sys=sys, _DEBUG_MODE=False,
              MIN_TRANSCRIPTION_LENGTH=1, NAME_MAP=mappings, CUSTOM_MAP=mappings,
              CUSTOM_SYMBOL_MAP={'bang': '!', 'question mark': '?'},
              PUNCTUATION_MAP={}, PROGRAMMER_MAP={}, WHITESPACE_STRIP_MAP={},
              STRIP_PUNCT_VALUES={'!', '?'}, NAME_RE=names, name_re=names,
              RULES=[], WILDCARD_MAP={}, WILDCARD_MODE='sql92',
              _strip_punct_used=False, WHISPER_HALLUCINATIONS=set(),
              EXPLICIT_DOT=formatter.EXPLICIT_DOT,
              format_sentences=formatter.format_sentences,
              strip_trailing_pipe=getattr(formatter, 'strip_trailing_pipe', lambda text: text),
              replace_spoken_email=lambda text: text)
    wanted = {'replace_misheard_names', 'strip_trailing_period_if_symbol_map',
              'apply_mappings', 'apply_wildcard_mappings', 'apply_rules',
              'deduplicate_spaces', 'is_whisper_hallucination',
              'process_and_validate_text'}
    tree = ast.parse((directory / 'dbdude-v2t.py').read_text())
    nodes = [n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name in wanted]
    exec(compile(ast.Module(body=nodes, type_ignores=[]), str(directory), 'exec'), ns)
    if platform != 'macos':
        return ns['process_and_validate_text']
    # Execute the actual formatting statements from the macOS worker.
    worker = next(n for n in tree.body if isinstance(n, ast.FunctionDef)
                  and any(isinstance(x, ast.Call) and isinstance(x.func, ast.Name)
                          and x.func.id == 'apply_mappings' for x in ast.walk(n)))
    statements = [n for n in ast.walk(worker) if isinstance(n, ast.Assign)
                  and any(isinstance(t, ast.Name) and t.id == 'text' for t in n.targets)]
    code = compile(ast.Module(body=sorted(statements, key=lambda n: n.lineno), type_ignores=[]), '<worker>', 'exec')
    def process(raw):
        ns['raw'] = raw
        exec(code, ns)
        return ns['text']
    return process


class PlatformFormattingTests(unittest.TestCase):
    def test_all_platforms(self):
        examples = {
            'dot': '.', 'Dot.': '.', 'Finish this dot.': 'Finish this.',
            'bang!': '!', 'bang bang!': '!!',
            'Very good exclamation point!': 'Very good!',
            'Ready question mark?': 'Ready?',
            'Ready question mark? here is another sentence.': 'Ready? Here is another sentence.',
            'This is a single sentence.': 'This is a single sentence',
            'This is one sentence. here is another.': 'This is one sentence. Here is another.',
            'First sentence dot second sentence dot.': 'First sentence. Second sentence.',
            'Go. stop.': 'Go. Stop.',
        }
        for platform in ('ubuntu', 'ubuntu-26.04', 'omarchy', 'windows', 'macos'):
            process = load_pipeline(platform)
            for raw, expected in examples.items():
                with self.subTest(platform=platform, raw=raw):
                    self.assertEqual(process(raw), expected)


if __name__ == '__main__':
    unittest.main()
