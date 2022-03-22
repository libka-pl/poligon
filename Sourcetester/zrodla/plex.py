# -*- coding: utf-8 -*-

'''
    FanFilm Add-on  2021
    Źródło Plex
    Wymagany plugin composite z repozytorium Kodi
'''

import re, os
import pickle
import json
import requests
import xbmcvfs, xbmcaddon, xbmc
from urllib.parse import urlencode, parse_qs, urlsplit, urlunparse
import xml.etree.ElementTree as ET

from ptw.libraries import cleantitle, client, control, source_utils
from ptw.fake import xbmc as plexserver

composite_plugin = 'plugin.video.composite_for_plex'
composite_enabled = control.condVisibility('System.HasAddon(%s)' % composite_plugin)
COMPOSITE_ADDON = xbmcaddon.Addon(id=composite_plugin)
COMPOSITE_PATH = f'special://profile/addon_data/{composite_plugin}/cache/servers/'
CACHE_NAME = 'plexhome_user.pcache'
COMPOSITE_SERVERS = 'discovered_plex_servers.cache'
def get_composite_cache(cache=''):
    cache_path = xbmc.translatePath(COMPOSITE_PATH) or 'd:\drop\\'
    #            cache = xbmcvfs.File(cache_path + CACHE_NAME)
    cache = open(cache_path + cache, 'rb')

    try:
        # cache_data = cache.readBytes()
        cache_data = cache.read()
    except Exception as error:
        print(f'CACHE [{cache}]: read error [{error}]')
        cache_data = False
    finally:
        cache.close()
    if cache_data:
        if isinstance(cache_data, str):
            cache_data = cache_data.encode('utf-8')
        print(f'CACHE [{cache}]: read')
        try:
            cache_object = pickle.loads(cache_data)
        except (ValueError, TypeError):
             return False, None
        return True, cache_object

