import requests
from urllib.parse import parse_qs, urlparse
from resources.libs import cleantitle
from resources.libs.justwatch import JustWatch
import re
import requests
import unicodedata
tm_user = '96606974601b25618007917bb01a0f5f'
tmdb_by_imdb = 'https://api.themoviedb.org/3/find/%s?api_key=%s&external_source=imdb_id' % ('%s', tm_user)
tmdb_providers = 'https://api.themoviedb.org/3/movie/%s/watch/providers?api_key=%s' % ('%s', tm_user)
tmdb_tvproviders = 'https://api.themoviedb.org/3/tv/%s/watch/providers?api_key=%s' % ('%s', tm_user)
aliases = []


#viaplay show
url = 'imdb=tt9742936&tvdb=None&tvshowtitle=FBI%3A+Most+Wanted&year=2020&title=Odcinek+1&premiered=2020-01-07&season=1&episode=1'
#show polsatbox
#url = 'imdb=tt7366338&tvdb=None&tvshowtitle=Chernobyl&year=2019&title=1%3A23%3A45&premiered=2019-05-06&season=1&episode=1'
#show hbo
#url = 'imdb=tt0475784&tvdb=None&tvshowtitle=Westworld&year=2016&title=Chestnut&premiered=2016-10-09&season=1&episode=2'
#movie hbo
#url = 'imdb=tt0133093&title=The+Matrix&year=1999'
#show player shadź
#url = 'imdb=tt11240572&tvdb=None&tvshowtitle=Szadz&year=2020&title=Odcinek+1&premiered=2020-04-30&season=1&episode=1'
#show amazon
#url = 'imdb=tt5057054&tvdb=None&tvshowtitle=Tom+Clancy%27s+Jack+Ryan&year=2018&title=Pilot&premiered=2018-08-30&season=1&episode=1'
#show netflix
#url = 'imdb=tt8398600&tvdb=None&tvshowtitle=After+Life&year=2019&title=Odcinek+1&premiered=2019-03-08&season=1&episode=1&providerlink=https%3A%2F%2Fwww.themoviedb.org%2Ftv%2F79410-after-life%2Fwatch%3Flocale%3DPL&provider_list=Netflix'
#movie
#url = 'imdb=tt12987838&title=Making+The+Witcher&year=2020&providerlink=https%3A%2F%2Fwww.themoviedb.org%2Fmovie%2F736759-making-the-witcher%2Fwatch%3Flocale%3DPL&provider_list=Netflix'


def normalize(title):
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

def is_match(name, title, hdlr=None, aliases=None):
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
        print('is_match exc')
        return True

def netflix_ep_id(show_id, season, episode):
    header = {
        'Accept': 'application/json',
        'referer': 'https://unogs.com/',
        'referrer': 'http://unogs.com',
        'x-requested-with': 'XMLHttpRequest',
    }
    netflix_search_pattern = 'https://unogs.com/api/title/episodes?netflixid=%s'

    r = requests.get(netflix_search_pattern % show_id, headers=header, timeout=5)
    r.raise_for_status()
    r.encoding = 'utf-8'
    apianswer = r.json()
    apifetch = [s['episodes'] for s in apianswer if s['season'] == int(season)][0]
    ep_id = str([e['epid'] for e in apifetch if e['epnum'] == int(episode)][0])

    return ep_id


data = parse_qs(url)
data = dict([(i, data[i][0]) if data[i] else (i, '') for i in data])
title = data['tvshowtitle'] if 'tvshowtitle' in data else data['title']
year = data['year']
content = 'movie' if not 'tvshowtitle' in data else 'show'


result = None
country = 'PL'

jw = JustWatch(country=country)
r0 = jw.get_providers()

provid = ''



