# -*- coding: utf-8 -*-
"""
    FanFilm Add-on
    Copyright (C) 2018 :)

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

import base64
import json
import urllib
import requests

from urllib.parse import parse_qs, quote_plus

from ptw.libraries import source_utils
from ptw.libraries import cleantitle
from ptw.libraries import client, log_utils
from ptw.debug import log_exception


class source:
    def __init__(self):
        self.priority = 1
        self.language = ["pl"]
        self.domains = ["filman.cc"]

        self.base_link = "https://filman.cc/"
        self.search_link = "wyszukiwarka?phrase="
        self.anime = False
        self.year = 0

    def movie(self, imdb, title, localtitle, aliases, year):
        return self.search(title, localtitle, year, True)

    def tvshow(self, imdb, tvdb, tvshowtitle, localtvshowtitle, aliases, year):
        return (tvshowtitle, localtvshowtitle), year

    def episode(self, url, imdb, tvdb, title, premiered, season, episode):
        anime = source_utils.is_anime("show", "tvdb", tvdb)
        self.year = int(url[1])
        self.anime = anime
        if anime:
            epNo = source_utils.absoluteNumber(tvdb, episode, season)
        else:
            epNo = "s" + season.zfill(2) + "e" + episode.zfill(2)
        return self.search_ep(url[0][0], url[0][1], self.year, epNo)

    def contains_word(self, str_to_check, word):
        if str(word).lower() in str(str_to_check).lower():
            return True
        return False

    def contains_all_words(self, str_to_check, words):
        for word in words:
            if not self.contains_word(str_to_check, word):
                return False
        return True

    def search(self, title, localtitle, year, is_movie_search):
        try:
            titles = []

            titles.append(localtitle.encode('utf8'))
            titles.append(title.encode('utf8'))

            for title in titles:
                url = urllib.urljoin(self.base_link, self.search_link)
                data = {
                    'phrase': title
                }
                title = cleantitle.normalize(cleantitle.getsearch(title.decode()))
                result = client.request(url, post=data)
                result = client.parseDOM(result, "div", attrs={"class": "col-xs-3 col-lg-2"})

                for item in result:
                    link = str(client.parseDOM(item, "a", ret="href")[0])
                    nazwa = str(client.parseDOM(item, "a", ret="title")[0])
                    name = cleantitle.normalize(cleantitle.getsearch(nazwa))
                    name = name.replace("  ", " ")
                    title = title.replace("  ", " ")
                    words = title.split(" ")
                    if self.contains_all_words(name, words) and str(year) in link:
                        return link
        except Exception as e:
            log_exception()
            return

    def search_ep(self, title, localtitle, year, epNo):
        try:
            titles = []

            titles.append(localtitle.encode('utf8'))
            titles.append(title.encode('utf8'))

            for title in titles:
                url = urllib.urljoin(self.base_link, self.search_link)
                data = {
                    'phrase': title
                }
                title = cleantitle.normalize(cleantitle.getsearch(title.decode()))
                result = client.request(url, post=data)
                result = client.parseDOM(result, "div", attrs={"class": "col-xs-3 col-lg-2"})

                for item in result:
                    try:
                        link = str(client.parseDOM(item, "a", ret="href")[0])
                        nazwa = str(client.parseDOM(item, "a", ret="title")[0])
                        name = cleantitle.normalize(cleantitle.getsearch(nazwa))
                        name = name.replace("  ", " ")
                        for title in titles:
                            title = cleantitle.normalize(cleantitle.getsearch(title.decode()))
                            title = title.replace("  ", " ")
                            words = title.split(" ")
                            if self.contains_all_words(name, words) and "serial" in link:
                                result2 = client.request(link)
                                found_year = str(client.parseDOM(result2, "div", attrs={"class": "info"}))
                                if str(year) in found_year:
                                    result2 = client.parseDOM(result2, "ul", attrs={"id": "episode-list"})
                                    li = client.parseDOM(result2, "li")
                                    for item2 in li:
                                        try:
                                            if epNo.lower() in item2.lower() and not item2.startswith("<span"):
                                                return client.parseDOM(item2, "a", ret="href")[0]
                                            else:
                                                continue
                                        except:
                                            continue
                                else:
                                    break
                    except:
                        continue
        except Exception as e:
            log_exception()
            return

    def sources(self, url, hostDict, hostprDict):
        try:
            sources = []
            if url == None:
                return sources
            data = parse_qs(url)
            data = dict([(i, data[i][0]) if data[i] else (i, "") for i in data])


            title = data["tvshowtitle"] if "tvshowtitle" in data else data["title"]

            if "season" in data:
                season = int(data["season"])
            if "episode" in data:
                episode = int(data["episode"])
            year = data["year"]

            url = self.base_link + self.search_link + quote_plus(title)
#            result = client.request(url)
            result = requests.get(url)
            result = [i for i in client.parseDOM(result.text, 'div', attrs={'class': 'container'}) if '<h3>Filmy' in i][0]
            links = [i for i in client.parseDOM(result, 'a', ret='href') if not 'https://filman.cc/dodaj-poszukiwany' in i]
            titles = client.parseDOM(result, 'a', ret='title')
            for t in titles:
                if cleantitle.get(t) == cleantitle.get(title):
                    index = titles.index(t)
                    link = links[index]
            result = requests.get(link)

            if 'tvshowtitle' in data:
                ep_pattern = f'[s{season:02}e{episode:02}]'

                ep_list = [client.parseDOM(i, 'a', ret='href') for i in
                           client.parseDOM(result.text, 'li')
                           if ep_pattern in i][0][1]
                result = requests.get(ep_list)


            links = client.parseDOM(result.text, 'a', ret='data-iframe')

            for i in links:
                out = json.loads(base64.b64decode(i))['src']
                print(out)
            if not result:
                return sources

            #if 'tvshowtitle' in data:











            tabela = client.parseDOM(
                result, "table", attrs={"class": "table table-bordered"}
            )[0]
            tabela = client.parseDOM(tabela, "tr")
            for item in tabela:
                try:
                    if "fa fa-sort" in item:
                        continue
                    lang, info = self.get_lang_by_type(str(item))
                    url = str(client.parseDOM(item, "a", ret="data-iframe")[0])
                    url = json.loads(base64.b64decode(url))["src"]
                    valid, host = source_utils.is_host_valid(url, hostDict)
                    if not valid:
                        continue
                    if "Wysoka" in item or "720" in item or "1080" in item:
                        sources.append(
                            {
                                "source": host,
                                "quality": "HD",
                                "language": lang,
                                "url": url,
                                "info": info,
                                "direct": False,
                                "debridonly": False,
                            }
                        )
                    elif "rednia" in item:
                        sources.append(
                            {
                                "source": host,
                                "quality": "SD",
                                "language": lang,
                                "url": url,
                                "info": info,
                                "direct": False,
                                "debridonly": False,
                            }
                        )
                    elif "Niska" in item:
                        sources.append(
                            {
                                "source": host,
                                "quality": "SD",
                                "language": lang,
                                "url": url,
                                "info": info,
                                "direct": False,
                                "debridonly": False,
                            }
                        )
                    else:
                        sources.append(
                            {
                                "source": host,
                                "quality": "SD",
                                "language": lang,
                                "url": url,
                                "info": info,
                                "direct": False,
                                "debridonly": False,
                            }
                        )
                except:
                    continue
            return sources
        except Exception as e:
            log_utils.log('gowatchseries1 - Exception', 'sources')
            print(e)
            return sources

    def get_lang_by_type(self, lang_type):
        if "dubbing" in lang_type.lower():
            if "kino" in lang_type.lower():
                return "pl", "Dubbing Kino"
            return "pl", "Dubbing"
        elif "napisy pl" in lang_type.lower():
            return "pl", "Napisy"
        elif "napisy" in lang_type.lower():
            return "pl", "Napisy"
        elif "lektor pl" in lang_type.lower():
            return "pl", "Lektor"
        elif "lektor" in lang_type.lower():
            return "pl", "Lektor"
        elif "POLSKI" in lang_type.lower():
            return "pl", None
        elif "pl" in lang_type.lower():
            return "pl", None
        return "en", None

    def resolve(self, url):
        link = str(url).replace("//", "/").replace(":/", "://").split("?")[0]
        return str(link)
