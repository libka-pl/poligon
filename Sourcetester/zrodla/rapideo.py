# -*- coding: utf-8 -*-
'''
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
'''

import requests
import xbmcgui
import math
import re

from ptw.libraries import source_utils
from ptw.libraries import cleantitle
from ptw.libraries import client, control, cache, log_utils


class source:
    def __init__(self):
        self.priority = 1
        self.language = ['pl']
        self.domains = ['rapideo.pl']
        self.login_url = 'https://www.rapideo.pl/api/rest/login'
        self.search_url = 'https://www.rapideo.pl/api/rest/search'
        self.check_url = "https://www.rapideo.pl/api/rest/files/check"
        self.files_url = "https://www.rapideo.pl/api/rest/files/get"
        self.download_url = "https://www.rapideo.pl/api/rest/files/download"
        self.r = requests
        self.exts = ['avi', 'mkv', 'mp4']
        self.user_name = control.setting('rapideo.username') or 'fanfilm'
        self.user_pass = control.setting('rapideo.password') or 'fanfilm777'

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

        self.authtoken = ''
        get_auth = cache.cache_get('rapideo_authtoken')
        if get_auth is not None:
            self.authtoken = get_auth['value']

        if self.authtoken == '':
            if self.user_name and self.user_pass:
                req = self.r.post(self.login_url, data={'login': self.user_name, 'password': self.user_pass})
                response = req.json()
                if "authtoken" in response:
                    self.authtoken = response['authtoken']
                    cache.cache_insert('rapideo_authtoken', self.authtoken)
                    return True
                elif "error" in response and response['message'] != '':
                    xbmcgui.Dialog().notification("Błąd", str(response['message']))
                    return False

    def search(self, title, localtitle, year=''):
        cache.cache_clear_providers()
        try:

            titles = [cleantitle.normalize(cleantitle.getsearch(localtitle)),
                      cleantitle.normalize(cleantitle.getsearch(title))]

            self.login()
            ##### test
            test = []
            results = []
            for title in titles:
                data = {'authtoken': self.authtoken, 'keyword': title + ' ' + year, 'video': True, 'mode': 'ff'}
                res = self.r.post(self.search_url, data=data)
                search = res.json()

                if "error" in search and search['message'] != '':
                    cache.cache_insert('rapideo_authtoken', '')
                    return False

                if "search" in search:
                    search = search['search']
                    if "search_result" in search and len(search["search_result"]) > 0:
                        if not year:  # tv show
                            for s in search["search_result"]:
                                div = title.split(' ')[-1]
                                master_title = cleantitle.get_title(s['filename']).rpartition(div)[0]
                                if title.strip(div) in master_title:
                                    results.append(s)
                                test.append(s)
                        else:
                            for s in search["search_result"]:
                                #master_title = cleantitle.getsearch(s['filename']).rpartition(year)[0]
                                #if title in master_title:
                                    #results.append(s)
                                results.append(s)
            return results

        except Exception as e:
            log_utils.log("rapideo - Exception " + str(e), 'sources')
            return

    def movie(self, imdb, title, localtitle, aliases, year):
        return self.search(title, localtitle, year)

    def tvshow(self, imdb, tvdb, tvshowtitle, localtvshowtitle, aliases, year):
        return (tvshowtitle, localtvshowtitle), year

    def episode(self, url, imdb, tvdb, title, premiered, season, episode):
        anime = source_utils.is_anime('show', 'tvdb', tvdb)
        self.year = int(url[1])
        self.anime = anime
        if anime:
            epNo = " " + source_utils.absoluteNumber(tvdb, episode, season)
        else:
            epNo = ' s' + season.zfill(2) + 'e' + episode.zfill(2)

        return self.search(url[0][0] + epNo, url[0][1] + epNo)

    def sources(self, rows, hostDict, hostprDict):
        sources = []
        try:
            for row in rows:
                try:
                    filename = row["filename_long"]
                    on_account = row['on_account']
                    source = row['hosting']
                    if not filename[-3:] in self.exts:
                        continue
                    link = row["url"]
                    size = row["filesize"]
                    if any(size in s['info'] for s in sources):
                        continue
                    quality = source_utils.check_sd_url(filename)
                    info = row['translation']
                    if on_account == True:
                        sources.append({'source': source + ' Biblioteka',
                                        'quality': quality,
                                        'language': info['language'],
                                        'url': link,
                                        'info': size + ' ' + info['description'],
                                        'direct': True, 'debridonly': False})
                    else:
                        sources.append({'source': source,
                                        'quality': quality, 'language': info['language'],
                                        'url': link,
                                        'info': size + ' ' + info['description'],
                                        'direct': True,
                                        'debridonly': False})
                except:
                    continue
            return sources
        except:
            log_utils.log("rapideo - Exception ", 'sources')
            return sources

    def recalculate(self, bytes):
        if bytes == 0:
            return "0 B"

        system = ("B", "KB", "MB", "GB", "TB", "PB", "EB", "ZB", "YB")
        i = int(math.floor(math.log(bytes, 1024)))
        p = math.pow(1024, i)
        s = round(bytes / p, 2)
        return "{0} {1}".format(s, system[i])

    def resolve(self, url):
        try:
            self.login()
            data = {'authtoken': self.authtoken, 'url': url, 'mode': 'ff'}
            req = self.r.post(self.files_url, data=data)
            get_files = req.json()

            if "files" in get_files:
                for file in get_files["files"]:
                    if "url" in file and file["url"] == url and "download_url" in file and file['download_url'] != '':
                        return str(file['download_url'])

            autorapideo = control.setting('autorapideo')

            data = {'authtoken': self.authtoken, 'url': url}
            req = self.r.post(self.check_url, data=data)
            check_file = req.json()
            if "file" in check_file:
                if "filesize" in check_file['file'] and "filename" in check_file['file']:
                    if autorapideo == 'false':
                        confirm = xbmcgui.Dialog().yesno("Pobieranie pliku", "Pobieranie pliku " + check_file['file'][
                            'filename_full'] + "\n\nOd transferu zostanie odliczone " + self.recalculate(
                            check_file['file']['chargeuser']), yeslabel="Pobierz", nolabel="Anuluj")
                        if not confirm:
                            raise Exception('Informacja', 'Anulowano pobieranie pliku')
                elif "error" in check_file['file'] and "message" in check_file['file']:
                    raise Exception('Błąd', check_file['file']['message'])
            elif "error" in check_file and check_file['message'] != '':
                cache.cache_insert('rapideo_authtoken', '')
                raise Exception('Błąd', check_file['message'])

            data = {'authtoken': self.authtoken, 'hash': check_file['file']['hash'], 'mode': 'ff'}
            add_file = self.r.post(self.download_url, data=data)
            response = add_file.json()
            if "file" in response:
                file = response["file"]
                if "url" in file:
                    return str(file["url"])
                elif "error" in file and "message" in file:
                    raise Exception('Błąd', file['message'])
            elif "error" in check_file and check_file['message'] != '':
                cache.cache_insert('rapideo_authtoken', '')
                raise Exception('Błąd', check_file['message'])

        except Exception as e:
            error, message = e.args
            xbmcgui.Dialog().notification(error, message)
            return 'https://www.rapideo.pl/error.mp4'
