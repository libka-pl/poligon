# -*- coding: utf-8 -*-
"""
    FanFilm Add-on
    Copyright (C) 2022 :)

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
import threading

import requests
import xbmcgui
try:
    import urllib.parse as urllib
except:
    pass

from ptw.libraries import source_utils
from ptw.libraries import cleantitle
from ptw.libraries import client, control, cache
from ptw.debug import log_exception

import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


class source:
    def __init__(self):
        self.lock = threading.Lock()
        self.priority = 1
        self.language = ["pl"]
        self.domains = ["tb7.pl"]
        self.results = []
        self.base_link = "https://tb7.pl/"
        self.wrzucaj_link = 'https://wrzucajpliki.pl/?op=catalogue&k={}&search=+Search+&ftype=vid&fsize_logic=gt&fsize='
        self.search_link = "https://tb7.pl/mojekonto/szukaj"  # post
        self.support_search_link = "https://tb7.pl/mojekonto/szukaj/{}"
        self.session = requests.Session()
        self.user_name = control.setting("tb7.username") or 'lukkaszga'
        self.user_pass = control.setting("tb7.password") or 'misio9731'
        self.exts = ['avi', 'mkv', 'mp4']
        self.headers = {
            "Connection": "keep-alive",
            "Upgrade-Insecure-Requests": "1",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/72.0.3626.53 Safari/537.36",
            "DNT": "1",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8",
            "Accept-Language": "pl-PL,pl;q=0.9,en-US;q=0.8,en;q=0.7",
        }

    def contains_word(self, str_to_check, word):
        if str(word).lower() in str(str_to_check).lower():
            return True
        return False

    def contains_all_words(self, str_to_check, words):
        for word in words:
            if not self.contains_word(str_to_check, word):
                return False
        return True

    def login(self):
        try:
            cookies = cache.cache_get("tb7_cookie")["value"]
        except:
            cookies = ""
        self.headers.update({"Cookie": cookies})
        result = self.session.get(self.base_link, headers=self.headers).text
        if self.user_name in result:
            return
        else:
            url = "https://tb7.pl/login"

            if self.user_name and self.user_pass:
                self.session.post(
                    url,
                    verify=False,
                    allow_redirects=False,
                    data={"login": self.user_name, "password": self.user_pass},
                )
                result = self.session.get(self.base_link).text
                if self.user_name in result:
                    cookies = self.session.cookies
                    cookies = "; ".join(
                        [str(x) + "=" + str(y) for x, y in cookies.items()]
                    )
                    cache.cache_insert("tb7_cookie", cookies)
                    self.headers.update({"Cookie": cookies})

    def get_pages_content(self, page, year):

        res = self.session.get(self.support_search_link.format(str(page)), headers=self.headers).text
        rows = client.parseDOM(res, "tr")[1:]
        #with self.lock:
        for row in rows:
            if year in row:
                self.results.append(row)
            else:
                continue


    def search(self, title, localtitle, year=""):
        try:
            titles = []
            titles.append(cleantitle.normalize(cleantitle.getsearch(title)))
            titles.append(cleantitle.normalize(cleantitle.getsearch(localtitle)))
            self.login()

            results = []

            for title in titles:
                #Old ver
                #data = {"type": "1", "search": title + " " + year + " (avi|mkv|mp4)"}
                ###Przeszukanie wrzucajpliki


                post = {'search': title + ' '+ year, 'type': '1'}

                pre_res = self.session.post(
                    self.search_link, headers=self.headers, data=post
                ).text.replace("\r", "").replace("\n", "")
                page_block = re.search('class="page-list"(.+?)</div>', pre_res, re.IGNORECASE)

                if page_block is not None:
                    pages = len(re.findall('href=', page_block.group()))
                    for page in range(pages):
                        #self.get_pages_content(page + 1, year)
                        t = threading.Thread(target=self.get_pages_content, args=(page+1, year))
                        t.start()
                    results = self.results
                else:
                    if self.results:
                        return self.results
                    else:

                        return None

#                self.session.post("https://tb7.pl/mojekonto/szukaj", data=data, headers=self.headers)

#                data = {"sort": "size"}

#                self.session.post(
#                    "https://tb7.pl/mojekonto/szukaj/1", headers=self.headers, data=data
#                )
#                r = self.session.post(
#                    "https://tb7.pl/mojekonto/szukaj/1", headers=self.headers, data=data
#                ).text

#                rows = client.parseDOM(r, "tr")

#                if rows:
#                    results += rows
            return results
        except Exception as e:
            log_exception()
            return

    def movie(self, imdb, title, localtitle, aliases, year):
        return self.search(title, localtitle, year)

    def tvshow(self, imdb, tvdb, tvshowtitle, localtvshowtitle, aliases, year):
        return (tvshowtitle, localtvshowtitle), year

    def episode(self, url, imdb, tvdb, title, premiered, season, episode):
        anime = source_utils.is_anime("show", "tvdb", tvdb)
        self.year = int(url[1])
        self.anime = anime
        if anime:
            epNo = " " + source_utils.absoluteNumber(tvdb, episode, season)
        else:
            epNo = " s" + season.zfill(2) + "e" + episode.zfill(2)
        return self.search(url[0][0] + epNo, url[0][1] + epNo)

    def sources(self, rows, hostDict, hostprDict):
        sources = []
        self.login()

        mojekonto = "https://tb7.pl/mojekonto/pliki"
        result = self.session.get(mojekonto, headers=self.headers).text
        result = client.parseDOM(result, "table", attrs={"class": "list"})
        result = client.parseDOM(result, "input", ret="value")

        try:
            for row in rows:
                try:
                    source = "tb7"
                    nazwa = client.parseDOM(row, "label")[0]
                    if not nazwa[-3:] in self.exts:
                        continue
                    link = client.parseDOM(row, "input", ret="value")[0]
                    size = client.parseDOM(row, "td")[3]
                    if any(size in s["info"] for s in sources):
                        continue
                    quality = source_utils.check_sd_url(nazwa)
                    info = self.get_lang_by_type(nazwa)
                    if not info[1]:
                        info2 = ""
                    else:
                        info2 = info[1]

                    for item in result:
                        item_org = item
                        item = urllib.unquote(item.split("/")[-1])
                        item = [character for character in item if character.isalnum()]
                        item = "".join(item)
                        url = urllib.unquote(link)
                        url = [character for character in url if character.isalnum()]
                        url = "".join(url)
                        if item in url:
                            link = item_org
                            source = "tb7 Biblioteka"


                    sources.append(
                        {
                            "source": source,
                            "quality": quality,
                            "language": info[0],
                            "url": link,
                            "info": size + " " + info2,
                            "direct": True,
                            "debridonly": False,
                        }
                    )
                except:
                    continue
            return sources
        except:
            log_exception()
            return sources

    def get_lang_by_type(self, lang_type):
        if "dubbing" in lang_type.lower():
            if "kino" in lang_type.lower():
                return "pl", "Dubbing Kino"
            return "pl", "Dubbing"
        elif "lektor pl" in lang_type.lower():
            return "pl", "Lektor"
        elif ".dual" in lang_type.lower():
            return "pl", ""
        elif ".pldub" in lang_type.lower():
            return "pl", "Dubbing"
        elif ".pl." in lang_type.lower():
            return "pl", ""
        elif ".sub" in lang_type.lower():
            return "pl", "Napisy"
        elif "lektor" in lang_type.lower():
            return "pl", "Lektor"
        elif "napisy pl" in lang_type.lower():
            return "pl", "Napisy"
        elif "napisy" in lang_type.lower():
            return "pl", "Napisy"
        elif "POLSKI" in lang_type.lower():
            return "pl", None
        elif "pl" in lang_type.lower():
            return "pl", None
        return "en", None

    def resolve(self, url):
        org_url = url
        self.login()

        mojekonto = "https://tb7.pl/mojekonto/pliki"
        result = self.session.get(mojekonto, headers=self.headers).text
        result = client.parseDOM(result, "table", attrs={"class": "list"})
        result = client.parseDOM(result, "input", ret="value")
        for item in result:
            link = item
            item = urllib.unquote(item.split("/")[-1])
            item = [character for character in item if character.isalnum()]
            item = "".join(item)
            url = urllib.unquote(url)
            url = [character for character in url if character.isalnum()]
            url = "".join(url)
            if item in url:
                return str(
                    link + "|User-Agent=vlc/3.0.0-git libvlc/3.0.0-git&verifypeer=false"
                )

        autotb7 = control.setting("autotb7")
        if autotb7 == "false":
            limit = self.session.get(self.base_link, headers=self.headers).text
            limit = client.parseDOM(limit, "div", attrs={"class": "textPremium"})
            limit = str(client.parseDOM(limit, "b")[-1])

            ret = xbmcgui.Dialog().yesno(
                "TB7",
                "Chcesz wykorzystać transfer ze swojego konta tb7 aby odtworzyć tę pozycję?\n Aktualnie posiadasz: [B]%s[/B] transferu"
                % limit,
            )
            if not ret:
                return

        data = {"step": "1", "content": org_url}

        self.session.post(
            "https://tb7.pl/mojekonto/sciagaj", data=data, headers=self.headers
        )

        data = {"0": "on", "step": "2"}

        content = self.session.post(
            "https://tb7.pl/mojekonto/sciagaj", data=data, headers=self.headers
        ).text

        result = client.parseDOM(content, "div", attrs={"class": "download"})
        link = client.parseDOM(result, "a", ret="href")[1]

        return str(link + "|User-Agent=vlc/3.0.0-git libvlc/3.0.0-git&verifypeer=false")