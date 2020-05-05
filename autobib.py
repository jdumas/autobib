#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# System libs
import re
import os
import ast
import sys
import json
import argparse

# Third party libs
import colorama
import termcolor
from loguru import logger
from bibtexparser.bibdatabase import BibDatabase

# Local libs
import config
import utils
import nomenclature
import providers

# Python 2/3 compatibility
try:
    input = raw_input
except NameError:
    pass


def query_crossref_folder(folder, use_backup):
    """
    Query metadata information for unmatched pdf files in the given folder.
    This function only queries Crossref.

    Args:
        folder (str): absolute or relative path to the folder to process.
        use_backup (bool): whether to backup previous files before writing.

    Returns:
        Nothing, but writes the queried databases in bibtex format in the given
        folder (and backup previous database if it differed).
    """

    # Create database
    db = utils.read_bib_file(os.path.join(folder, '.queried.bib'))
    files = utils.guess_manual_files(folder, db, update_queried_db=False)
    utils.add_skip_files(folder, files)
    json_entries = []
    rejected = []

    # For each pdf in the folder
    for path in utils.get_pdf_list(folder):
        file = os.path.basename(path)
        parsed = nomenclature.parse_filename(file)
        if parsed is None or file in files:
            continue
        print('Q: ' + os.path.basename(file))
        authors, title = parsed

        # Crossref
        rbib, rjson, score = providers.crossref_query(authors, title)
        if score >= config.crossref_accept_threshold:
            # Append filename and store entry
            rbib['file'] = utils.encode_filename_field(file)
            json_entries.append(rjson)
            db.entries.append(rbib)
        else:
            rejected.append(os.path.basename(file))

    # Store results
    bib_path = os.path.join(folder, '.queried.bib')
    utils.write_with_backup(bib_path, utils.write_bib(db, order=False), use_backup)
    json_path = os.path.join(folder, '.queried.json')
    json_str = json.dumps(json_entries, sort_keys=True, indent=4, separators=(',', ': '))
    utils.write_with_backup(json_path, json_str, use_backup)
    rejected_path = os.path.join(folder, '.rejected.txt')
    if len(rejected) > 0:
        utils.write_with_backup(rejected_path, '\n'.join(rejected), use_backup)


def query_google_folder(folder, use_backup):
    """
    Query metadata information for unmatched pdf files in the given folder.
    This function only queries Google Scholar.

    Args:
        folder (str): absolute or relative path to the folder to process.
        use_backup (bool): whether to backup previous files before writing.

    Returns:
        Nothing, but writes the queried databases in bibtex format in the given
        folder (and backup previous database if it differed).
    """

    # Create database
    db = utils.read_bib_file(os.path.join(folder, '.queried.bib'))
    files = utils.guess_manual_files(folder, db, update_queried_db=False)
    utils.add_skip_files(folder, files)

    for path in utils.get_pdf_list(folder):
        file = os.path.basename(path)
        parsed = nomenclature.parse_filename(file)
        if parsed is None or file in files:
            continue
        print('Q: ' + os.path.basename(file))
        authors, title = parsed

        # Google Scholar
        rbib = providers.scholarly_query(authors, title)
        if rbib is None:
            continue

        # Append filename and store entry
        rbib['file'] = utils.encode_filename_field(file)
        db.entries.append(rbib)

    # Store results
    bib_path = os.path.join(folder, '.queried.bib')
    utils.write_with_backup(bib_path, utils.write_bib(db, order=False), use_backup)


def format_folder(folder, use_backup, context=None):
    """
    Pretty print bibtex file in the given folder.
    This function looks for a file named 'queried.bib' in the given folder,
    and use it as an input to pretty print a file called 'biblio.bib'.

    Args:
        folder (str): absolute or relative path to the folder to process.
        use_backup (bool): whether to backup previous files before writing.
        context (set): set of existing bibtex keys in the current context.

    Returns:
        Nothing, but writes the results in a file called 'biblio.bib'.
    """

    # Create database
    db = utils.read_bib_file(os.path.join(folder, '.queried.bib'), homogenize=True)
    utils.guess_manual_files(folder, db, update_queried_db=True)

    if context is None:
        context = set()

    # Generate bibkeys
    for entry in db.entries:
        entry['ID'] = nomenclature.gen_bibkey(entry, context)

    # Write output bibtex file
    output_bib_path = os.path.join(folder, 'biblio.bib')
    output_bib_str = utils.write_bib(db, order=True)
    utils.write_with_backup(output_bib_path, output_bib_str, use_backup)


