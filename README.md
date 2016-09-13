Autobib
=======

Autobib is a python script that helps organizing your bibliography by automatizing mundane tasks such as querying `.bib` information from the web.
The way it works is that you simply provide `autobib.py` with the root of your folder tree containing all the pdfs you want to index, and it will automagically query information from the internet and create a nice `biblio.bib` out of it.
It can also do other stuff, such as autoformating you `.bib` files, generating unique keys, and so on.


This program has been tested with **Python 3.5**, and I don't know if it works with Python 2.7.


Examples
--------

##### Example 1:

    ./autobib.py /home/username/biblio -cgf

Will find all pdf in subdirectories of `/home/username/biblio`, retrieve bibtex entries from online databases [Crossref](http://www.crossref.org/) and [Google Scholar](https://scholar.google.fr/), and producde a nice formatted `biblio.bib` file in all folders containing pdfs.

Note that it only use filename information (no pdf metadata query yet), so each article needs to be named roughly like so:

    (Author1, Author2) Title of the paper.pdf

This can of course be customized, but you'll need to adapt the functions `parse_filename` and `gen_filename` to your liking.

##### Example 2:

    ./autobib.py /home/username/biblio -srm

Will synchronize the entries in your bibtex with the files in each folder (by updating the `file` field, or removing the entry if it does not exist). Then `-r` will rename the files according to the bibtex entries (the program always asks for confirmation before doing something). Finally, `-m` creates a `master.bib` file at the root folder that is being process (effectively merging and sorting each entry in subfolders).

Dependencies
------------

Pip only:

    pip3 install --user habanero scholarly bibtexparser latexcodec titlecase termcolor colorama

Mixed (Archlinux):

    sudo pacman -S python-termcolor python-colorama
    yaourt -S python-bibtexparser
    pip install --user habanero scholarly titlecase latexcodec


Usage
-----

    usage: autobib.py [-h] [-b] [-c] [-g] [-f] [-s] [-r] [-m] [-d] [filename]

    positional arguments:
      filename        input file/folder

    optional arguments:
      -h, --help      show this help message and exit
      -b, --backup    backup files upon writing
      -c, --crossref  query missing from Crossref
      -g, --google    query missing from Google Scholar
      -f, --format    format biblio
      -s, --sync      sync filenames and bib entries
      -r, --rename    rename files
      -m, --merge     merge bib files in subfolders into a master bib file
      -d, --delete    delete backuped files


How It Works
------------

This program relies heavily on the [python-bibtexparser](https://github.com/sciunto-org/python-bibtexparser) library for reading/writing formated bibtex files.

The queries are currently done using 2 different backends : [Crossref](http://www.crossref.org/) and [Google Scholar](https://scholar.google.fr/). Crossref provides a nice API, and returns results with very few false negative<sup>[1](#cr)</sup>. False positive and discarded according to the confidence score returned by Crossref.

Papers that were not matched using Crossref can be queried on Google Scholar, which doesn't offer a query API and might block you if you have too many requests. But it usually finds the more obscure references you might have in your library.

<sub><sup><a name="cr">1</a>: It might happen if you have a paper that has been published in little known conference, but has been republished latter in a higher-impact journal, by the same authors and under almost the same title. So be wary to always check the results that are returned by the online queries.</sup></sub>


Manual Override
---------------

Sometimes it happens that a result produced by Crossref or Google Scholar doesn't quite correspond to what you had in mind. Maybe the match is wrong, or maybe it's missing a piece of information. In that case, you can override the matched entry by providing your own record for the offending file.

By default, the results of the online queries are stored in a `.queried.bib` file in each processed folder. You can provide your own `.manual.bib` file, which contain entries that you wrote manually and that will override the results found in `.queried.bib`.

When calling `./autobib.py --format`, the program will read both `.queried.bib` and `.manual.bib` in each folder, and override entries from `.queried.bib` which are similar to  the ones in `.manual.bib`.


Customization
-------------

There is several aspects of `autobib.py` which can be customized. The 2 files that you can modify to fit your need are `nomenclature.py` and `config.py`.

* Functions `parse_filename` and `gen_filename` defines the expected naming convention of a file. By default it is something like `(Author1, Author2) Title of the paper.pdf`, but maybe you want to include the year, maybe you want to keep only the author initials.

* The function `gen_bibkey` defines how bibkey identifiers are generated when invoking `./autobib.py --format`. By default it uses ACM style `Sigmund:2001:ALT`.

* This file defines capitalization and pattern substitution rules. You can complete the lists of `uppercase_words` and `lowercase_words`. For now pattern substitutions are hardcorded, but this will change in the future.


Unicode Madness
---------------

Right now the whole situation is a little bit messy. Problematic characters are replaced using hardcoded substitutions everywhere. The current rule is to use UTF-8 encoding to write and read every file, even on Windows. So please make sure you do not have any weird accent written in a file that uses an exotic encoding, or it might create troubles.

Storing non-ASCII characters as their latex equivalent code is the best option for maximum compatibility, but I would also like to keep the possibility of using unicode characters, which pose no problem with modern alternatives such as `biblatex` and `biber`. Eventually I should provide an option for both strategies. But this will come later when I have the time to implement it correctly.


FAQ
---

##### Q1: The program crashed when parsing the filename of my paper?

> Are you sure your file is named according to the format `(%authors) %title.pdf`? Right now this is the only supported naming scheme, but this will be improved in the future. Please see the [customization](#customization) section for more information.

##### Q2: Can I skip a sub-folder that I do not want to be processed?

> Sure! Simply put an empty file named `.nobib` in this folder. There could be other options in the future, but for now this should be sufficient.

##### Q3: There are some weird characters in my results?

> Ah, this is probably the result of some encoding madness. Right now there are some hardcoded character substitutions written here and there in the code. This will be improved in the future, but right now all I can do it add more quick fix that works for you.

##### Q4: I have trouble with unicode characters on my Windows terminal.

> Try setting your environment variable `PYTHONIOENCODING` to `UTF-8`. More information on the subject can be found [here](http://stackoverflow.com/questions/507123/python-3-0-how-to-make-print-output-unicode) and [here](http://stackoverflow.com/questions/25127673/how-to-print-utf-8-to-console-with-python-3-4-windows-8).


Disclaimer
----------

This is heavily work-in-progress, so use at your own risks. I wrote this program to help me organize papers for my PhD thesis, so I know it works for me, but maybe you will not like the way I sort my bib entries, or the way I generate my bib keys, etc. In that case I encourage you to contribute or modify the script directly to fit your needs.

Also, there is no telling that the Google Scholar backend will still work tomorrow, because Google doesn't seem to like scripts too much and will probably eventually block it.


Roadmap
-------

Cf. the [TODO list](TODO.md).
