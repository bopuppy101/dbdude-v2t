import ast
from pathlib import Path
import re
import sys
import unittest

APP_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(APP_DIR))
from text_formatting import EXPLICIT_DOT, format_sentences


class SentenceFormattingTests(unittest.TestCase):
    def test_dictation(self):
        examples = {
            'This is a longer snippet to paste.': 'This is a longer snippet to paste',
            'This is a longer snippet to paste': 'This is a longer snippet to paste',
            'One sentence. do not lowercase this one.': 'One sentence. Do not lowercase this one.',
            'first sentence. second sentence': 'First sentence. Second sentence.',
            'Go. stop.': 'Go. Stop.',
            'Ready?': 'Ready?',
            'Stop!': 'Stop!',
            'Ready? go now': 'Ready? Go now.',
            'Ask Dr. Smith about this.': 'Ask Dr. Smith about this',
            'Ask J. Smith about this.': 'Ask J. Smith about this',
            'It costs 3.14 dollars.': 'It costs 3.14 dollars',
            'Visit example.com today.': 'Visit example.com today',
            'Email mike@example.com today.': 'Email mike@example.com today',
            'He said “hello.”': 'He said “hello”',
            'He said “hello.” then left.': 'He said “hello.” Then left.',
            'Wait...': 'Wait...',
            '': '',
        }
        for raw, expected in examples.items():
            with self.subTest(raw=raw):
                self.assertEqual(format_sentences(raw), expected)

    def test_processing_pipeline(self):
        # Load the real pipeline without starting the model, mic, or hotkeys.
        tree = ast.parse((APP_DIR / 'dbdude-v2t.py').read_text())
        function = next(node for node in tree.body
                        if isinstance(node, ast.FunctionDef)
                        and node.name == 'process_and_validate_text')
        namespace = {
            'EXPLICIT_DOT': EXPLICIT_DOT, 'regex': re, 'MIN_TRANSCRIPTION_LENGTH': 1, '_DEBUG_MODE': False,
            'replace_spoken_email': lambda text: text,
            'replace_misheard_names': lambda text: text,
            'apply_wildcard_mappings': lambda text: text,
            'strip_trailing_period_if_symbol_map': lambda text: text,
            'format_sentences': format_sentences,
        }
        exec(compile(ast.Module(body=[function], type_ignores=[]), '<pipeline>', 'exec'), namespace)
        process = namespace['process_and_validate_text']
        self.assertEqual(process('This is a single sentence.'), 'This is a single sentence')
        self.assertEqual(process('This is one sentence. do not forget this one.'),
                         'This is one sentence. Do not forget this one.')
        self.assertIsNone(process('   '))

    def test_spoken_punctuation_replaces_attached_punctuation(self):
        tree = ast.parse((APP_DIR / 'dbdude-v2t.py').read_text())
        function = next(node for node in tree.body
                        if isinstance(node, ast.FunctionDef)
                        and node.name == 'replace_misheard_names')
        mappings = {'bang': '!', 'exclamation point': '!', 'question mark': '?',
                    'mike': 'Mike'}
        namespace = {
            'EXPLICIT_DOT': EXPLICIT_DOT, 'regex': re, '_DEBUG_MODE': False,
            'NAME_RE': re.compile(r'\b(' + '|'.join(mappings) + r')\b', re.I),
            'NAME_MAP': mappings, 'CUSTOM_SYMBOL_MAP': {'bang': '!'},
            'WHITESPACE_STRIP_MAP': {'!': (True, False), '?': (True, False)},
        }
        exec(compile(ast.Module(body=[function], type_ignores=[]), '<mapping>', 'exec'), namespace)
        replace = namespace['replace_misheard_names']
        for raw, expected in {
            'bang!': '!', 'Bang.': '!', 'Very good bang!': 'Very good!',
            'Very good exclamation point!': 'Very good!',
            'Ready question mark?': 'Ready?',
            'bang! next sentence.': '! next sentence.',
            'bang bang!': '!!', 'Wow!!': 'Wow!!', 'mike!': 'Mike!',
        }.items():
            with self.subTest(raw=raw):
                self.assertEqual(replace(raw), expected)


if __name__ == '__main__':
    unittest.main()