if content == 'movie':
    tmdb = requests.get(tmdb_by_imdb % data['imdb']).json()
    tmdb = tmdb['movie_results'][0]['id']

    r = jw.search_for_item(query=title.lower())
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
    if not items:
        jw0 = JustWatch(country='PL')
        titlePL = normalize(title)
        r = jw0.search_for_item(query=titlePL.lower())
        items = r['items']
        jw_id = [i for i in items if
                 is_match(' '.join((normalize(i['title']), str(i['original_release_year']))), titlePL, year, aliases)]
        jw_id = [i['id'] for i in jw_id if i['object_type'] == 'show']

    else:
        jw_id = [i for i in items if
                 is_match(' '.join((i['title'], str(i['original_release_year']))), title, year, aliases)]
        jw_id = [i['id'] for i in jw_id if i['object_type'] == 'show']

    if jw_id:
        r = jw.get_episodes(str(jw_id[0]))
        item = r['items']
        item = [i for i in item if
                i['season_number'] == int(data['season']) and i['episode_number'] == int(data['episode'])]
        if not item:
            r = jw.get_episodes(str(jw_id[0]), page='2')
            item = r['items']
            item = [i for i in item if
                    i['season_number'] == int(data['season']) and i['episode_number'] == int(data['episode'])]
        if item:
            result = item[0]

if not result:
    raise Exception('%s not found in jw database' % title)
# log_utils.log('justwatch result: ' + repr(result))

offers = result.get('offers')
if not offers:
    raise Exception('%s not available in %s' % (title, country))
# log_utils.log('justwatch offers: ' + repr(offers))

netflix = ['nfx', 'nfk']
prime = ['amp', 'prv', 'aim']
hbogo = ['hge']
hbomax = ['hmf', 'hbm', 'hbo', 'hbn']
disney = ['dnp']
iplayer = ['bbc']
playerpl = ['plp']
curstream = ['cts']
hulu = ['hlu']
paramount = ['pmp']
vodpl = ['vpl']
polsat = ['ipl']
viaplay = ['vip']

streams = []

netflix_pattern = 'plugin://plugin.video.netflix/play/movie/%s'
prime_pattern = 'plugin://plugin.video.amazon-test/?asin=%s&mode=PlayVideo&name=None&adult=0&trailer=0&selbitrate=0'
hbogo_pattern = 'plugin://plugin.video.hbogoeu/?url=PLAY&mode=5&cid='
hbomax_pattern = 'plugin://slyguy.hbo.max/?_=play&slug='
disney_pattern = 'plugin://slyguy.disney.plus/?_=play&_play=1&content_id='
iplayer_pattern = 'plugin://plugin.video.iplayerwww/?url=%s&mode=202&name=null&iconimage=null&description=null&subtitles_url=&logged_in=False'
curstream_pattern = 'plugin://slyguy.curiositystream/?_=play&_play=1&id='
hulu_pattern = 'plugin://slyguy.hulu/?_=play&id='
paramount_pattern = 'plugin://slyguy.paramount.plus/?_=play&id='
playerpl_pattern = 'plugin://plugin.video.playermb/?mode=playvid&url='
polsatbox_pattern = 'plugin://plugin.video.pgobox/?mode=playtvs&url='
viaplay_pattern = 'plugin://plugin.video.viaplay/play?guid=%s&url=None&tve=false'


nfx = [o for o in offers if o['package_short_name'] in netflix]
if nfx:
    nfx_id = nfx[0]['urls']['standard_web']
    nfx_id = nfx_id.rstrip('/').split('/')[-1]
    if content == 'movie':
        netflix_id = nfx_id
    else:  # justwatch returns show ids for nf - get episode ids from instantwatcher
        netflix_id = netflix_ep_id(nfx_id, data['season'], data['episode'])
    if netflix_id:
        # log_utils.log('official netflix_id: ' + netflix_id)
        streams.append(('netflix', netflix_pattern % netflix_id))


prv = [o for o in offers if o['package_short_name'] in prime]
if prv:
    prime_id = prv[0]['urls']['standard_web']
    prime_id = prime_id.rstrip('/').split('gti=')[1]
    # log_utils.log('official prime_id: ' + prime_id)
    streams.append(('amazon prime', prime_pattern % prime_id))