def rename_folder(folder, use_backup):
    """
    Rename the pdf files in the given folder according to the information found
    in `biblio.bib`. Note that this function will update file entries in
    `biblio.bib`, but also in `.queried.bib`.

    Args:
        folder (str): absolute or relative path to the folder to process.
        use_backup (bool): whether to backup previous files before writing.

    Returns:
        Nothing, but renames the pdfs in the given folder, and update bib files.
    """

    # Read input bib files
    pretty_bib_path = os.path.join(folder, 'biblio.bib')
    pretty_db = utils.read_bib_file(pretty_bib_path)
    queried_bib_path = os.path.join(folder, '.queried.bib')
    queried_db = utils.read_bib_file(queried_bib_path)
    queried_files = utils.create_file_dict(queried_db)

    # Iterate over db entries
    need_rename = False
    for entry in pretty_db.entries:
        old_filename = utils.decode_filename_field(entry['file'])
        new_filename = nomenclature.gen_filename(entry)
        if not os.path.exists(os.path.join(folder, old_filename)):
            print(termcolor.colored('file not found: ', 'red') + old_filename)
        elif old_filename != new_filename:
            need_rename = True
            print(termcolor.colored('-', 'red') + old_filename)
            print(termcolor.colored('+', 'green') + new_filename)

    # Skip if nothing to rename
    if not need_rename:
        return

    # Ask confirmation
    cmd = input('(Y/n) ')
    if cmd == '' or cmd == 'y' or cmd == 'Y':
        for entry in pretty_db.entries:
            old_filename = utils.decode_filename_field(entry['file'])
            new_filename = nomenclature.gen_filename(entry)
            old_path = os.path.join(folder, old_filename)
            new_path = os.path.join(folder, new_filename)
            if os.path.exists(old_path):
                os.rename(old_path, new_path)
                new_val = utils.encode_filename_field(new_filename)
                if old_filename in queried_files:
                    idx = queried_files[old_filename]
                    queried_db.entries[idx]['file'] = new_val
                entry['file'] = new_val

    # Write output bibtex files
    utils.write_with_backup(pretty_bib_path, utils.write_bib(pretty_db, order=False), use_backup)
    utils.write_with_backup(queried_bib_path, utils.write_bib(queried_db, order=False), use_backup)


def sync_folder(folder, use_backup):
    """
    Update the file field of bibtex entries for the given folder.
    When an entry could not find a good match, it will be removed from the
    bibtex, unless the user explicitly prevents it.

    Args:
        folder (str): absolute or relative path to the folder to process.
        use_backup (bool): whether to backup previous files before writing.

    Returns:
        Nothing, but updates `.queried.bib` and `biblio.bib` files.
    """
    for bib_file in ('.queried.bib', 'biblio.bib'):
        bib_path = os.path.join(folder, bib_file)
        db = utils.read_bib_file(bib_path)
        unmatched = set([os.path.basename(f) for f in utils.get_pdf_list(folder)])
        to_delete = []
        for i, entry in enumerate(db.entries):
            guess = nomenclature.gen_filename(entry)
            if 'file' in entry:
                guess = utils.decode_filename_field(entry['file'])
            match, score = utils.most_similar_filename(guess, unmatched)
            if score >= 0.90:
                unmatched.remove(match)
                entry['file'] = utils.encode_filename_field(match)
            else:
                print(termcolor.colored(bib_file, "magenta") +
                      ": ({1}) will remove '{0}'".format(guess, termcolor.colored(score, "yellow")))
                to_delete.append(i)

        # Delete unmatched entries
        if to_delete:
            cmd = input('(Y/n) ')
            if cmd == '' or cmd == 'y' or cmd == 'Y':
                for i in sorted(to_delete, reverse=True):
                    del db.entries[i]

        # Write synced database
        utils.write_with_backup(bib_path, utils.write_bib(db, order=False), use_backup)


