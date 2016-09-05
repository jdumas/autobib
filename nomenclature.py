#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# System libs
import re
import os
import json
import codecs

# Third party libs
import titlecase
import latexcodec
import bibtexparser

# Local libs
import config
import utils


def to_titlecase(text):
    """
    Converts string into a titlecased version of itself.
    A list of uppercase or lowercase abbreviation is read from config.py.

    Args:
        text (str): input string to convert.

    Returns:
        A titlecased version of the input string.
    """
    def abbreviations(word, **_kwargs):
        if word.upper() in config.uppercase_words:
            return word.upper()
        if word.lower() in config.lowercase_words:
            return word.lower()
        if word.startswith('\\'):
            return word
    return titlecase.titlecase(text, callback=abbreviations)


def parse_filename(path):
    """
    Extract author list and article title from a well-formed filename.
    If the file should not be processed (e.g. supplemental), returns None.

    Args:
        path (str): absolute or relative path to the .pdf

    Returns:
        A tuple (authors, title) where authors is a list of the first authors of
        the article, and title is the article title.
        None if the file should not be processed.
    """
    file = os.path.basename(path)
    if re.search('supplement[a-z]*( material)?(\\))?.pdf', file, re.IGNORECASE):
        return None  # Don't process supplementals
    if re.search(' - changes.pdf', file, re.IGNORECASE):
        return None  # Another ignored file
    assert file.endswith(".pdf")
    match = re.search('\\((.*?)( et al.)?\\) (.*).pdf', file)
    assert match, "Error parsing filename: " + file
    authors = match.group(1).split(', ')
    title = match.group(3)
    return (authors, title)


def gen_filename(record):
    """
    Guess the expected filename from the record.

    Args:
        record (dict): a record of the bibtex entry.

    Returns:
        A string which corresponds to guessed filename (expected to be a pdf).
    """
    record_copy = record.copy()
    record_copy = bibtexparser.customization.author(record_copy)

    # Retrieve a stripped down last name of the first authors
    last_names = []
    for author in record_copy['author']:
        stripped = utils.strip_accents(codecs.decode(author, "ulatex"))
        name = re.sub('([\\{\\}])', '', stripped.split(',')[0])
        name = re.sub('~', ' ', name)
        name = re.sub("\\\\'ı", "i", name)
        name = re.sub("\\\\`ı", "i", name)
        name = re.sub("ı", "i", name)
        name = re.sub('\xf8', 'o', name)
        last_names.append(name)

    # If there are more than 4 authors, use the 'et al.' form
    if len(last_names) > 4:
        prefix = '(' + last_names[0] + ' et al.) '
    else:
        prefix = '(' + ', '.join(last_names) + ') '

    title = utils.get_title(record_copy)
    title = re.sub('\\\\textendash  ', '- ', title)
    title = utils.strip_accents(codecs.decode(title, "ulatex"))
    title = re.sub('([\\{\\}])', '', title)
    title = re.sub(' *: ', ' - ', title)
    title = re.sub(' *— *', ' - ', title)
    title = re.sub('–', '-', title)
    title = re.sub('/', '-', title)
    title = re.sub('\\$\\mathplus \\$', '+', title)
    title = re.sub('\\\\textquotesingle ', "'", title)
    title = to_titlecase(title)
    title = re.sub('"', '', title)

    return prefix + title + '.pdf'


def gen_bibkey(record, all_keys):
    """
    Generate a unique bibtex key for the given record.

    Args:
        record (dict): a record of the bibtex entry.
        all_keys (set): a set of existing bibtex keys in the current context.

    Returns:
        A string which corresponds to the newly generated unique bibtex key.
        The argument 'all_keys' is also appended with the new key.
    """
    for field in ['year', 'title', 'author']:
        if field not in record:
            record_str = json.dumps(record, sort_keys=True, indent=4, separators=(',', ': '))
            raise ValueError("Missing field '{0}' in bibtex entry:\n{1}".format(field, record_str))

    record_copy = record.copy()
    record_copy = bibtexparser.customization.author(record_copy)

    # Retrieve a stripped down last name of the first author
    first_author = record_copy['author'][0]
    stripped = utils.strip_accents(codecs.decode(first_author, "ulatex"))
    last_name = stripped.split(',')[0]
    last_name = last_name.replace('ø', 'o')
    last_name = re.sub('([^a-zA-Z])', '', last_name)

    # Then get the first 3 initials of the article title
    curated_title = re.sub('([^a-zA-Z])', ' ', utils.get_title(record_copy))
    short_title = ''.join(s[0] for s in curated_title.split())
    short_title += curated_title.split()[-1][1:]
    short_title = short_title[:3].upper()

    # Key is Author:Year:Initials
    basekey = last_name + ":" + record_copy['year'] + ":" + short_title
    bibkey = basekey

    # Assign a unique key
    tail = 'a'
    while bibkey in all_keys:
        bibkey = basekey + tail
        tail = chr((ord(tail) + 1))

    all_keys.add(bibkey)
    return bibkey


def homogenize_latex_encoding(record):
    """
    Homogenize the latex encoding style for bibtex.

    Args:
        record (dict): a record.

    Returns:
        Customized record.
    """
    # Pre-processing
    for val in record:
        if val not in ('ID', 'file'):
            record[val] = record[val].replace('\\copyright', '©')
    # Apply functions from bibtexparser.customization
    record = bibtexparser.customization.convert_to_unicode(record)
    record = bibtexparser.customization.page_double_hyphen(record)
    # Reorganize authors
    record = bibtexparser.customization.author(record)
    if 'author' in record:
        stripped = [name.rstrip(', ') for name in record['author']]
        record['author'] = ' and '.join(stripped)
    # Convert to latex string and titlecase the title
    for val in record:
        if val not in ('ID', 'file'):
            # record[val] = bibtexparser.latexenc.string_to_latex(record[val])
            record[val] = re.sub('\\\\?&', '\\&', record[val])
            record[val] = record[val].replace('\\i', 'i')
            record[val] = record[val].replace('\n', ' ').replace('\r', '')
            record[val] = re.sub('\\\\textdollar \\\\textbackslash mathplus\\\\textdollar ', '+', record[val])
            record[val] = re.sub('\\$\\\\mathplus\\$', '+', record[val])
            record[val] = re.sub('\{́i\}', 'í', record[val])
            if val == 'title':
                record[val] = re.sub('GCMMA-two', 'GCMMA - two', record[val])
                record[val] = re.sub('ShapeOp—A', 'ShapeOp — A', record[val])
                record[val] = to_titlecase(record[val])
    return record
