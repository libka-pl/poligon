# -*- coding: utf-8 -*-

'''
    FanFilm Add-on  2021
    Źródło w fazie testów
'''

import re
import requests
from urllib.parse import parse_qs, urlencode, urlparse
from collections.abc import Mapping

from ptw.libraries import cleantitle, control, log_utils, apis
from resources.lib.indexers.justwatch import JustWatch

# For playermb mylist support
import os.path
import json
import xbmcvfs
import xbmcaddon

netflix_plugin = 'plugin.video.netflix'
prime_plugin = 'plugin.video.amazon-test'
hbogo_plugin = 'plugin.video.hbogoeu'
hbomax_plugin = 'slyguy.hbo.max'
disney_plugin = 'slyguy.disney.plus'
iplayer_plugin = 'plugin.video.iplayerwww'
curstream_plugin = 'slyguy.curiositystream'
hulu_plugin = 'slyguy.hulu'
paramount_plugin = 'slyguy.paramount.plus'
playerpl_plugin = 'plugin.video.playermb'
polsatbox_plugin = 'plugin.video.pgobox'
viaplay_plugin = 'plugin.video.viaplay'
vodpl_plugin = ''
upcgo_plugin = 'plugin.video.horizongo'

netflix_enabled = False #control.condVisibility('System.HasAddon(%s)' % netflix_plugin)
prime_enabled = False #control.condVisibility('System.HasAddon(%s)' % prime_plugin)
hbogo_enabled = False #control.condVisibility('System.HasAddon(%s)' % hbogo_plugin)
hbomax_enabled = control.condVisibility('System.HasAddon(%s)' % hbomax_plugin) or True
disney_enabled = False #control.condVisibility('System.HasAddon(%s)' % disney_plugin)
iplayer_enabled = False #control.condVisibility('System.HasAddon(%s)' % iplayer_plugin)
curstream_enabled = False #control.condVisibility('System.HasAddon(%s)' % curstream_plugin)
hulu_enabled = False #control.condVisibility('System.HasAddon(%s)' % hulu_plugin)
paramount_enabled = False #control.condVisibility('System.HasAddon(%s)' % paramount_plugin)
playerpl_enabled = False #control.condVisibility('System.HasAddon(%s)' % playerpl_plugin)
polsatbox_enabled = False #control.condVisibility('System.HasAddon(%s)' % polsatbox_plugin)
viaplay_enabled = False #control.condVisibility('System.HasAddon(%s)' % viaplay_plugin)
vodpl_enabled = False # control.condVisibility('System.HasAddon(%s)' % vodpl_plugin)
upcgo_enabled = False # control.condVisibility('System.HasAddon(%s)' % upcgo_plugin )

netflix_pattern = 'plugin://plugin.video.netflix/play/movie/%s'
prime_pattern = 'plugin://plugin.video.amazon-test/?asin=%s&mode=PlayVideo&name=None&adult=0&trailer=0&selbitrate=0'
hbogo_pattern = 'plugin://plugin.video.hbogoeu/?url=PLAY&mode=5&cid='
hbomax_pattern = 'plugin://slyguy.hbo.max/?_=play&slug='
disney_pattern = 'plugin://slyguy.disney.plus/?_=play&_play=1&content_id='
iplayer_pattern = 'plugin://plugin.video.iplayerwww/?url=%s&mode=202&name=null&iconimage=null&description=null&subtitles_url=&logged_in=False'
curstream_pattern = 'plugin://slyguy.curiositystream/?_=play&_play=1&id='
hulu_pattern = 'plugin://slyguy.hulu/?_=play&id='
paramount_pattern = 'plugin://slyguy.paramount.plus/?_=play&id='
playerpl_pattern = 'plugin://plugin.video.playermb/?mode=playvid&url={id}'
polsatbox_pattern = 'plugin://plugin.video.pgobox/?mode=playtvs&url='
viaplay_pattern = 'plugin://plugin.video.viaplay/play?guid=%s&url=None&tve=false'
vodpl_pattern = ''
upcgo_pattern = ''


