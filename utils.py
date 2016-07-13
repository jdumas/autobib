#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# System libs
import re
import os
import sys
import glob
import shutil
import filecmp
import difflib
import unicodedata

# Third party libs
import bibtexparser
from bibtexparser.bwriter import BibTexWriter
from bibtexparser.bparser import BibTexParser

# Local libs
import nomenclature


if sys.version_info.major == 2:
    TEXT_TYPE = unicode
else:
    TEXT_TYPE = str


MONTHS = [
    'jan',
    'feb',
    'mar',
    'apr',
    'may',
    'jun',
    'jul',
    'aug',
    'sep',
    'oct',
    'nov',
    'dec',
]


def strip_accents(s):
    return ''.join(c for c in unicodedata.normalize('NFD', s)
                   if unicodedata.category(c) != 'Mn')


def has_pdfs(folder):
    return len(glob.glob(os.path.join(folder, "*.pdf"))) > 0


def simratio(file1, file2):
    return difflib.SequenceMatcher(None, file1.lower(), file2.lower()).ratio()


def get_title(record):
    title = record['title']
    if 'booktitle' in record and record['ENTRYTYPE'] == 'book':
        if title:
            title = record['booktitle'] + ' - ' + title
        else:
            title = record['booktitle']
    return title


def most_similar_filename(guess, candidates):
    """
    Return the most similar filename amongst files in given folder.

    Args:
        guess (str): filename you want to find a match to.
        candidates (str or iterable): path of the folder to inspect, or sequence of candidates.

    Returns:
        A tuple (match, score), with the name of the most similar match in the
        given list, and the score of such a match.
    """
    best_score = 0.0
    best_file = ""
    if isinstance(candidates, str):
        candidates = os.listdir(candidates)
    for file in candidates:
        sc = simratio(guess, file)
        if sc > best_score:
            best_score = sc
            best_file = file
    return best_file, best_score


def multireplace(string, replacements):
    """
    Given a string and a replacement map, it returns the replaced string.
    Taken from https://gist.github.com/bgusach/a967e0587d6e01e889fd1d776c5f3729

    Args:
        string (str): string to execute replacements on
        replacements (dict): replacement dictionary {value to find: value to replace}

    Returns:
        The replaced string.
    """

    # Place longer ones first to keep shorter substrings from matching where the
    # longer ones should take place. For instance given the replacements
    # {'ab': 'AB', 'abc': 'ABC'} against the string 'hey abc', it should produce
    # 'hey ABC' and not 'hey ABc'.
    substrs = sorted(replacements, key=len, reverse=True)

    # Create a big OR regex that matches any of the substrings to replace.
    regexp = re.compile('|'.join(map(re.escape, substrs)))

    # For each match, look up the new string in the replacements.
    return regexp.sub(lambda match: replacements[re.escape(match.group(0))], string)


def write_with_backup(filename, new_content, use_backup=True):
    """
    Backup the given text file, provided it differs from new_content.

    Args:
        filename (str): absolute or relative path the file to backup.
        new_content (str): new content that will be written to filename.
        use_backup (bool): whether to actually backup the file or not.
    """

    # Find new backup filename
    if use_backup:
        backup = filename + '.bak'
        if os.path.exists(backup):
            index = 1
            while os.path.exists(backup):
                # If a backuped file has similar content, no need to do a new backup
                if filecmp.cmp(filename, backup, shallow=False):
                    return
                backup = filename + '.bak.' + str(index)
                index += 1
        if os.path.exists(filename):
            if new_content == open(filename).read():
                # If file to write is similar to the file to overwrite, do nothing
                return
            else:
                # Otherwise backup current file
                print('Backing up "' + os.path.basename(filename) + '"')
                shutil.move(filename, backup)

    # Write new content
    with open(filename, 'w') as file:
        file.write(new_content)