class source:
    def __init__(self):
        self.priority = 1
        self.language = ['pl']
        self.domains = ['plex.tv']
        self.base_link = 'https://plex.tv'
        self.server_url = '{scheme}://{IP}:{port}{path}'
        self.search_link = '{scheme}://{IP}:{port}/{path}?query={query}'
        self.composite_pattern = 'plugin://plugin.video.composite_for_plex/?url={uri}{key}&mode=5'
        self.session = requests.session()

        if composite_enabled:
            UUID = COMPOSITE_ADDON.getSetting('client_id') or '21e50ec5-c634-481a-bcdf-84b38bb323c3'
            self.cache_status, self.cache_token = get_composite_cache(CACHE_NAME)
            self.token = self.cache_token['myplex_user_cache'].split('|')[1]
            self.headers = {
                'X-Plex-Client-Identifier': UUID,
                'X-Plex-Product': COMPOSITE_ADDON.getAddonInfo('name') or 'plugin.video.composite_for_plex',
                'X-Plex-Token': self.token
            }

            plex_API = 'https://plex.tv//api/resources?includeHttps=1'
            r = self.session.get(plex_API, headers=self.headers)
            servers = []
            server_list = ET.fromstring(r.text)
            devices = server_list.iter('Device')
            for device in devices:
                server = {}
                server['name'] = device.get('name')
                server['accessToken'] = device.get('accessToken')
                server['protocol'] = device.find('./Connection').get('protocol')
                server['address'] = device.find('./Connection').get('address')
                server['port'] = device.find('./Connection').get('port')
                server['uri'] = device.find('./Connection').get('uri')
                server['local'] = device.find('./Connection').get('local')
                servers.append(server)
            self.server_list = servers
            print('plex enabled')
        else: self.cache_status = False


    def movie(self, imdb, title, localtitle, aliases, year):

        try:
            if not composite_enabled:
                return
            if not self.cache_status:
                return
            url = {'imdb': imdb,
                   'title': title,
                   'localtitle': localtitle,
                   'year': year}
            url = urlencode(url)
            return url
        except:
            return

    def tvshow(self, imdb, tvdb, tvshowtitle, localtvshowtitle, aliases, year):

        try:
            if not composite_enabled:
                return
            if not self.cache_status:
                return
            url = {'imdb': imdb,
                   'tvdb': tvdb,
                   'tvshowtitle': tvshowtitle,
                   'localtvshowtitle': localtvshowtitle ,
                   'year': year}
            url = urlencode(url)
            return url
        except: return

    def episode(self, url, imdb, tvdb, title, premiered, season, episode):

        try:
            if url is None: return
            url = parse_qs(url)
            url = dict([(i, url[i][0]) if url[i] else (i, '') for i in url])
            url['title'], url['premiered'], url['season'], url['episode'] = title, premiered, season, episode
            url = urlencode(url)
            return url
        except:
            return

    def parse_source_data(self, server, xml):

        src = server
        src['key'] = xml.get('key')
        src.update(xml.find('./Media').attrib)
        src['file'] = xml.find('.//Part').get('file').split('/')[-1]
        src['videoinfo'] = src['videoCodec'] + ' ' + src['videoFrameRate'] + ' ' + src['container']
        src['audioinfo'] = src['audioCodec'] + ' ' + src['audioChannels'] + 'CH '
        src['language'], src['lang_type'] = self.get_lang_by_type(src['file'])
        return src

    def sources(self, url, hostDict, hostprDict):

        try:
            sources = []
            if url is None: return sources
            url = parse_qs(url)
            url = dict([(i, url[i][0]) if url[i] else (i, '') for i in url])

            if not composite_enabled:
                return sources
            if not self.cache_status:
                return sources
            for server in self.server_list:
                if 'tvshowtitle' in url:
                    titles = [url['tvshowtitle'], url['localtvshowtitle']]
                    try:
                        self.headers['X-Plex-Token'] = server['accessToken']
                        for title in titles:
                            try:
                                build_url = self.search_link.format(scheme=server['protocol'],
                                                                    IP=server['address'],
                                                                    port=server['port'],
                                                                    path='search',
                                                                    #query='behaviorist'
                                                                    query=title
                                                                    )
                                r = self.session.get(build_url, headers=self.headers, verify=False, timeout=3)
                                show = ET.fromstring(r.text)
                                show = show.find('./Directory').get('key')
                                if isinstance(show, str):
                                    break
                            except AttributeError:
                                continue
                        seas_url = self.server_url.format(scheme=server['protocol'],
                                                          IP=server['address'],
                                                          port=server['port'],
                                                          path=show)
                        seas_list = self.session.get(seas_url, headers=self.headers, verify=False, timeout=3)
                        seas = ET.fromstring(seas_list.text)
                        ep_path = seas.find(f'./Directory[@title="Season {url["season"]}"]').get('key')
                        ep_url = self.server_url.format(scheme=server['protocol'],
                                                          IP=server['address'],
                                                          port=server['port'],
                                                          path=ep_path)
                        ep_list = self.session.get(ep_url, headers=self.headers, verify=False, timeout=3)
                        episodes = ET.fromstring(ep_list.text)
                        episodes = episodes.findall(f'./Video[@type="episode"][@index="{url["episode"]}"]'
                                                    f'[@parentTitle="Season {url["season"]}"]')

                        for episode in episodes:

                            src = self.parse_source_data(server, episode)

                            sources.append({ 'source': src['name'],
                                             'quality': source_utils.get_qual(src['videoResolution']),
                                             'language': src['language'],
                                             'url': self.composite_pattern.format(uri=src['uri'], key=src['key']),
                                             'info': src['videoinfo'] + ' | ' + src['audioinfo'] + '| ' + src['lang_type'],
                                             'direct': True,
                                             'debridonly': False})

                    except Exception as e:
                        print('series  append fault')
                        print(e)
                        pass

                else:

                    try:
                        self.headers['X-Plex-Token'] = server['accessToken']
                        build_url = self.search_link.format(scheme=server['protocol'],
                                                            IP=server['address'],
                                                            port=server['port'],
                                                            path='search',
                                                            query=url['title']
                                                           )

                        r = self.session.get(build_url, headers=self.headers, verify=False, timeout=3)

                        results = ET.fromstring(r.text)
                        results = results.findall(f'./Video[@type="movie"][@year="{url["year"]}"]')
                        for result in results:
                            src = self.parse_source_data(server, result)

                            sources.append({ 'source': src['name'],
                                             'quality': source_utils.get_qual(src['videoResolution']),
                                             'language': src['language'],
                                             'url': self.composite_pattern.format(uri=src['uri'], key=src['key']),
                                             'info': src['videoinfo'] + ' | ' + src['audioinfo'] + '| ' + src['lang_type'],
                                             'direct': True,
                                             'debridonly': False})

                    except Exception as e:
                        print('append fault')
                        print(e)
                        pass

        except Exception as e:
            print(e)
            return

        return sources

    def resolve(self, url):
        return url

    def get_lang_by_type(self, lang_type):
            if "dubbing" in lang_type.lower():
                if "kino" in lang_type.lower():
                    return 'pl', 'Dubbing Kino'
                return 'pl', 'Dubbing'
            elif 'lektor pl' in lang_type.lower():
                return 'pl', 'Lektor'
            elif '.dual' in lang_type.lower():
                return 'pl', 'multi'
            elif '.multi' in lang_type.lower():
                return 'pl', 'multi'
            elif '.pldub' in lang_type.lower():
                return 'pl', 'Dubbing'
            elif '.pl.' in lang_type.lower():
                return 'pl', ''
            elif '.sub' in lang_type.lower():
                return 'pl', 'Napisy'
            elif 'lektor' in lang_type.lower():
                return 'pl', 'Lektor'
            elif 'napisy pl' in lang_type.lower():
                return 'pl', 'Napisy'
            elif 'napisy' in lang_type.lower():
                return 'pl', 'Napisy'
            elif 'POLSKI' in lang_type.lower():
                return 'pl', ''
            elif 'pl' in lang_type.lower():
                return 'pl', ''
            return 'en', ''