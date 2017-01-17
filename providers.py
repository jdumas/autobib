#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# System libs
import re
import difflib

# Third party libs
import termcolor
import bibtexparser
import scholarly
from habanero import Crossref, cn

# Local libs
import config
import utils
import nomenclature
import fix_scholarly


def print_score(sc):
    if sc >= 3:
        color = "green"
    elif sc >= 2:
        color = "yellow"
    else:
        color = "red"
    print("Score: " + termcolor.colored(sc, color))


def score_type(s):
    """
    Assign a score to a work type depending on a user-defined preference list.
    The list of available types can be obtained via the following url:
    http://api.crossref.org/types
    """
    preference_list = [
        "journal-article",
        "book"
    ]
    if s in preference_list:
        return preference_list.index(s) + 1
    else:
        return 0


def pick_best(title, item1, item2):
    """
    Pick best record among two items with identical scores.
    """
    def compare(x):
        return difflib.SequenceMatcher(None, title.lower(), x.lower()).ratio()
    if not item1['title']:
        return item2
    elif not item2['title']:
        return item2
    r1 = compare(item1['title'][0])
    r2 = compare(item2['title'][0])
    if r1 > r2:
        return item1
    elif r2 > r1:
        return item2
    else:
        # Try to find other discriminating criteria... e.g. prefer journal-articles
        if score_type(item1["type"]) > score_type(item2["type"]):
            return item1
        else:
            return item2


def crossref_query(authors, title):
    """
    Query Crossref database.

    Args:
        authors (list): a list of strings for up the first authors last names.
        title (str): the title of the article.
        filename (str): the original path of the file to link to.

    Returns:
        A tuple (bibtex, json, score) where the first element is the data in
        bibtex format (returned as a record/dict), the second element is the
        data returned in json format, and the third element is the score of the
        match given by Crossref.
    """
    cr = Crossref()
    query = ['+"' + name + '"' for name in authors]
    query = ' '.join(query) + ' +"' + title + '"'
    x = cr.works(query=query)
    assert x['status'] == "ok"

    # No result found
    if not x['message']['items']:
        print_score(0)
        return (None, [], 0)

    best_item = x['message']['items'][0]
    for item in x['message']['items']:
        if item['score'] < best_item['score']:
            break
        else:
            best_item = pick_best(title, best_item, item)

    # Retrieve DOI and json item
    doi = best_item['DOI']
    res_json = best_item

    # If the entry is invalid, return a score of 0
    if 'author' not in res_json or not res_json['title']:
        print_score(0)
        return (None, res_json, 0)

    # Retrieve metadata as bibtex entry
    res_bib = cn.content_negotiation(ids=doi, format="bibentry")
    res_bib = re.sub('Ă¤', 'ä', res_bib)
    res_bib = re.sub('Ă', 'Ö', res_bib)
    res_bib = re.sub('รถ', 'ö', res_bib)
    res_bib = re.sub('Ăź', 'ü', res_bib)
    res_bib = re.sub('Ěo', 'ö', res_bib)
    res_bib = re.sub('ďż˝', 'ø', res_bib)
    res_bib = re.sub('ĂŤ', 'ë', res_bib)
    db = bibtexparser.loads(res_bib)
    assert len(db.entries) == 1
    res_bib = db.entries[0]

    # If article has subtitle(s), fix bibtex entry
    subtitles = [x for x in res_json['subtitle'] if not str.isupper(x)]
    if len(subtitles) > 0:
        # Discard subtitle that are all uppercase
        title = ' '.join(res_json['title'])
        subtitle = ' '.join(subtitles)
        if title.lower().startswith(subtitle.lower()) or utils.simratio(title, subtitle) > 0.95:
            # Don't repeat title if the subtitle is too similar to the title
            new_title = title
        else:
            new_title = title + ": " + subtitle
        res_bib['title'] = new_title
    else:
        new_title = ' '.join(res_json['title'])
        res_bib['title'] = new_title

    # Post-process title
    res_bib['title'] = re.sub('\\*$', '', res_bib['title'])
    res_bib['title'] = re.sub('^[0-9]*\\. ', '', res_bib['title'])
    res_bib['title'] = re.sub('\\.*$', '', res_bib['title'])

    # If bibtex entry has a 'journal' field, then use the longest alias from the json
    if 'journal' in res_bib:
        best = ""
        for container in res_json['container-title']:
            if len(container) > len(best):
                best = container
        res_bib['journal'] = best

    # If entry is missing the year, set score to 0
    score = res_json['score']
    if 'year' not in res_bib:
        score = 0

    # Fix incorrect year in crossref entry
    if 'published-print' in res_json:
        item = res_json['published-print']
        if 'date-parts' in item and len(item['date-parts']) == 1:
            date = item['date-parts'][0]
            year = date[0]
            month = date[1] if len(date) > 1 else None
            if str(year) != res_bib['year']:
                res_bib['year'] = str(year)
                if month is None and 'month' in res_bib:
                    del res_bib['month']
                elif month is not None:
                    assert month >= 1 and month <= 12
                    month_str = utils.MONTHS[month - 1]
                    res_bib['month'] = month_str

    # Fix potential ambiguous author entries
    msg = utils.fix_author_field(res_bib, res_json)

    print('C: ' + nomenclature.gen_filename(res_bib))
    print_score(score)

    # If score is above threshold, display msg from fix_author_field
    if score >= config.crossref_accept_threshold and msg:
        print(msg)

    # Return database entry
    return (res_bib, res_json, score)


def scholarly_query(authors, title):
    """
    Query Google Scholar database.

    Args:
        authors (list): a list of strings for up the first authors last names.
        title (str): the title of the article.

    Returns:
        A record (dict) of the bibtex entry obtained from Google Scholar.
    """
    query = ' '.join(authors) + ' ' + title
    search_query = scholarly.search_pubs_query(query)
    try:
        res = next(search_query)
    except StopIteration:
        return None
    res.fill()
    if 'abstract' in res.bib:
        del res.bib['abstract']

    # Post-process title
    res.bib['title'] = re.sub('\\.*$', '', res.bib['title'])

    print('S: ' + nomenclature.gen_filename(res.bib))
    return res.bib


def zotero_query(_authors, _title):
    return None