def merge_folder_tree(folder, use_backup):
    """
    Merge bib files from the current subtree into a master bib file at the root.
    This function updates the 'file' link of each entry with the relative path
    to each subfolder that has been processed.

    Args:
        folder (str): relative or absolute path of the folder to process.

    Returns:
        Nothing, but creates a file named `master.bib` in the given folder.
    """
    db = BibDatabase()
    for subdir, _dirs, _files in os.walk(os.path.abspath(folder)):
        if os.path.exists(os.path.join(subdir, '.nobib')):
            continue  # Skip blacklisted folders
        reldir = os.path.relpath(subdir, os.path.abspath(folder))
        bib_path = os.path.join(subdir, 'biblio.bib')
        subdb = utils.read_bib_file(bib_path)
        for entry in subdb.entries:
            filename = utils.decode_filename_field(entry['file'])
            filename = os.path.join(reldir, filename)
            entry['file'] = utils.encode_filename_field(filename)
        db.entries += subdb.entries
    # Remove duplicated entries
    entries_dict = db.entries_dict
    db.entries = [val for key, val in entries_dict.items()]
    # Write result
    bib_path = os.path.join(folder, 'master.bib')
    utils.write_with_backup(bib_path, utils.write_bib(db, order=True), use_backup)


def clean_folder_tree(folder):
    """
    Removed backup files from the given folder tree.
    Backup are files that ends with .bak or .bak

    Args:
        folder (str): relative or absolute path of the folder to cleanup.
    """
    res = []
    for subdir, _dirs, files in os.walk(folder):
        if os.path.exists(os.path.join(subdir, '.nobib')):
            continue  # Skip blacklisted folders
        files = [f for f in os.listdir(subdir) if re.search('.*\\.bak([0-9]*)?', f)]
        res = res + [os.path.join(subdir, f) for f in files]
    for path in res:
        assert os.path.exists(path)
        print("will remove '" + path + "'")
    if len(res) == 0:
        print("nothing to delete")
    else:
        cmd = input("confirm deletion (y/N) ")
        if cmd == 'y':
            for path in res:
                os.remove(path)


def format_file(filename, use_backup):
    """
    Format a single bib file.

    Args:
        filename (str): relative or absolute path of the file to process.

    Returns:
        Nothing, but update the given file.
    """
    db = utils.read_bib_file(filename, homogenize=True)
    # Generate bibkeys
    context = set()
    subst = {}
    for entry in db.entries:
        old_key = entry['ID']
        new_key = nomenclature.gen_bibkey(entry, context)
        entry['ID'] = new_key
        if old_key != new_key:
            subst[old_key] = new_key
    utils.write_with_backup(filename, utils.write_bib(db, order=True), use_backup)
    utils.write_remap_script(subst, os.path.dirname(filename))


def extract_from_file(filename, output_folder):
    """
    Extract citation from a given .bib file, and write the resulting list in a
    '.biblist' in the given folder.
    """
    db = utils.read_bib_file(filename, homogenize=False)
    outfile = os.path.join(output_folder, ".biblist")
    if os.path.exists(outfile):
        cmd = input("overwrite existing file '{0}' (y/N) ".format(outfile))
        if cmd != 'y':
            return
    filenames = sorted([nomenclature.gen_filename(entry) for entry in db.entries])
    with open(outfile, 'w') as f:
        for name in filenames:
            f.write(name)
            f.write('\n')


def remap_keys(old_filename, new_filename, output_folder):
    """
    Create a script to remap bibtex keys from one .bib file to another.

    This function uses the edit distance on filenames generated from a bitex entry
    to compare entries together, and greedily matches old entries to new entries.
    """
    old_db = utils.read_bib_file(old_filename, homogenize=False)
    new_db = utils.read_bib_file(new_filename, homogenize=False)
    old_list = {}
    new_list = {}
    subst = {}
    for entry in new_db.entries:
        name = nomenclature.gen_filename(entry)
        new_list[name] = entry['ID']
    for entry in old_db.entries:
        name = nomenclature.gen_filename(entry)
        if name in new_list.keys():
            subst[entry['ID']] = new_list[name]
            del new_list[name]
        else:
            old_list[name] = entry['ID']
    for name, bibkey in new_list.items():
        match, score = utils.most_similar_filename(name, old_list.keys())
        if score < 0.90:
            print(termcolor.colored("Warning: potentially incorrect substitution:", 'yellow', attrs=["bold"]))
            print(termcolor.colored('-', 'red') + match)
            print(termcolor.colored('+', 'green') + name)
        subst[old_list[match]] = bibkey
    utils.write_remap_script(subst, output_folder)


