# -*- coding: utf-8 -*-

"""
    FanFilm Project
"""

import re
from urllib.parse import parse_qs, urljoin, urlencode

from ptw.libraries import cleantitle
from ptw.libraries import client
from ptw.libraries import source_utils, log_utils
from six import ensure_text




class source:
    def __init__(self):
        self.priority = 1
        self.language = ["en"]
        self.domains = ["filmxy.me", "filmxy.one", "filmxy.tv"]
        self.base_link = "https://www.filmxy.pw"
        self.search_link = "/search/%s/feed/rss2/"
        self.post = "https://cdn.filmxy.one/asset/json/posts.json"

    def movie(self, imdb, title, localtitle, aliases, year):
        try:
            url = {"imdb": imdb, "title": title, "year": year}
            url = urlencode(url)
            return url
        except:
            log_utils.log("filmxy", 'sources')
            return

    def sources(self, url, hostDict, hostprDict):
        sources = []
        try:
            if url is None:
                return
            data = parse_qs(url)
            data = dict((i, data[i][0]) for i in data)
            title = data["title"]
            year = data["year"]

            tit = cleantitle.geturl(title + " " + year)
            query = urljoin(self.base_link, tit)

            r = client.request(query, referer=self.base_link, redirect=True)
            if not data["imdb"] in r:
                return sources

            links = []

            try:
                down = client.parseDOM(r, "div", attrs={"id": "tab-download"})[0]
                down = client.parseDOM(down, "a", ret="href")[0]
                data = client.request(down)
                frames = client.parseDOM(data, "div", attrs={"class": "single-link"})
                frames = [client.parseDOM(i, "a", ret="href")[0] for i in frames if i]
                for i in frames:
                    links.append(i)

            except Exception:
                pass
            try:
                streams = client.parseDOM(r, "div", attrs={"id": "tab-stream"})[0]
                streams = re.findall(
                    r"""iframe src=(.+?) frameborder""",
                    streams.replace("&quot;", ""),
                    re.I | re.DOTALL,
                )
                for i in streams:
                    links.append(i)
            except Exception:
                pass

            for url in links:
                try:
                    valid, host = source_utils.is_host_valid(url, hostDict)
                    if not valid:
                        valid, host = source_utils.is_host_valid(url, hostprDict)
                        if not valid:
                            continue
                        else:
                            rd = True
                    else:
                        rd = False
                    # quality, _ = source_utils.get_release_quality(url, url)
                    quality = "720p"
                    host = client.replaceHTMLCodes(host)
                    host = ensure_text(host)
                    if rd:
                        sources.append(
                            {
                                "source": host,
                                "quality": quality,
                                "language": "en",
                                "url": url,
                                "direct": False,
                                "debridonly": True,
                            }
                        )
                    else:
                        sources.append(
                            {
                                "source": host,
                                "quality": quality,
                                "language": "en",
                                "url": url,
                                "direct": False,
                                "debridonly": False,
                            }
                        )
                except Exception:
                    pass
            return sources
        except:
            log_utils.log("filmxy", 'sources')
            return sources

    def resolve(self, url):
        return url
