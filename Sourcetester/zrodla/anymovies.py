# -*- coding: utf-8 -*-
# Created by Tempest
"""
    FanFilm Project
"""



import re
from urllib.parse import parse_qs, urljoin, urlencode, quote_plus
from ptw.libraries import source_utils
from ptw.libraries import client, cleantitle
from ptw.libraries import log_utils



class source:
    def __init__(self):
        self.priority = 1
        self.language = ['en']
        self.domain = ['downloads-anymovies.com']
        self.base_link = 'https://www.downloads-anymovies.co'
        self.search_link = '/search.php?zoom_query=%s'
        self.headers = {'User-Agent': client.agent()}
        self.aliases = []

    def movie(self, imdb, title, localtitle, aliases, year):
        try:
            self.aliases.extend(aliases)
            url = {'imdb': imdb, 'title': title, 'year': year}
            url = urlencode(url)
            return url
        except:
            return

    def sources(self, url, hostDict, hostprDict):
        sources = []
        try:
            if url is None:
                return sources

            data = parse_qs(url)
            data = dict([(i, data[i][0]) if data[i] else (i, '') for i in data])
            title = data['title']
            year = data['year']

            query = ' '.join((title, year))
            query = re.sub('(\\\|/| -|:|;|\*|\?|"|\'|<|>|\|)', ' ', query)

            url = self.search_link % quote_plus(query)
            url = urljoin(self.base_link, url).replace('++', '+')

            post = client.request(url, headers=self.headers)
            items = re.compile('class="result_title"><a href="(.+?)">(.+?)</a></div>').findall(post)
            for url, data in items:
                data = data[6:] if data.lower().startswith('watch ') else data
                if not self.is_match(data, title, year, self.aliases):
                    continue
                r = client.request(url, headers=self.headers)
                try:
                    links = re.findall('<span class="text"><a href="(.+?)" target="_blank">', r)
                    for link in links:
                        valid, host = source_utils.is_host_valid(link, hostDict)
                        if valid:
                            sources.append({'source': host, 'quality': 'HD', 'language': 'en', 'url': link, 'direct': False, 'debridonly': False})
                except:
                    return

            return sources
        except Exception as e:
            print(e)
            log_utils.log('ANYMOVIES - Exception', 'sources')
            return sources
    def is_match(self, name, title, hdlr=None, aliases=None):
        try:
            name = name.lower()
            t = re.sub(r'(\+|\.|\(|\[|\s)(\d{4}|s\d+e\d+|s\d+|3d)(\.|\)|\]|\s|)(.+|)', '', name)
            t = cleantitle.get(t)
            titles = [cleantitle.get(title)]

            if aliases:
                if not isinstance(aliases, list):
                    from ast import literal_eval
                    aliases = literal_eval(aliases)
                try: titles.extend([cleantitle.get(i['title']) for i in aliases])
                except: pass

            if hdlr:
                return (t in titles and hdlr.lower() in name)
            return t in titles
        except:
            log_utils.log('is_match exc', 'sources')
            return True


    def resolve(self, url):
        return url
