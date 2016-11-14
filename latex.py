#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import unicodedata

accents = {
    0x0300: '`', 0x0301: "'", 0x0302: '^', 0x0308: '"',
    0x030B: 'H', 0x0303: '~', 0x0327: 'c', 0x0328: 'k',
    0x0304: '=', 0x0331: 'b', 0x0307: '.', 0x0323: 'd',
    0x030A: 'r', 0x0306: 'u', 0x030C: 'v',
}

specials = {
    'ø': '\\o',
    'ß': '\\ss'
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
            out += "{\\%s %s}" % (accents[code], txt[i + 1])
            i += 1
        # precomposed characters
        elif unicodedata.decomposition(char):
            base, acc = unicodedata.decomposition(char).split()
            acc = int(acc, 16)
            base = int(base, 16)
            if acc in accents:
                out += "{\\%s %s}" % (accents[acc], chr(base))
            else:
                out += char
        # other special case
        elif char in specials:
            out += "{%s}" % specials[char]
        else:
            out += char

        i += 1

    return out


if __name__ == '__main__':
    print(uni2tex("Klüft skräms inför på fédéral électoral große"))
