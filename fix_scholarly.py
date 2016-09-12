#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""scholarly.py"""

from __future__ import absolute_import, division, print_function, unicode_literals

import re
import sys
import time
import random
import hashlib
import requests
import scholarly

from bs4 import BeautifulSoup

_GOOGLEID = hashlib.md5(str(random.random()).encode('utf-8')).hexdigest()[:16]
_COOKIES = {'GSP': 'ID={0}:CF=4'.format(_GOOGLEID)}
_HEADERS = {
    'accept-language': 'en-US,en',
    'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Ubuntu Chromium/41.0.2272.76 Chrome/41.0.2272.76 Safari/537.36',
    'accept': 'text/html,application/xhtml+xml,application/xml'
}
_SCHOLARHOST = 'https://scholar.google.com'
_PUBSEARCH = '/scholar?q={0}'
_AUTHSEARCH = '/citations?view_op=search_authors&hl=en&mauthors={0}'
_KEYWORDSEARCH = '/citations?view_op=search_authors&hl=en&mauthors=label:{0}'
_CITATIONAUTH = '/citations?user={0}&hl=en'
_CITATIONAUTHRE = r'user=([\w-]*)'
_CITATIONPUB = '/citations?view_op=view_citation&citation_for_view={0}'
_CITATIONPUBRE = r'citation_for_view=([\w-]*:[\w-]*)'
_SCHOLARPUB = '/scholar?oi=bibs&hl=en&cites={0}'
_SCHOLARPUBRE = r'cites=([\w-]*)'
_SCHOLARCITERE = r'gs_ocit\(event,\'([\w-]*)\''
_SESSION = requests.Session()
_PAGESIZE = 100


def _get_page(pagerequest):
    """Return the data for a page on scholar.google.com"""
    # Note that we include a sleep to avoid overloading the scholar server
    time.sleep(5 + random.uniform(0, 5))
    # Deal with local / absolute url requests
    if pagerequest.startswith('/'):
        pagerequest = _SCHOLARHOST + pagerequest
    resp_url = _SESSION.get(pagerequest, headers=_HEADERS, cookies=_COOKIES)
    if resp_url.status_code == 200:
        return resp_url.text
    if resp_url.status_code == 503:
        # Inelegant way of dealing with the G captcha
        dest_url = requests.utils.quote(pagerequest)
        g_id_soup = BeautifulSoup(resp_url.text, 'html.parser')
        g_id = g_id_soup.findAll('input')[1].get('value')
        # Get the captcha image
        captcha_url = _SCHOLARHOST + '/sorry/image?id={0}'.format(g_id)
        captcha = _SESSION.get(captcha_url, headers=_HEADERS)
        # Upload to remote host and display to user for human verification
        img_upload = requests.post(
            'http://postimage.org/',
            files={'upload[]': ('scholarly_captcha.jpg', captcha.text)})
        img_url_soup = BeautifulSoup(img_upload.text, 'html.parser')
        img_url = img_url_soup.findAll(alt='scholarly_captcha')[0].get('src')
        print('CAPTCHA image URL: {0}'.format(img_url))
        # Need to check Python version for input
        if sys.version[0] == "3":
            g_response = input('Enter CAPTCHA: ')
        else:
            g_response = raw_input('Enter CAPTCHA: ')
        # Once we get a response, follow through and load the new page.
        url_response = _SCHOLARHOST + '/sorry/CaptchaRedirect?continue={0}&id={1}&captcha={2}&submit=Submit'.format(dest_url, g_id, g_response)
        resp_captcha = _SESSION.get(url_response, headers=_HEADERS)
        print('Forwarded to {0}'.format(resp_captcha.url))
        res = _get_page(re.findall(r'https:\/\/(?:.*?)(\/.*)', resp_captcha.url)[0])
        print(res)
        return res
    else:
        raise Exception('Error: {0} {1}'.format(resp_url.status_code, resp_url.reason))


# Monkey patching the original scholarly method
scholarly._get_page = _get_page
