#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# System libs
import os
import glob
import shutil
import argparse
import tempfile
import subprocess

# Third party libs
import colorama
import termcolor
from pdfrw import PdfReader
from PyPDF2 import PdfFileReader

# Python 2/3 compatibility
try:
    input = raw_input
except NameError:
    pass


def decrypt_pdf(filename):
    try:
        PdfReader(filename)
    except ValueError:
        print("-- Could not read pdf, decrypting: {}".format(os.path.basename(filename)))
        with tempfile.NamedTemporaryFile(suffix=".pdf", prefix="decrypted_", delete=False) as tmp:
            args = ['pdftk', filename, 'output', tmp.name, 'allow', 'AllFeatures']
            subprocess.check_call(args)
            shutil.move(tmp.name, filename)


def is_valid(name):
    if not name:
        return False
    if name == '.pdf':
        return False
    if name.endswith('.dvi') or name.endswith('.docx'):
        return False
    if '/' in name:
        return False
    return True


def shorten_authors(name):
    return ', '.join(name.split(',')[:3])


def rename_pdf(filename):
    """
    Rename a pdf file based on title meta-data.

    Args:
        filename (str): Path of the pdf file to rename

    """
    # Extract pdf title from pdf file
    print(filename)
    # r = PdfFileReader(filename)
    # info = r.getDocumentInfo()
    # print("pypdf: ", info.author, info.title)

    reader = PdfReader(filename)
    title = reader.Info.Title
    author = reader.Info.Author
    new_name = ""
    if author is not None:
        if author.decode():
            new_name += '({})'.format(shorten_authors(author.decode()))
    if title is not None:
        if new_name:
            new_name += ' '
        new_name += '{}'.format(title.decode())
    new_name += '.pdf'
    root_folder = os.path.dirname(filename)
    base_name = os.path.basename(filename)
    if new_name == base_name:
        print('-- Filename is already ok: {}'.format(new_name))
        return  # Nothing to do
    if is_valid(new_name):
        new_path = os.path.join(root_folder, new_name)
        if os.path.exists(new_path):
            print('-- File already exists: {} -> {}'.format(base_name, new_name))
        else:
            print('-- Renaming {} -> {}'.format(base_name, new_name))
            os.rename(filename, new_path)
    # else:
    #     print('-- New name not valid: {}'.format(new_name))


def iterate_folder(path, function):
    for filename in glob.glob(os.path.join(path, '*.pdf')):
        function(filename)


def parse_args():
    parser = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('input', default='.', nargs='?', help="input file/folder")
    parser.add_argument('-d', '--decrypt', action='store_true', help="decrypt protected pdfs")
    return parser.parse_args()


def main():
    colorama.init()
    args = parse_args()
    function = decrypt_pdf if args.decrypt else rename_pdf
    if os.path.isdir(args.input):
        iterate_folder(args.input, function)
    elif args.input.endswith('.pdf'):
        function(args.input)


if __name__ == "__main__":
    main()
