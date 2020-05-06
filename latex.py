#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# System libs
import re
import unicodedata

# Third party libs
import titlecase

# Local libs
import config

accents = {
    0x0300: '`', 0x0301: "'", 0x0302: '^', 0x0308: '"',
    0x030B: 'H', 0x0303: '~', 0x0327: 'c', 0x0328: 'k',
    0x0304: '=', 0x0331: 'b', 0x0307: '.', 0x0323: 'd',
    0x030A: 'r', 0x0306: 'u', 0x030C: 'v',
}

specials = {
    'ø': '\\o',
    'ß': '\\ss',
    '′': "'"
}


def uni2tex(text):
    """
    Translate accented unicode characters intro latex macros.

    http://tex.stackexchange.com/questions/23410/how-to-convert-characters-to-latex-code
    """
    out = ""
    txt = tuple(text)
    i = 0
    while i < len(txt):
        char = text[i]
        code = ord(char)

        # combining marks
        if unicodedata.category(char) in ("Mn", "Mc") and code in accents:
            out += "{\\%s{%s}}" % (accents[code], txt[i + 1])
            i += 1
        # precomposed characters
        elif unicodedata.decomposition(char):
            base, acc = unicodedata.decomposition(char).split()
            acc = int(acc, 16)
            base = int(base, 16)
            if acc in accents:
                out += "{\\%s{%s}}" % (accents[acc], chr(base))
            else:
                out += char
        # other special case
        elif char in specials:
            out += "{%s}" % specials[char]
        else:
            out += char

        i += 1

    return out


def remove_nested_braces(s):
    """
    Remove some cases of nested braces such as 'a{{b}}c' -> 'a{b}c'.
    """
    for __ in range(10):
        x = re.sub('{{([^{}]*)}}', '{\\1}', s)
        if len(x) >= len(s):
            break
        else:
            s = x
    s = re.sub('{([^{}])}', '\\1', s)
    s = re.sub('{([a-zA-Z]*)}', '\\1', s)
    return s


def protect_uppercase(s):
    """
    Protect uppercase words defined in config.py
    """
    def protect_one(word, **_kwargs):
        if word.upper() in config.uppercase_words:
            return '{' + word.upper() + '}'
        if '-' in word:
            return
        if "/" in word and "//" not in word:
            return
        return word
    return titlecase.titlecase(s, callback=protect_one)


if __name__ == '__main__':
    print(uni2tex("Klüft skräms çinför på fédéral électoral große"))
    print(protect_uppercase("Lorem BFGS Ipsum 3D Computer-3D 3DGraphics"))
