# -*- coding: utf-8 -*-

"""
    FanFilm Project
"""

import base64
import re

# from ptw.libraries import cfScraper
from urllib.parse import parse_qs, urljoin, urlencode

from ptw.libraries import client
from ptw.libraries import log_utils
from ptw.libraries import source_utils
from six import ensure_text




class source:
    def __init__(self):
        self.priority = 1
        self.language = ["en"]
        self.domains = ["fsapi.xyz"]
        self.base_link = "https://fsapi.xyz"
        self.search_link = "/movie/%s"
        self.search_link2 = "/tv-imdb/%s-%s-%s"

    def movie(self, imdb, title, localtitle, aliases, year):
        try:
            url = {"imdb": imdb, "title": title, "year": year}
            url = urlencode(url)
            return url
        except:
            return

    def tvshow(self, imdb, tvdb, tvshowtitle, localtvshowtitle, aliases, year):
        try:
            url = {"imdb": imdb, "tvdb": tvdb, "tvshowtitle": tvshowtitle, "year": year}
            url = urlencode(url)
            return url
        except:
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
            return

    def sources(self, url, hostDict, hostprDict):
        sources = []
        try:
            if url is None:
                return sources

            hostDict = hostprDict + hostDict

            data = parse_qs(url)
            data = dict([(i, data[i][0]) if data[i] else (i, "") for i in data])

            if not data["imdb"] or data["imdb"] == "0":
                return sources

            if "tvshowtitle" in data:
                query = self.search_link2 % (
                    data["imdb"],
                    data["season"],
                    data["episode"],
                )
            else:
                query = self.search_link % data["imdb"]

            url = urljoin(self.base_link, query)
            posts = client.r_request(url)
            #posts = posts.replace("\r", "").replace("\n", "")
            r = re.findall('<a href="(.+?)" target="iframe', posts)
            urls = [u.split("url=")[1] for u in r]
            urls = [base64.b64decode(url).decode('utf-8') for url in urls]
            urls = ["https:" + url if url.startswith("//") else url for url in urls]
            urls = list(set(urls))
            # log_utils.log('fsapi_all_urls: ' + repr(urls))

            for url in urls:

                try:

                    valid, host = source_utils.is_host_valid(url, hostDict)
                    if valid:
                        sources.append(
                            {
                                "source": host,
                                "quality": '720p',
                                "language": "en",
                                "url": url,
                                "direct": False,
                                "debridonly": False,
                            }
                        )

                    elif "/hls/" in url:
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


                except:
                    pass


            return sources
        except:
            log_utils.log("FSAPI Exception", 'sources')
            return sources

    def resolve(self, url):
        # log_utils.log('FSAPI url: ' + repr(url))
        return url
