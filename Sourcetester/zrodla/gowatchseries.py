# -*- coding: utf-8 -*-


"""
    FanFilm Project
"""

import json
import requests
import re
from urllib.parse import parse_qs, urljoin, urlencode, quote_plus

from ptw.libraries import cleantitle
from ptw.libraries import client
from ptw.libraries import source_utils, log_utils

# from ptw.libraries import cfScraper



class source:
    def __init__(self):
        self.priority = 1
        self.language = ["en"]
        self.domains = ["gowatchseries.co", "www5.gowatchseries.bz", "gowatchseries.online"]
        self.base_link = "https://www1.gowatchseries.online/"
        self.search_link = "/search.html?keyword=%s"
        self.session = requests.Session()
        #self.search_link = '/ajax-search.html?keyword=%s&id=-1'

    def movie(self, imdb, title, localtitle, aliases, year):
        try:
            url = {"imdb": imdb, "title": title, "year": year}
            url = urlencode(url)
            return url
        except:
            log_utils.log("gowatchseries0 - Exception", 'sources')
            return

    def tvshow(self, imdb, tvdb, tvshowtitle, localtvshowtitle, aliases, year):
        try:
            url = {"imdb": imdb, "tvdb": tvdb, "tvshowtitle": tvshowtitle, "year": year}
            url = urlencode(url)
            return url
        except:
            log_utils.log("gowatchseries1 - Exception", 'sources')
            return

    def episode(self, url, imdb, tvdb, title, premiered, season, episode):
        try:
            if url is None:
                return

            url = parse_qs(url)
            url = dict([(i, url[i][0]) if url[i] else (i, "") for i in url])
            url["title"], url["premiered"], url["season"], url["episode"] = (
                title,
                premiered,
                season,
                episode,
            )
            url = urlencode(url)
            return url
        except:
            log_utils.log("gowatchseries2 - Exception", 'sources')
            return

    def sources(self, url, hostDict, hostprDict):
        try:
            sources = []

            if url is None:
                return sources

            host_dict = hostprDict + hostDict

            data = parse_qs(url)
            data = dict([(i, data[i][0]) if data[i] else (i, "") for i in data])

            title = data["tvshowtitle"] if "tvshowtitle" in data else data["title"]
            if "season" in data:
                season = data["season"]
            if "episode" in data:
                episode = data["episode"]
            year = data["year"]

            r = self.session.get(self.base_link, timeout=10)
            # r = cfScraper.get(self.base_link).text
            headers = r.headers
            headers['X-Requested-With'] = 'XMLHttpRequest'
            result = r.text

            query = urljoin(
                self.base_link,
                self.search_link % quote_plus(cleantitle.getsearch(title)),
            )
            query2 = urljoin(
                self.base_link, self.search_link % quote_plus(title).lower()
            )

            r = self.session.get(query, timeout=10).text
#            if len(r) < 20:
#                 r = self.session.get(query2, headers=headers, timeout=10).text

#            listing = re.findall('class="listing items(.+?)</ul>', r)

            #r = json.loads(r)["content"]
            #r = zip(client.parseDOM(r, "a", ret="href"), client.parseDOM(r, "a"))
            r0 = client.parseDOM(r, 'div', attrs={'class': 'movies_index'})[0]
            r = [(client.parseDOM(r0, 'a', ret="href"), client.parseDOM(r0, 'div', attrs={'class': 'name'}))][0]

            if "tvshowtitle" in data:
                cltitle = cleantitle.get(title + "season" + season)
                cltitle2 = cleantitle.get(title + "season%02d" % int(season))
                t = [
                    i
                    for i in r
                    if cltitle == cleantitle.get(i[0])
                    or cltitle2 == cleantitle.get(i[0])
                ]
                vurl = "%s%s-episode-%s" % (
                    self.base_link,
                    str(r[0][0]).replace("/info", ""),
                    episode,
                )
                vurl2 = None

            else:
                cltitle = cleantitle.getsearch(title)
                cltitle2 = cleantitle.getsearch("%s (%s)" % (title, year))
                t = [
                    i
                    for i in r
                    if cltitle2 == cleantitle.getsearch(i[0])
                    or cltitle == cleantitle.getsearch(i[0])
                ]
                vurl = "%s%s-episode-0" % (
                    self.base_link,
                    str(r[0][0]).replace("/info", ""),
                )
                vurl2 = "%s%s-episode-1" % (
                    self.base_link,
                    str(r[0][0]).replace("/info", ""),
                )

            r = self.session.get(vurl, timeout=10).text
            headers["Referer"] = vurl

            slinks = client.parseDOM(r, "li", ret="data-video")
            if len(slinks) == 0 and vurl2 is not None:
                r = self.session.get(vurl2, headers=headers, timeout=10).text
                headers["Referer"] = vurl2
                slinks = client.parseDOM(r, "li", ret="data-video")
            slinks = [
                slink if slink.startswith("http") else "https:{0}".format(slink)
                for slink in slinks
            ]

            for url in slinks:
                url = client.replaceHTMLCodes(url)
                # log_utils.log('gowatchseries_url: ' + repr(url))
                valid, host = source_utils.is_host_valid(url, host_dict)
                if valid:
                    sources.append(
                        {
                            "source": host,
                            "quality": "720p",
                            "language": "en",
                            "url": url,
                            "direct": False,
                            "debridonly": False,
                        }
                    )

                elif ("vidembed" in url and "/goto." in url) or "/hls/" in url:
                    sources.append(
                        {
                            "source": host,
                            "quality": "720p",
                            "language": "en",
                            "url": url,
                            "direct": True,
                            "debridonly": False,
                        }
                    )

            return sources
        except Exception as e:
            print("gowatchseries - Exception %s " % e, 'sources')
            return sources

    def resolve(self, url):
        return url