scraper_init = any(e for e in [netflix_enabled,
                               prime_enabled,
                               hbomax_enabled,
                               hbogo_enabled,
                               disney_enabled,
                               iplayer_enabled,
                               curstream_enabled,
                               hulu_enabled,
                               paramount_enabled,
                               playerpl_enabled,
                               polsatbox_enabled,
                               viaplay_enabled,
                               vodpl_enabled,
                               upcgo_enabled]
                   )


class source:

    #: Skip all VoD in PlayerMB if VoD is not available
    PLAYERMB_SKIP_UNAVAILABLE = True

    def __init__(self):
        self.priority = 1
        self.language = ['pl']
        self.domains = []
        self.base_link = ''
        self.session = requests.Session()
        self.tm_user = apis.tmdb_API
        self.country = control.setting('external.country') or 'PL'
        self.tmdb_by_imdb = f'https://api.themoviedb.org/3/find/%s?api_key={self.tm_user}&external_source=imdb_id'
        self.movie_prov = f'https://api.themoviedb.org/3/movie/%s/watch/providers?api_key={self.tm_user}'
        self.tv_prov = f'https://api.themoviedb.org/3/tv/%s/watch/providers?api_key={self.tm_user}'
        self.aliases = []

    def movie(self, imdb, title, localtitle, aliases, year):
        if not scraper_init:
            return

        try:
            self.aliases.extend(aliases)
            url = {'imdb': imdb, 'title': title, 'year': year, 'localtitle': localtitle}
            url = urlencode(url)
            return url
        except:
            return

    def tvshow(self, imdb, tvdb, tvshowtitle, localtvshowtitle, aliases, year):
        if not scraper_init:
            return

        try:
            self.aliases.extend(aliases)
            url = {'imdb': imdb, 'tvdb': tvdb, 'tvshowtitle': tvshowtitle, 'localtvshowtitle': localtvshowtitle, 'year': year}
            url = urlencode(url)
            return url
        except Exception:
            return

    def episode(self, url, imdb, tvdb, title, premiered, season, episode):
        try:
            if url is None: return
            url = parse_qs(url)
            url = dict([(i, url[i][0]) if url[i] else (i, '') for i in url])
            url['title'], url['premiered'], url['season'], url['episode'] = title, premiered, season, episode
            url = urlencode(url)
            return url
        except Exception:
            return

    def sources(self, url, hostDict, hostprDict):
        try:
            log_utils.log(f'sources({url!r})...', log_utils.LOGDEBUG)
            return self._sources(url, hostDict, hostprDict)
        except Exception as exc:
            import traceback
            tb = traceback.format_exc()
            log_utils.log(f'sources({url!r}):\nException: {exc}\n{tb}', log_utils.LOGINFO)
            return []

    def _sources(self, url, hostDict, hostprDict):
        def jget(url, params=None):
            return requests.get(url, params=params).json()

        sources = []
        if url is None:
            return sources

        data = parse_qs(url)
        data = dict([(i, data[i][0]) if data[i] else (i, '') for i in data])
        title = data['tvshowtitle'] if 'tvshowtitle' in data else data['title']
        year = data['year']
        content = 'movie' if not 'tvshowtitle' in data else 'show'

        result = None

        jw = JustWatch(country=self.country)
        # r0 = jw.get_providers()
        # log_utils.log('justwatch {0} providers: {1}'.format(self.country, repr(r0)))

        if content == 'movie':
            tmdb = requests.get(self.tmdb_by_imdb % data['imdb']).json()
            tmdb = tmdb['movie_results'][0]['id']

            r = jw.search_for_item(query=title.lower())
            r = jw.search_for_item(query='dark', **{'release_year_from': 2017})


            items = r['items']

            for item in items:
                tmdb_id = item['scoring']
                if tmdb_id:
                    tmdb_id = [t['value'] for t in tmdb_id if t['provider_type'] == 'tmdb:id']
                    if tmdb_id:
                        if tmdb_id[0] == tmdb:
                            result = item
                            break

        else:
            jw0 = JustWatch(country='US')
            r = jw0.search_for_item(query=title.lower())

            items = r['items']

            jw_id = [i for i in items
                     if self.is_match(' '.join((i['title'], str(i['original_release_year']))), title, year, self.aliases)]
            jw_id = [i['id'] for i in jw_id if i['object_type'] == 'show']

            if not jw_id:
                jw0 = JustWatch(country='PL')
                titlePL = self.normalize(title)
                r = jw0.search_for_item(query=titlePL.lower())
                items = r['items']
                jw_id = [i for i in items if
                         self.is_match(' '.join((self.normalize(i['title']), str(i['original_release_year']))), titlePL, year, self.aliases)]
                jw_id = [i['id'] for i in jw_id if i['object_type'] == 'show']

            if jw_id:
                r = jw.get_episodes(str(jw_id[0]))
                item = r['items']
                item = [i for i in item if i['season_number'] == int(data['season']) and i['episode_number'] == int(data['episode'])]
                if not item:
                    r = jw.get_episodes(str(jw_id[0]), page='2')
                    item = r['items']
                    item = [i for i in item if i['season_number'] == int(data['season']) and i['episode_number'] == int(data['episode'])]
                if item:
                    result = item[0]

        if not result:
            raise Exception(f'{title!r} not found in jw database')
        #log_utils.log('justwatch result: ' + repr(result))

        offers = result.get('offers')
        if not offers:
            raise Exception(f'{title!r} not available in {self.country!r}')
        #log_utils.log('justwatch offers: ' + repr(offers))

        netflix = ['nfx', 'nfk']
        prime = ['amp', 'prv', 'aim']
        hbo = ['hmf', 'hbm', 'hbo', 'hbn']
        hbogo = ['hge']
        disney = ['dnp']
        iplayer = ['bbc']
        curstream = ['cts']
        hulu = ['hlu']
        paramount = ['pmp']
        playerpl = ['plp']
        polsatbox = ['ipl']
        viaplay = ['vip']
        vodpl = ['vpl']
        upcgo = ['hrz']

        streams = []

        if netflix_enabled:
            nfx = [o for o in offers if o['package_short_name'] in netflix]
            if nfx:
                nfx_id = nfx[0]['urls']['standard_web']
                nfx_id = nfx_id.rstrip('/').split('/')[-1]
                if content == 'movie':
                    netflix_id = nfx_id
                else:
                    netflix_id = self.netflix_ep_id(nfx_id, data['season'], data['episode'])
                if netflix_id:
                    #log_utils.log('official netflix_id: ' + netflix_id)
                    streams.append(('netflix', netflix_pattern % netflix_id))

        if prime_enabled:
            prv = [o for o in offers if o['package_short_name'] in prime]
            if prv:
                prime_id = prv[0]['urls']['standard_web']
                prime_id = prime_id.rstrip('/').split('gti=')[1]
                #log_utils.log('official prime_id: ' + prime_id)
                streams.append(('amazon prime', prime_pattern % prime_id))

        if hbomax_enabled:
            hbm = [o for o in offers if o['package_short_name'] in hbo]
            if hbm:
                hbo_id = hbm[0]['urls']['standard_web']
                hbo_id = hbo_id.rstrip('/').split('/')[-1]
                #log_utils.log('official hbo_id: ' + hbo_id)
                streams.append(('hbo max', hbomax_pattern + hbo_id))

        if hbogo_enabled:
            hge = [o for o in offers if o['package_short_name'] in hbogo]
            if hge:
                hge_id = hge[0]['urls']['standard_web']
                hbogo_path = urlparse(hge_id).path
                hbogo_resp = requests.get(hge_id).text
                hbogo_resp = hbogo_resp.replace("\r", "").replace("\n", "")

                if content == 'movie':
                    hbogo_id = re.findall(r"href=\"%s#play\".*?data-external-id=\"(.*?)\"" % hbogo_path, hbogo_resp)[0]
                    resp = requests.get("https://plapi.hbogo.eu/v8/ContentByExternalId/json/POL/COMP/%s/1" % hbogo_id).json()
                    cid = resp['Id']
                else:
                    hbo_ep_path = "/".join(hbogo_path.split("/")[:-1])
                    hbogo_id = re.findall(r"href=\"%s\".data-season-number=\".*?data-season-id=\"(.*?)\"" % hbo_ep_path, hbogo_resp)[0]
                    resp = requests.get("https://hbogo.pl/api/modal/meta/season/%s/ext" % hbogo_id).json()
                    odcinek = item[0]["episode_number"]
                    cid = resp['episodes'][odcinek-1]['media_id']
                streams.append(('hbo go', hbogo_pattern + cid))

        if playerpl_enabled:
            def load_mylist():
                try:
                    profile = xbmcaddon.Addon('plugin.video.playermb').getAddonInfo('profile')
                    path = xbmcvfs.translatePath(profile)
                    path = os.path.join(path, 'cache', 'mylist.json')
                    with open(path) as f:
                        return set(json.load(f))
                except Exception:
                    return set()

            def is_allowed(vod):
                """Check if item (video, folder) is available in current pay plan."""
                return (
                    # not have to pay and not on ncPlus, it's means free
                    not (vod.get('payable') or vod.get('ncPlus'))
                    # or it's on myslit, it's means it is in pay plan
                    or vod.get('id') in mylist)

            def append(vod):
                allowed = not mylist or is_allowed(vod)
                if self.PLAYERMB_SKIP_UNAVAILABLE and not allowed:
                    return
                quality = '4K' if vod.get('uhd') else '1080p'
                streams.append({'source': 'player pl' if allowed else 'player pl (X)',
                                'url': playerpl_pattern.format(id=vod['id']),
                                'quality': quality})

            plp = [o for o in offers if o['package_short_name'] in playerpl]
            if plp:
                params = {'4K': 'true', 'platform': 'BROWSER'}
                mylist = load_mylist()
                r = re.search((r'(?:/(?P<serial_slug>[^/]*)-odcinki,(?P<sid>\d+))?'
                               r'/(?P<slug>[^/]+?)(?:,S(?P<season>\d+)E(?P<episode>\d+))?,(?P<id>\d+)$'),
                              plp[0]['urls']['standard_web'])
                if r:
                    slug, aid, sn, en = r.group('slug', 'id', 'season', 'episode')
                    if sn:
                        slug = r.group('serial_slug')
                        sn, en = int(sn), int(en)
                    resp = jget(f'https://player.pl/playerapi/item/translate?articleId={aid}', params)
                    vid = resp['id']
                    # check if video is avaliable and find better one
                    data = jget(f'https://player.pl/playerapi/product/vod/{vid}', params)
                    # try to find by slug, it should be better then title
                    found = jget('https://player.pl/playerapi/product/vod/search', params={**params, 'keyword': slug})
                    for item in found.get('items', []):
                        season = item.get('season', {})
                        serial = item.get('season', season.get('serial', {}))
                        vslug = item['slug'] or season.get('slug', '') or serial.get('slug', '')
                        if vslug == slug:
                            if sn and en:
                                # episode
                                url = f'https://player.pl/playerapi/product/vod/serial/{item["id"]}/season/list'
                                for season in jget(url, params=params):
                                    if season['number'] == sn:
                                        url = f'https://player.pl/playerapi/product/vod/serial/{item["id"]}/season/{season["id"]}/episode/list'
                                        for episode in jget(url, params=params):
                                            if episode['episode'] == en:
                                                append(episode)
                                                break
                            else:
                                # vod (movie)
                                append(item)

        if polsatbox_enabled:
            ipl = [o for o in offers if o['package_short_name'] in polsatbox]
            if ipl:
                polsat_id = ipl[0]['urls']['standard_web']
                polsat_id = polsat_id.rstrip('/').split('/')[-1]
                # TODO: sprawdzenie pakietu we wtyczce

                streams.append(('polsat box', polsatbox_pattern + polsat_id + '%7Cnull'))

        if viaplay_enabled:
            vip = [o for o in offers if o['package_short_name'] in viaplay]
            if vip:
                viaplay_url = vip[0]['urls']['standard_web']
                via_r = requests.get(viaplay_url)
                via_r = via_r.text.replace("\r", "").replace("\n", "")
                via_api = re.findall(':\"multiPartial\",\"href\":\"(.+?)&multiPartial=true', via_r)[0]
                via_api_r = requests.get(via_api).json()
                viaplay_id = via_api_r['_embedded']['viaplay:blocks'][0]['_embedded']['viaplay:product']['system']['guid']
                streams.append(('viaplay', viaplay_pattern % viaplay_id))

        if disney_enabled:
            dnp = [o for o in offers if o['package_short_name'] in disney]
            if dnp:
                disney_id = dnp[0]['urls']['deeplink_web']
                disney_id = disney_id.rstrip('/').split('/')[-1]
                #log_utils.log('official disney_id: ' + disney_id)
                streams.append(('disney+', disney_pattern + disney_id))

        if iplayer_enabled:
            bbc = [o for o in offers if o['package_short_name'] in iplayer]
            if bbc:
                iplayer_id = bbc[0]['urls']['standard_web']
                #log_utils.log('official iplayer_id: ' + iplayer_id)
                streams.append(('bbc iplayer', iplayer_pattern % iplayer_id))

        if curstream_enabled:
            cts = [o for o in offers if o['package_short_name'] in curstream]
            if cts:
                cts_id = cts[0]['urls']['standard_web']
                cts_id = cts_id.rstrip('/').split('/')[-1]
                #log_utils.log('official cts_id: ' + cts_id)
                streams.append(('curiosity stream', curstream_pattern + cts_id))

        if hulu_enabled:
            hlu = [o for o in offers if o['package_short_name'] in hulu]
            if hlu:
                hulu_id = hlu[0]['urls']['standard_web']
                hulu_id = hulu_id.rstrip('/').split('/')[-1]
                #log_utils.log('official hulu_id: ' + hulu_id)
                streams.append(('hulu', hulu_pattern + hulu_id))

        if paramount_enabled:
            pmp = [o for o in offers if o['package_short_name'] in paramount]
            if pmp:
                pmp_url = pmp[0]['urls']['standard_web']
                pmp_id = pmp_url.split('?')[0].split('/')[-1] if content == 'movie' else re.findall('/video/(.+?)/', pmp_url)[0]
                #log_utils.log('official pmp_url: {0} | pmp_id: {1}'.format(pmp_url, pmp_id))
                streams.append(('paramount+', paramount_pattern + pmp_id))

        if vodpl_enabled:
            vpl = [o for o in offers if o['package_short_name'] in vodpl]
            if vpl:
                vodpl_url = vpl[0]['urls']['standard_web']
                vodpl_id = vodpl_url
                streams.append(('upc go', vodpl_pattern + vodpl_id))

        if upcgo_enabled:
            hrz = [o for o in offers if o['package_short_name'] in upcgo]
            if hrz:
                upcgo_url = hrz[0]['urls']['standard_web']
                upcgo_id = upcgo_url
                streams.append(('upc go', upcgo_pattern + upcgo_id))

        if streams:
            default = {'quality': '1080p',
                       'language': 'pl',
                       'direct': True,
                       'debridonly': False,
                       'external': True}
            for s in streams:
                if isinstance(s, Mapping):
                    ss = s
                else:
                    ss = {'source': s[0], 'url': s[1]}
                sources.append({**default, **ss})

        return sources


    def resolve(self, url):
        return url


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
                try:
                    titles.extend([cleantitle.get(i['title']) for i in aliases])
                except:
                    pass

            if hdlr:
                return (t in titles and hdlr.lower() in name)
            return t in titles
        except:
            log_utils.log('is_match exc', 1)
            return True

    def normalize(self, title):
        import unicodedata
        try:
            return str(
                "".join(
                    c
                    for c in unicodedata.normalize("NFKD", title)
                    if unicodedata.category(c) != "Mn"
                )
            ).replace("ł", "l")
        except:
            title = (title
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

    def netflix_ep_id(self, show_id, season, episode):
        header = {
            'Accept': 'application/json',
            'referer': 'https://unogs.com/',
            'referrer': 'http://unogs.com',
            'x-requested-with': 'XMLHttpRequest',
        }
        netflix_search_pattern = 'https://unogs.com/api/title/episodes?netflixid=%s'

        r = self.session.get(netflix_search_pattern % show_id, headers=header, timeout=5)
        r.raise_for_status()
        r.encoding = 'utf-8'
        apianswer = r.json()
        apifetch = [s['episodes'] for s in apianswer if s['season'] == int(season)][0]
        ep_id = str([e['epid'] for e in apifetch if e['epnum'] == int(episode)][0])

        return ep_id



