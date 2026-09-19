"""Sentence formatting for dictated snippets and longer passages."""

import re

# Keep explicitly dictated periods through automatic punctuation and user rules.
EXPLICIT_DOT = "\ue000"


_BREAK = re.compile(r'''([.!?\ue000]+)["'”’)]*\s+["'“‘(]*(?P<start>\w)''')
_ABBREVIATIONS = {
    'mr', 'mrs', 'ms', 'dr', 'prof', 'sr', 'jr', 'st', 'vs', 'etc',
    'e.g', 'i.e', 'a.m', 'p.m',
}


def format_sentences(text):
    """Omit a single sentence's final period; capitalize longer dictation.

    Use punctuation supplied by the recognizer, ignoring common abbreviations
    and initials. Dots inside emails, domains, and decimals aren't boundaries.
    Sentence detection is heuristic: ambiguous abbreviations remain ambiguous.
    """
    starts = []
    for match in _BREAK.finditer(text):
        if match.group(1) == '.':
            token = re.search(r'([\w.]+)$', text[:match.start()])
            if token:
                word = token.group(1)
                if (word.lower() in _ABBREVIATIONS
                        or re.fullmatch(r'(?:[A-Za-z]\.)*[A-Za-z]', word)):
                    continue
        starts.append(match.start('start'))

    if not starts:
        # Keep deliberate question/exclamation marks and ellipses.
        return re.sub(r'''(?<!\.)\.(?=["'”’)]*$)''', '', text)

    first = re.search(r'\w', text)
    if first:
        starts.insert(0, first.start())
    for index in reversed(starts):
        text = text[:index] + text[index].upper() + text[index + 1:]
    if not re.search(r'''[.!?\ue000]["'”’)]*$''', text):
        text += '.'
    return text
