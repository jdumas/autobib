# Local libs
import utils
import nomenclature

# Third party libs
import termcolor
import bibtexparser
import scholarly
from habanero import Crossref, cn

# System libs
import re
import difflib


def print_score(sc):
    if sc >= 3:
        color = "green"
    elif sc >= 2:
        color = "yellow"
    else:
        color = "red"
    print("Score: " + termcolor.colored(sc, color))


def pick_best(authors, title, item1, item2):
    """
    Pick best record among two items with identical scores.
    """
    def compare(x):
        return difflib.SequenceMatcher(None, title.lower(), x.lower()).ratio()
    r1 = compare(item1['title'][0])
    r2 = compare(item2['title'][0])
    return item1 if r1 > r2 else item2


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
    assert(x['status'] == "ok")

    best_item = x['message']['items'][0]
    for item in x['message']['items']:
        if item['score'] < best_item['score']:
            break
        else:
            best_item = pick_best(authors, title, best_item, item)

    # Retrieve DOI and json item
    doi = best_item['DOI']
    res_json = best_item

    # Retrieve metadata as bibtex entry
    res_bib = cn.content_negotiation(ids=doi, format="bibentry")
    res_bib = re.sub('Ă¤', 'ä', res_bib)
    db = bibtexparser.loads(res_bib)
    assert(len(db.entries) == 1)
    res_bib = db.entries[0]

    # If article has subtitle(s), fix bibtex entry
    subtitles = [x for x in res_json['subtitle'] if not str.isupper(x)]
    if len(subtitles) > 0:
        # Discard subtitle that are all uppercase
        title = ' '.join(res_json['title'])
        subtitle = ' '.join(subtitles)
        if utils.simratio(title, subtitle) > 0.95:
            # Don't repeat title if the subtitle is too similar to the title
            new_title = title
        else:
            new_title = title + ": " + subtitle
        res_bib['title'] = new_title
    else:
        new_title = ' '.join(res_json['title'])
        res_bib['title'] = new_title

    # Post-process title
    res_bib['title'] = re.sub('\*$', '', res_bib['title'])
    res_bib['title'] = re.sub('^[0-9]*\. ', '', res_bib['title'])

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

    print('C: ' + nomenclature.gen_filename(res_bib))
    print_score(score)

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
    res = next(search_query)
    res.fill()
    if 'abstract' in res.bib:
        del res.bib['abstract']
    print('S: ' + nomenclature.gen_filename(res.bib))
    return res.bib


def zotero_query(authors, title):
    return None