def apply_folder_tree(folder, func, *args):
    for subdir, _dirs, _files in os.walk(folder):
        if os.path.exists(os.path.join(subdir, '.nobib')):
            continue  # Skip blacklisted folders
        if utils.has_pdfs(subdir):
            print(termcolor.colored('Entering: ' + subdir, "cyan", attrs=["bold"]))
            func(subdir, *args)


def parse_args():
    parser = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('filename', nargs='?', help="input file/folder")
    parser.add_argument('extra', nargs='?', default='.',
                        help="extra argument (if applicable)")
    parser.add_argument('-b', '--backup', action='store_true', help="backup files upon writing")
    parser.add_argument('-B', '--no-backup', dest='backup', action='store_false', help="disable backup files")
    parser.set_defaults(backup=True)
    parser.add_argument('-c', '--crossref', default=False, action='store_true',
                        help="query missing from Crossref")
    parser.add_argument('-g', '--google', default=False, action='store_true',
                        help="query missing from Google Scholar")
    parser.add_argument('-f', '--format', default=False, action='store_true',
                        help="format biblio")
    parser.add_argument('-s', '--sync', default=False, action='store_true',
                        help="sync filenames and bib entries")
    parser.add_argument('-r', '--rename', default=False, action='store_true',
                        help="rename files")
    parser.add_argument('-m', '--merge', default=False, action='store_true',
                        help="merge bib files in subfolders into a master bib file")
    parser.add_argument('-d', '--delete', default=False, action='store_true',
                        help="delete backuped files")
    parser.add_argument('-e', '--extract', default=False, action='store_true',
                        help="extract pdfs names from bibtex")
    parser.add_argument('-k', '--compare', default="",
                        help="create a script to remap bibtex entries from one .bib to another")
    parser.add_argument('-t', '--tol', default=config.crossref_accept_threshold,
                        type=float, help="set crossref tolerance")
    parser.add_argument('-u', '--utf8', default=config.use_utf8_characters, type=ast.literal_eval,
                        help="write utf8 characters in output .bib")
    return parser.parse_args()


if __name__ == "__main__":
    def run():
        colorama.init()
        logger.remove()
        logger.add(sys.stdout, colorize=True, format="<green>{time:HH:mm}</green> <level>{message}</level>")
        args = parse_args()
        input_path = "."
        if args.filename:
            input_path = args.filename
        # Set config from command line
        config.crossref_accept_threshold = args.tol
        config.use_utf8_characters = bool(args.utf8)
        # If input path is a bib file
        if input_path.endswith('.bib'):
            assert os.path.isfile(input_path)
            # Format biblio
            if args.format:
                format_file(input_path, args.backup)
            # Extract pdf list from bibtex
            if args.extract:
                extract_from_file(input_path, args.extra)
            # Remap bibtex entries
            if args.compare.endswith('.bib'):
                remap_keys(args.compare, input_path, args.extra)
        else:
            assert os.path.isdir(input_path)
            # Crossref query
            if args.crossref:
                apply_folder_tree(input_path, query_crossref_folder, args.backup)
            # Google scholar query
            if args.google:
                apply_folder_tree(input_path, query_google_folder, args.backup)
            # Format biblio
            if args.format:
                context = set()
                apply_folder_tree(input_path, format_folder, args.backup, context)
            # Sync filenames
            if args.sync:
                apply_folder_tree(input_path, sync_folder, args.backup)
            # Rename files
            if args.rename:
                apply_folder_tree(input_path, rename_folder, args.backup)
            # Merge bib entries
            if args.merge:
                merge_folder_tree(input_path, args.backup)
            # Cleanup backup files
            if args.delete:
                clean_folder_tree(input_path)

    run()
