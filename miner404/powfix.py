"""`-x ** 2` is a SyntaxError in JavaScript; the models write it the way mathematics reads it. This puts the
parentheses in: `-(x ** 2)`. Only parentheses are inserted, and only where the source could not have parsed, so a
module that parses is returned as it came.

Strings, template literals and comments are blanked before the search (positions are kept). A source the scan cannot
follow (an unclosed string or bracket) is returned unchanged.
"""
from __future__ import annotations

import re

_WORD = re.compile(r"[\w$]")
_NUMBER = re.compile(r"(?:0[xXoObB][0-9a-fA-F_]+|(?:\d[\d_]*\.?[\d_]*|\.\d[\d_]*)(?:[eE][+-]?\d+)?)n?")
_EXPONENT = re.compile(r"(?<![\w$])(?:\d[\d_]*\.?[\d_]*|\.\d[\d_]*)[eE][+-]$")
_OPERAND_KEYWORDS = ("return", "typeof", "void", "delete", "await", "in", "of", "instanceof", "new", "case", "do", "else",
                     "throw", "yield")
_CLOSERS = {")": "(", "]": "["}
_OPENERS = {"(": ")", "[": "]"}


def _blanked(source: str) -> str | None:
    """The source with the insides of strings, templates and comments replaced, same length. Strings keep their
    quotes and are filled with `s`, so they still read as operands; comments become spaces."""
    out = list(source)
    i, n = 0, len(source)
    while i < n:
        c = source[i]
        if source.startswith("//", i):
            j = source.find("\n", i)
            j = n if j < 0 else j
            out[i:j] = " " * (j - i)
            i = j
        elif source.startswith("/*", i):
            j = source.find("*/", i + 2)
            if j < 0:
                return None
            out[i:j + 2] = " " * (j + 2 - i)
            i = j + 2
        elif c in "'\"":
            j = i + 1
            while j < n and source[j] != c:
                if source[j] == "\n":
                    return None
                j += 2 if source[j] == "\\" else 1
            if j >= n:
                return None
            out[i + 1:j] = "s" * (j - i - 1)
            i = j + 1
        elif c == "`":
            j, depth = i + 1, 0
            while j < n and (source[j] != "`" or depth):
                if source[j] == "\\":
                    j += 1
                elif source.startswith("${", j):
                    depth += 1
                    j += 1
                elif source[j] == "}" and depth:
                    depth -= 1
                j += 1
            if j >= n:
                return None
            out[i + 1:j] = "s" * (j - i - 1)
            i = j + 1
        else:
            i += 1
    return "".join(out)


def _skip_left(text: str, i: int) -> int:
    while i >= 0 and text[i].isspace():
        i -= 1
    return i


def _skip_right(text: str, i: int) -> int:
    while i < len(text) and text[i].isspace():
        i += 1
    return i


def _matching_left(text: str, i: int) -> int:
    """Index of the bracket that opens the one closed at i, or -1."""
    depth = 0
    for j in range(i, -1, -1):
        if text[j] in ")]}":
            depth += 1
        elif text[j] in "([{":
            depth -= 1
            if depth == 0:
                return j
    return -1


def _matching_right(text: str, i: int) -> int:
    depth = 0
    for j in range(i, len(text)):
        if text[j] in "([{":
            depth += 1
        elif text[j] in ")]}":
            depth -= 1
            if depth == 0:
                return j
    return -1


def _operand_start(text: str, end: int) -> int:
    """Start of the postfix chain (name, number, string, group, member, call, index) that ends at `end`, or -1."""
    i = end
    start = -1
    while i >= 0:
        c = text[i]
        if c in _CLOSERS:
            i = _matching_left(text, i)
            if i < 0:
                return -1
            start = i
            i -= 1
            if i >= 0 and (_WORD.match(text[i]) or text[i] in ")]"):
                continue  # a call or an index: the callee is part of the operand
            break
        if c in "'\"`":
            j = text.rfind(c, 0, i)
            if j < 0:
                return -1
            start = j
            break
        if _WORD.match(c):
            while i >= 0 and _WORD.match(text[i]):
                i -= 1
            start = i + 1
            exponent = _EXPONENT.search(text, 0, i + 1) if i >= 1 and text[i] in "+-" and text[start].isdigit() else None
            if exponent:  # 1e-3: the sign belongs to the number
                start = exponent.start()
                break
            if i >= 0 and text[i] == ".":
                start = i
                i -= 1
                if i >= 0 and text[i] == "?":
                    i -= 1
                if i >= 0 and (_WORD.match(text[i]) or text[i] in ")]"):
                    continue
            break
        break
    return start


def _operand_end(text: str, i: int) -> int:
    """Index just past the right side of `**` that starts at or after i: unary prefixes, a postfix chain, and any
    further `**` (the operator groups to the right). -1 when it cannot be followed."""
    n = len(text)
    while True:
        i = _skip_right(text, i)
        while i < n and text[i] in "-+!~":
            i = _skip_right(text, i + 1)
        if i >= n:
            return -1
        number = _NUMBER.match(text, i) if text[i].isdigit() or text[i] == "." else None
        if number:
            i = number.end()
        elif text[i] in _OPENERS:
            i = _matching_right(text, i)
            if i < 0:
                return -1
            i += 1
        elif text[i] in "'\"`":
            i = text.find(text[i], i + 1)
            if i < 0:
                return -1
            i += 1
        elif _WORD.match(text[i]):
            while i < n and _WORD.match(text[i]):
                i += 1
        else:
            return -1
        while i < n:  # members, calls and indexes
            if text[i] == "." or text.startswith("?.", i):
                i += 2 if text[i] == "?" else 1
                if i < n and text[i] in _OPENERS:
                    continue
                while i < n and _WORD.match(text[i]):
                    i += 1
            elif text[i] in _OPENERS:
                i = _matching_right(text, i)
                if i < 0:
                    return -1
                i += 1
            else:
                break
        j = _skip_right(text, i)
        if text.startswith("**", j) and not text.startswith("**=", j):
            i = j + 2
            continue
        return i


def _is_unary(text: str, i: int) -> bool:
    """Whether the sign at i is a unary operator: nothing that ends an operand stands before it."""
    j = _skip_left(text, i - 1)
    if j < 0:
        return True
    c = text[j]
    if c in ")]}'\"`":
        return False
    if _WORD.match(c):
        k = j
        while k >= 0 and _WORD.match(text[k]):
            k -= 1
        return text[k + 1:j + 1] in _OPERAND_KEYWORDS
    return True


def fix(source: str) -> str:
    text = _blanked(source)
    if text is None or "**" not in text:
        return source
    inserts: list[tuple[int, str]] = []
    for found in re.finditer(r"(?<!\*)\*\*(?![*=])", text):
        end = _skip_left(text, found.start() - 1)
        start = _operand_start(text, end) if end >= 0 else -1
        if start < 0:
            continue
        sign = _skip_left(text, start - 1)
        if sign < 0 or text[sign] not in "-+!~":
            continue
        if text[sign] in "-+" and sign > 0 and text[sign - 1] == text[sign]:
            continue  # --x ** 2 and ++x ** 2 are valid
        if text[sign] in "-+" and not _is_unary(text, sign):
            continue
        stop = _operand_end(text, found.end())
        if stop < 0:
            continue
        inserts.append((start, "("))
        inserts.append((stop, ")"))
    if not inserts:
        return source
    out = source
    for position, piece in sorted(inserts, key=lambda item: (item[0], item[1] == "("), reverse=True):
        out = out[:position] + piece + out[position:]
    return out