def sort_entries(db, order_entries_by):
    """
    Since it is has to sort by decreasing order using biblatex, here we sort
    entries manually.

    Args:
        db (BibDatabase): the database whose entries to sort.

    Returns:
        Nothing, but update the entries attribute of the input db.
    """
    def entry_sort_key(entry, fields):
        result = []
        for field in fields:
            if field == 'year':
                result.append(-int(entry.get(field, 0)))
            else:
                result.append(TEXT_TYPE(entry.get(field, '')).lower())
        return tuple(result)
    db.entries = sorted(db.entries, key=lambda x: entry_sort_key(x, order_entries_by))


def create_file_dict(db):
    """
    Generates a dictionary that maps a decoded file field to its index in the
    given database entry list.

    Args:
        db (BibDatabase): the database whose to index.

    Returns:
         A dictionary {filename: id} mapping decoded file fields to their index
         in the input database.
    """
    gen = ((i, x) for i, x in enumerate(db.entries) if 'file' in x)
    files = {decode_filename_field(x['file']): i for i, x in gen}
    return files


def guess_manual_files(folder, queried_db, update_queried_db=True):
    """
    Tries to guess which files in a folder correspond to entries placed in the
    `.manual.bib` file. This is useful for e.g. to avoid performing online queries
    for files which we know have a manual entry.

    If a '.manual.bib' is present, override corresponding queried entries
    The way it works is as follows:
      1. Guess the filename of each entry in `.manual.bib`
      2. Find entry in `.queried.bib` with the closest file name in its 'file' field
      3. Override with manual entry
    """
    files = create_file_dict(queried_db)
    manual_bib_path = os.path.join(folder, '.manual.bib')
    if os.path.exists(manual_bib_path):
        manual_database = read_bib_file(manual_bib_path, custom=True)
        for entry in manual_database.entries:
            guess = nomenclature.gen_filename(entry)
            file = encode_filename_field(guess)
            best_score = 0.0
            best_idx = -1
            # Compare again other file entries
            for key, idx in sorted(files.items()):
                sc = simratio(key, file)
                if sc > best_score:
                    best_score = sc
                    best_idx = idx
            # Update 'file' field
            match, _ = most_similar_filename(guess, folder)
            entry['file'] = encode_filename_field(match)
            # If best match is good enough, override old entry
            if update_queried_db:
                if best_score > 0.95:
                    queried_db.entries[best_idx] = entry
                else:
                    queried_db.entries.append(entry)
            else:
                files[match] = -1
    return files


def read_bib_file(filename, custom=False):
    """
    Read bibtex file.

    Args:
        filename (str): path of the bibtex file.
        custom (bool): whether to homogenize the entries upon reading.

    Returns:
        A BibDatabase object.
    """

    # Read input bibtex file
    bibtex_str = ""
    if os.path.exists(filename):
        with open(filename, 'r') as bibfile:
            bibtex_str = bibfile.read()

    # Choose parser
    parser = None
    if custom:
        parser = BibTexParser()
        parser.customization = nomenclature.homogenize_latex_encoding

    # Create database from string
    return bibtexparser.loads(bibtex_str, parser=parser)


def write_bib(db, order=False):
    """
    Write bibtex string.

    Args:
        db (BibDatabase): database object to dump..
        order (bool): whether to reorder entries upon writing.

    Returns:
        The dumped string.
    """

    # Custom writer
    writer = BibTexWriter()
    writer.indent = '\t'
    writer.order_entries_by = None

    if order:
        # Manual sort
        order_entries_by = ('year', 'author', 'ID')
        sort_entries(db, order_entries_by)

    # Write bib string
    return writer.write(db)


def encode_filename_field(filename):
    """
    Create an escaped bibtex field with the relative file path.

    Args:
        filename (str): absolute or relative name of the file.

    Returns:
        A string which corresponds to the escaped field to be used
    """
    assert filename.endswith(".pdf")
    return ':' + filename.replace(':', '\\:') + ':PDF'


def decode_filename_field(text):
    """
    Interpret a file field.

    Args:
        text (str): content of the field.

    Returns:
        A string which corresponds to the decoded file name.
    """
    assert text.endswith(":PDF")
    match = re.search(':(.*):PDF', text)
    assert match
    filename = match.group(1).replace('\\:', ':')
    return filename
