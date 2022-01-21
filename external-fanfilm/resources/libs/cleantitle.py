# -*- coding: utf-8 -*-

"""
    Fanfilm Add-on

    This program is free software: you can redistribute it and/or modify
    it under the terms of the GNU General Public License as published by
    the Free Software Foundation, either version 3 of the License, or
    (at your option) any later version.

    This program is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU General Public License for more details.

    You should have received a copy of the GNU General Public License
    along with this program.  If not, see <http://www.gnu.org/licenses/>.
"""

import re

import unicodedata
#from ptw.libraries.utils import convert


def get(title):
    if title is None: return
    
    title = re.sub(r'&#(\d+);', '', title)
    title = re.sub(r'(&#[0-9]+)([^;^0-9]+)', '\\1;\\2', title)
    title = title.replace(r'&quot;', '\"').replace(r'&amp;', '&').replace(r'–', '-').replace(r'!', '')
    title = re.sub(r'\n|([\[].+?[\]])|([\(].+?[\)])|\s(vs|v[.])\s|(:|;|-|–|"|,|\'|\_|\.|\?)|\s', '', title).lower()
    return title

def get_title(title):
    if title is None: return
    from urllib.parse import unquote
    
    title = unquote(title)
    title = re.sub('[^A-Za-z0-9 ]+', ' ', title)
    title = re.sub(' {2,}', ' ', title)
    title = title.strip().lower()
    return title
    
def geturl(title):
    if title is None:
        return
    title = title.lower()
    title = title.translate(None, ":*?\"'\.<>|&!,")
    title = title.replace("/", "-")
    title = title.replace(" ", "-")
    title = title.replace("--", "-")
    return title


def get_simple(title):
    if title is None:
        return
    title = title.lower()
    title = re.sub("(\d{4})", "", title)
    title = re.sub("&#(\d+);", "", title)
    title = re.sub("(&#[0-9]+)([^;^0-9]+)", "\\1;\\2", title)
    title = title.replace("&quot;", '"').replace("&amp;", "&")
    title = re.sub(
        "\n|\(|\)|\[|\]|\{|\}|\s(vs|v[.])\s|(:|;|-|–|\"|,|'|\_|\.|\?)|\s", "", title
    ).lower()
    return title


def getsearch(title):
    if title is None:
        return
    title = title.lower()
    title = re.sub("&#(\d+);", "", title)
    title = re.sub("(&#[0-9]+)([^;^0-9]+)", "\\1;\\2", title)
    title = title.replace("&quot;", '"').replace("&amp;", "&")
    title = re.sub("\\\|/|!|\[|\]|–|:|;|\*|\?|\"|'|<|>|\|", "", title).lower()
    title = title.replace(".", " ").replace("  ", " ")
    return title


def query(title):
    if title is None:
        return
    title = (
        title.replace("'", "").rsplit(":", 1)[0].rsplit(" -", 1)[0].replace("-", " ")
    )
    return title


def normalize(title):
    try:
        return str(
            "".join(
                c
                for c in unicodedata.normalize("NFKD", convert(title))
                if unicodedata.category(c) != "Mn"
            )
        ).replace("ł", "l")
    except:
        title = (
            convert(title)
            .replace("ą", "a")
            .replace("ę", "e")
            .replace("ć", "c")
            .replace("ź", "z")
            .replace("ż", "z")
            .replace("ó", "o")
            .replace("ł", "l")
            .replace("ń", "n")
            .replace("ś", "s")
        )
        return title


def clean_search_query(url):
    url = url.replace("-", "+")
    url = url.replace(" ", "+")
    return url



def scene_title(title, year):
    title = normalize(title)
    try:
        title = title
    except:
        pass
    title = title.replace('&', 'and').replace('-', ' ').replace('–', ' ').replace('/', ' ').replace('*', ' ').replace('.', ' ')
    title = re.sub('[^A-Za-z0-9 ]+', '', title)
    title = re.sub(' {2,}', ' ', title).strip()
    if title.startswith('Birdman or') and year == '2014': title = 'Birdman'
    if title == 'Birds of Prey and the Fantabulous Emancipation of One Harley Quinn' and year == '2020': title = 'Birds of Prey'
    if title == "Roald Dahls The Witches" and year == '2020': title = 'The Witches'
    return title, year
    
def scene_tvtitle(title, year, season, episode):
    title = normalize(title)
    try:
        title = title
    except:
        pass
    title = title.replace('&', 'and').replace('-', ' ').replace('–', ' ').replace('/', ' ').replace('*', ' ').replace('.', ' ')
    title = re.sub('[^A-Za-z0-9 ]+', '', title)
    title = re.sub(' {2,}', ' ', title).strip()
    if title in ['The Haunting', 'The Haunting of Bly Manor', 'The Haunting of Hill House'] and year == '2018':
        if season == '1': title = 'The Haunting of Hill House'
        elif season == '2': title = 'The Haunting of Bly Manor'; year = '2020'; season = '1'
    if title in ['Cosmos', 'Cosmos A Spacetime Odyssey', 'Cosmos Possible Worlds'] and year == '2014':
        if season == '1': title = 'Cosmos A Spacetime Odyssey'
        elif season == '2': title = 'Cosmos Possible Worlds'; year = '2020'; season = '1'
    if 'Special Victims Unit' in title: title = title.replace('Special Victims Unit', 'SVU')
    if title == 'Cobra Kai' and year == '1984': year = '2018'
    #if title == 'The Office' and year == '2001': title = 'The Office UK'
    if title == 'The End of the F ing World': title = 'The End of the Fucking World'
    if title == 'M A S H': title = 'MASH'
    if title == 'Lupin' and year == '2021':
        if season == '1' and int(episode) > 5: season = '2'; episode = str(int(episode) - 5)
    return title, year, season, episode
