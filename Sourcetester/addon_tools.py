# -*- coding: UTF-8 -*-
import sys
import re
import urllib.request, urllib.parse, urllib.error
from urllib.parse import parse_qs, quote_plus, urlencode, unquote
from resources.libs import dqplayer
import xbmc
import xbmcgui
import xbmcplugin
import xbmcaddon
import inputstreamhelper


my_addon = xbmcaddon.Addon()
Getsetting = my_addon.getSetting

def addDir(name, url, mode='', icon='', thumb='', fanart='', poster='', banner='', clearart='', clearlogo='',
           genre='', year='', rating='', dateadded='', plot='', subdir='',
           section='', page='', code='', studio='', meta='',
           isFolder=True, total=1):
    u = (sys.argv[0] + '?url=' + quote_plus(url) + '&mode=' + str(mode) + '&name='
         + quote_plus(name) + '&img=' + quote_plus(thumb)
         + '&section=' + quote_plus(section) + '&page=' + quote_plus(page)
         + '&subdir=' + quote_plus(subdir))
    liz = xbmcgui.ListItem(name)
    contextmenu = []
    contextmenu.append(('Informacja', 'Action(Info)'), )
    info = {
        'title': name,
        'genre': genre,
        'year': year,
        'rating': rating,
        'dateadded': dateadded,
        'plot': plot,
        'code': code,
        'studio': studio
    }
    liz.setInfo(type='video', infoLabels=info)
    liz.setArt({
        'thumb': thumb,
        'icon': icon,
        'fanart': fanart,
        'poster': poster,
        'banner': banner,
        'clearart': clearart,
        'clearlogo': clearlogo,
    })
    liz.addContextMenuItems(contextmenu)
    xbmcplugin.addDirectoryItem(handle=int(sys.argv[1]), url=u, listitem=liz,
                                isFolder=isFolder, totalItems=total)


def addLink(name, url, mode='', icon='', thumb='', fanart='', poster='',
            banner='', clearart='', clearlogo='', genre='', year='', subdir='',
            rating='', dateadded='', plot='', code='', studio='', meta='',
            isFolder=False, total=1,
            type='video', section='', page=''):
    u = (sys.argv[0] + '?url=' + quote_plus(url) + '&mode=' + str(mode)
         + '&name=' + quote_plus(name) + '&img=' + quote_plus(thumb)
         + '&section=' + quote_plus(section) + '&page=' + quote_plus(page)
         + '&subdir=' + quote_plus(subdir))
    liz = xbmcgui.ListItem(name)
    contextmenu = []
    contextmenu.append(('Informacja', 'Action(Info)'), )
    info = {
        'title': name,
        'plot': plot,
        'code': code,
        'studio': studio,
        'genre': genre,
        'rating': rating,
        'year': year,
        'dateadded': dateadded,
    }
    liz.setProperty('IsPlayable', 'true')
    liz.setInfo(type, infoLabels=info)
    liz.setArt({
        'thumb': thumb,
        'icon': icon,
        'fanart': fanart,
        'poster': poster,
        'banner': banner,
        'clearart': clearart,
        'clearlogo': clearlogo
    })

    liz.addContextMenuItems(contextmenu)
    xbmcplugin.addDirectoryItem(handle=int(sys.argv[1]), url=u, listitem=liz,
                                isFolder=isFolder, totalItems=total)


def get_params():
    paramstring = sys.argv[2]
    if paramstring.startswith('?'):
        paramstring = paramstring[1:]
    return dict((k, vv[0]) for k, vv in parse_qs(paramstring).items())

def PlayFromHost(url, mode, title, subdir=''):
    try:
        from urllib.parse import urlencode, quote_plus, quote, unquote
    except ImportError:
        from urllib import urlencode, quote_plus, quote, unquote

    if 'google' in url:
        url = url.replace('preview', 'view')

    #DQ Player
    if 'dqplayer' in url:
        videolink = url.split('|')[1]

        strmUrl, headers_mpd, url = dqplayer.fetch(videolink)

        UA = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/97.0.4692.71 Safari/537.36 Edg/97.0.1072.62'

        PROTOCOL = 'hls'
        DRM = 'com.widevine.alpha'

        import inputstreamhelper
        import ssl
        try:
            _create_unverified_https_context = ssl._create_unverified_context
        except AttributeError:
            pass
        else:
            ssl._create_default_https_context = _create_unverified_https_context
        certificate_data = "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 VsLobiUUxUx2s1Y//+knyk7clpgw7dzQJd+q"

        is_helper = inputstreamhelper.Helper(PROTOCOL)
        if is_helper.check_inputstream():
            li = xbmcgui.ListItem(path=strmUrl)
            li.setInfo( type="Video", infoLabels={ "Title": title, } )

            li.setMimeType('application/x-mpegURL')
            li.setContentLookup(False)

            if sys.version_info[0] > 2:
                li.setProperty('inputstream', is_helper.inputstream_addon)
            else:
                li.setProperty('inputstreamaddon', is_helper.inputstream_addon)
            li.setProperty('inputstream.adaptive.manifest_type', PROTOCOL)
            li.setProperty('inputstream.adaptive.license_type', DRM)
            #li.setProperty('inputstream.adaptive.server_certificate', certificate_data)
            li.setProperty('inputstream.adaptive.license_key', '|authority=video-91.mediadelivery.net&referer=https://iframe.mediadelivery.net/&User-Agent=' +quote(UA)+'|R{SSM}|')
            li.setProperty('inputstream.adaptive.stream_headers', 'Referer=https://iframe.mediadelivery.net/embed/22450/4dad925f-7843-4d4e-8de1-e2f09b31233e&authority=iframe.mediadelivery.net&User-Agent=' + quote(UA))
            li.setProperty('IsPlayable', 'true')

        else:
            print('dupa')

        xbmcplugin.setResolvedUrl(handle=int(sys.argv[1]), succeeded=True, listitem=li)

def SourceSelect(players, links, title, subdir=''):

    if len(players) > 0:
        d = xbmcgui.Dialog()
        select = d.select('Wybór playera', players)
        if select > -1:
            link = str(links[select])
            xbmc.log('DramaQueen.pl | Proba z : %s' % players[select] + '   ' + link + '  ', xbmc.LOGINFO)
            if Getsetting('download.opt') == 'true':
                ret = d.yesno('Pobieranie', 'Wybierz Opcję', 'Oglądaj', 'Pobierz')
                if ret:
                    mode = 'download'
                else:
                    mode = 'play'
            else:
                mode = 'play'
            PlayFromHost(link, mode='play', title=title, subdir=subdir)

        else:
            exit()
    else:
        xbmcgui.Dialog().ok('[COLOR red]Problem[/COLOR]', 'Brak linków', '')