hbm = [o for o in offers if o['package_short_name'] in hbomax]
if hbm:
    hbo_id = hbm[0]['urls']['standard_web']
    hbo_id = hbo_id.rstrip('/').split('/')[-1]
    # log_utils.log('official hbo_id: ' + hbo_id)
    streams.append(('hbo max', hbomax_pattern + hbo_id))

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
#        test = "/".join(hbogo_id.replace("https://hbogo.pl", "").split("/")[:-1])
        hbogo_id = re.findall(r"href=\"%s\".data-season-number=\".*?data-season-id=\"(.*?)\"" % hbo_ep_path, hbogo_resp)[0]
        resp = requests.get("https://hbogo.pl/api/modal/meta/season/%s/ext" % hbogo_id).json()
        odcinek = item[0]["episode_number"]
#        odcinek = int(re.findall(r'\d+', hbogo_id)[-1])
        cid = resp['episodes'][odcinek-1]['media_id']
    streams.append(('hbo go', hbogo_pattern + cid))

plp = [o for o in offers if o['package_short_name'] in playerpl]
if plp:
    playerpl_id = plp[0]['urls']['standard_web']
    playerpl_id = playerpl_id.split(',')[-1]
    player_web = f'https://player.pl/playerapi/item/translate?articleId={playerpl_id}&4K=true&platform=BROWSER'
    resp = requests.get(player_web).json()
    playerpl_id = str(resp['id'])
    # TODO: sprawdzenie pakietu we wtyczce


    streams.append(('player pl', playerpl_pattern + playerpl_id))

ipl = [o for o in offers if o['package_short_name'] in polsat]
if ipl:
    polsat_id = ipl[0]['urls']['standard_web']
    polsat_id = polsat_id.rstrip('/').split('/')[-1]
    # TODO: sprawdzenie pakietu we wtyczce

    streams.append(('polsat box', polsatbox_pattern + polsat_id + '%7Cnull'))

vip = [o for o in offers if o['package_short_name'] in viaplay]
if vip:
    viaplay_url = vip[0]['urls']['standard_web']
    via_r = requests.get(viaplay_url)
    via_r = via_r.text.replace("\r", "").replace("\n", "")
    via_api = re.findall(':\"multiPartial\",\"href\":\"(.+?)&multiPartial=true', via_r)[0]
    via_api_r = requests.get(via_api).json()
    viaplay_id = via_api_r['_embedded']['viaplay:blocks'][0]['_embedded']['viaplay:product']['system']['guid']

    streams.append(('viaplay', viaplay_pattern % viaplay_id))

dnp = [o for o in offers if o['package_short_name'] in disney]
if dnp:
    disney_id = dnp[0]['urls']['deeplink_web']
    disney_id = disney_id.rstrip('/').split('/')[-1]
    # log_utils.log('official disney_id: ' + disney_id)
    streams.append(('disney+', disney_pattern + disney_id))


bbc = [o for o in offers if o['package_short_name'] in iplayer]
if bbc:
    iplayer_id = bbc[0]['urls']['standard_web']
    # log_utils.log('official iplayer_id: ' + iplayer_id)
    streams.append(('bbc iplayer', iplayer_pattern % iplayer_id))

cts = [o for o in offers if o['package_short_name'] in curstream]
if cts:
    cts_id = cts[0]['urls']['standard_web']
    cts_id = cts_id.rstrip('/').split('/')[-1]
    # log_utils.log('official cts_id: ' + cts_id)
    streams.append(('curiosity stream', curstream_pattern + cts_id))

hlu = [o for o in offers if o['package_short_name'] in hulu]
if hlu:
    hulu_id = hlu[0]['urls']['standard_web']
    hulu_id = hulu_id.rstrip('/').split('/')[-1]
    # log_utils.log('official hulu_id: ' + hulu_id)
    streams.append(('hulu', hulu_pattern + hulu_id))

pmp = [o for o in offers if o['package_short_name'] in paramount]
if pmp:
    pmp_url = pmp[0]['urls']['standard_web']
    pmp_id = pmp_url.split('?')[0].split('/')[-1] if content == 'movie' else re.findall('/video/(.+?)/', pmp_url)[0]
    # log_utils.log('official pmp_url: {0} | pmp_id: {1}'.format(pmp_url, pmp_id))
    streams.append(('paramount+', paramount_pattern + pmp_id))

list = streams

print('dupa')