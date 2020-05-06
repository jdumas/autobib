#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
User-defined replacement rules for auto-formatting bibtex entries and filenames.
"""

# Words to keep all uppercase when converting to titlecase
uppercase_words = [
    '3D',
    'CG',
    'BFGS',
]

# Words to keep all lowercase when converting to titlecase
lowercase_words = [
    '$\\Tt'
]

# Words to keep as is
mixedcase_words = [
    'FreeFem++'
]

# Crossref acceptance threshold
crossref_accept_threshold = 2.8

# Whether to write accented characters (True), or their latex equivalent (False)
use_utf8_characters = False

# Protect uppercase words when writing the 'title' field
protect_uppercase = True
