#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# Local libs
import utils

# Third party libs
import codecs
import latexcodec
import bibtexparser

# System libs
import re
import os
import json


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
    if re.search('supplement[a-z]*( material)?(\))?.pdf', file, re.IGNORECASE):
        return None  # Don't process supplementals
    assert(file.endswith(".pdf"))
    match = re.search('\((.*?)( et al.)?\) (.*).pdf', file)
    assert(match)
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
        name = re.sub('([\{\}])', '', stripped.split(',')[0])
        name = re.sub('~', ' ', name)
        name = re.sub("\\\\'ı", "i", name)
        name = re.sub("\\\\`ı", "i", name)
        last_names.append(name)

    # If there are more than 4 authors, use the 'et al.' form
    if len(last_names) > 4:
        prefix = '(' + last_names[0] + ' et al.) '
    else:
        prefix = '(' + ', '.join(last_names) + ') '

    title = record_copy['title']
    title = re.sub('\\\\textendash  ', '- ', title)
    title = utils.strip_accents(codecs.decode(title, "ulatex"))
    title = re.sub('([\{\}])', '', title)
    title = re.sub(' *: ', ' - ', title)
    title = re.sub(' *— *', ' - ', title)
    title = re.sub('–', '-', title)
    title = re.sub('\$\\mathplus \$', '+', title)
    title = re.sub('\\\\textquotesingle ', "'", title)
    title = utils.to_titlecase(title)
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
    if 'year' not in record:
        record_str = json.dumps(record, sort_keys=True, indent=4, separators=(',', ': '))
        raise ValueError("Field 'year' not present in bibtex entry:\n" + record_str)

    record_copy = record.copy()
    record_copy = bibtexparser.customization.author(record_copy)

    # Retrieve a stripped down last name of the first author
    first_author = record_copy['author'][0]
    stripped = utils.strip_accents(codecs.decode(first_author, "ulatex"))
    last_name = stripped.split(',')[0]
    last_name = re.sub('([^a-zA-Z])', '', last_name)

    # Then get the first 3 initials of the article title
    curated_title = re.sub('([^a-zA-Z])', ' ', record_copy['title'])
    short_title = ''.join(s[0] for s in curated_title.split())
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
