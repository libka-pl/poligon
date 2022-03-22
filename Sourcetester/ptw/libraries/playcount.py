# -*- coding: utf-8 -*-

"""
    Fanfilm Add-on

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

from ptw.libraries import control
from ptw.libraries import bookmarks
from ptw.libraries import trakt
from ptw.libraries import log_utils


def getMovieIndicators(refresh=False):
#    try:
#        if trakt.getTraktIndicatorsInfo():
#            raise Exception()
#        from metahandler import metahandlers
#
#        indicators = metahandlers.MetaData(preparezip=False)
#        return indicators
#    except:
#        pass
    try:
        if not trakt.getTraktIndicatorsInfo():
            raise Exception()
        if not refresh:
            timeout = 720
        else:
            timeout = 0
        indicators = trakt.cachesyncMovies(timeout=timeout)
        return indicators
    except Exception as e:
        pass


def getTVShowIndicators(refresh=False):
#   try:
#         if trakt.getTraktIndicatorsInfo() == True: raise Exception()
#         indicators_ = bookmarks._indicators()
#         return indicators_
#   except:
#         pass
    try:
        if not trakt.getTraktIndicatorsInfo(): 
            raise Exception()
        if refresh == False: 
            timeout = 720
#        elif trakt.getWatchedActivity() < trakt.timeoutsyncTVShows():
#            timeout = 720
        else: 
            timeout = 0
        indicators = trakt.cachesyncTVShows(timeout=timeout)
        return indicators
    except:
        pass


def getSeasonIndicators(imdb):
    try:
        if trakt.getTraktIndicatorsInfo() == False:
            raise Exception()
        indicators = trakt.syncSeason(imdb)
        return indicators
    except:
        pass


def getMovieOverlay(indicators, imdb):
    try:
        try:
            playcount = indicators._get_watched("movie", imdb, "", "")
            return str(playcount)
        except:
            playcount = [i for i in indicators if i == imdb]
            playcount = 7 if len(playcount) > 0 else 6
            return str(playcount)
    except:
        return "6"


def getTVShowOverlay(indicators, tmdb):
    try:
        playcount = [
            i[0] for i in indicators if i[0] == tmdb and len(i[2]) >= int(i[1])
        ]
        playcount = 7 if len(playcount) > 0 else 6
        return str(playcount)
    except:
        return "6"

def getSeasonOverlay(indicators, imdb, season):
    try:
        if trakt.getTraktIndicatorsInfo():
            playcount = [i for i in indicators if int(season) == int(i)]
            playcount = 7 if len(playcount) > 0 else 6
            return str(playcount)
        # else:
            # playcount = bookmarks._get_watched('season', imdb, season, '')
            # return str(playcount)
    except:
        return '6'
        
        
def getEpisodeOverlay(indicators, imdb, tmdb, season, episode):
    try:
        if trakt.getTraktIndicatorsInfo() == False:
            overlay = bookmarks._get_watched('episode', imdb, season, episode)
            return str(overlay)
        else:
            playcount = [i[2] for i in indicators if i[0] == tmdb]
            playcount = playcount[0] if len(playcount) > 0 else []
            playcount = [i for i in playcount if int(season) == int(i[0]) and int(episode) == int(i[1])]
            overlay = 7 if len(playcount) > 0 else 6
            return str(overlay)
    except:
        return '6'


def markMovieDuringPlayback(imdb, watched):
    try:
        if trakt.getTraktIndicatorsInfo() == False:
            raise Exception()

        if int(watched) == 7:
            trakt.markMovieAsWatched(imdb)
        else:
            trakt.markMovieAsNotWatched(imdb)
        trakt.cachesyncMovies()

        if trakt.getTraktAddonMovieInfo() == True:
            trakt.markMovieAsNotWatched(imdb)
    except:
        pass

    try:
        from metahandler import metahandlers

        metaget = metahandlers.MetaData(preparezip=False)
        metaget.get_meta("movie", name="", imdb_id=imdb)
        metaget.change_watched("movie", name="", imdb_id=imdb, watched=int(watched))
    except:
        pass


def markEpisodeDuringPlayback(imdb, tvdb, season, episode, watched):
    try:
        if trakt.getTraktIndicatorsInfo() == False:
            raise Exception()

        if int(watched) == 7:
            trakt.markEpisodeAsWatched(imdb, season, episode)
        else:
            trakt.markEpisodeAsNotWatched(imdb, season, episode)
        trakt.cachesyncTVShows()

        if trakt.getTraktAddonEpisodeInfo() == True:
            trakt.markEpisodeAsNotWatched(imdb, season, episode)
    except:
        pass

    try:
        from metahandler import metahandlers

        metaget = metahandlers.MetaData(preparezip=False)
        metaget.get_meta("tvshow", name="", imdb_id=imdb)
        metaget.get_episode_meta("", imdb_id=imdb, season=season, episode=episode)
        metaget.change_watched(
            "episode",
            "",
            imdb_id=imdb,
            season=season,
            episode=episode,
            watched=int(watched),
        )
    except:
        pass


def movies(imdb, watched):
    control.busy()
    try:
        if trakt.getTraktIndicatorsInfo() == False:
            raise Exception()
        if int(watched) == 7:
            trakt.markMovieAsWatched(imdb)
        else:
            trakt.markMovieAsNotWatched(imdb)
        trakt.cachesyncMovies()
        control.refresh()
    except:
        pass

    try:
        from metahandler import metahandlers

        metaget = metahandlers.MetaData(preparezip=False)
        metaget.get_meta("movie", name="", imdb_id=imdb)
        metaget.change_watched("movie", name="", imdb_id=imdb, watched=int(watched))
        if trakt.getTraktIndicatorsInfo() == False:
            control.refresh()
    except:
        pass


def episodes(imdb, tmdb, season, episode, watched):
#    control.busy()
    try:
        if trakt.getTraktIndicatorsInfo() == False: raise Exception()
        if int(watched) == 7: trakt.markEpisodeAsWatched(imdb, season, episode)
        else: trakt.markEpisodeAsNotWatched(imdb, season, episode)
        trakt.cachesyncTVShows()
        control.refresh()
#        control.idle()
    except:
        pass

    try:
        if int(watched) == 7:
            bookmarks.reset(1, 1, 'episode', imdb, season, episode)
        else:
            bookmarks._delete_record('episode', imdb, season, episode)
        if trakt.getTraktIndicatorsInfo() == False: control.refresh()
#        control.idle()
    except:
        pass


def tvshows(tvshowtitle, imdb, tmdb, season, watched):
    control.busy()
    try:
        import sys,xbmc

        if not trakt.getTraktIndicatorsInfo() == False: raise Exception()

        from resources.lib.indexers import episodes

        name = control.addonInfo('name')

        dialog = control.progressDialogBG
        dialog.create(str(name), str(tvshowtitle))
        dialog.update(0, str(name), str(tvshowtitle))

        #log_utils.log('playcount_season: ' + str(season))
        items = []
        if season:
            items = episodes.episodes().get(tvshowtitle, '0', imdb, tmdb, meta=None, season=season, idx=False)
            items = [i for i in items if int('%01d' % int(season)) == int('%01d' % int(i['season']))]
            items = [{'label': '%s S%02dE%02d' % (tvshowtitle, int(i['season']), int(i['episode'])), 'season': int('%01d' % int(i['season'])), 'episode': int('%01d' % int(i['episode'])), 'unaired': i['unaired']} for i in items]

            for i in range(len(items)):
                if control.monitor.abortRequested(): return sys.exit()

                dialog.update(int((100 / float(len(items))) * i), str(name), str(items[i]['label']))

                _season, _episode, unaired = items[i]['season'], items[i]['episode'], items[i]['unaired']
                if int(watched) == 7:
                    if not unaired == 'true':
                        bookmarks.reset(1, 1, 'episode', imdb, _season, _episode)
                    else: pass
                else:
                    bookmarks._delete_record('episode', imdb, _season, _episode)

        else:
            seasons = episodes.seasons().get(tvshowtitle, '0', imdb, tmdb, meta=None, idx=False)
            seasons = [i['season'] for i in seasons]
            #log_utils.log('playcount_seasons: ' + str(seasons))
            for s in seasons:
                items = episodes.episodes().get(tvshowtitle, '0', imdb, tmdb, meta=None, season=s, idx=False)
                items = [{'label': '%s S%02dE%02d' % (tvshowtitle, int(i['season']), int(i['episode'])), 'season': int('%01d' % int(i['season'])), 'episode': int('%01d' % int(i['episode'])), 'unaired': i['unaired']} for i in items]
                #log_utils.log('playcount_items2: ' + str(items))

                for i in range(len(items)):
                    if control.monitor.abortRequested(): return sys.exit()

                    dialog.update(int((100 / float(len(items))) * i), str(name), str(items[i]['label']))

                    _season, _episode, unaired = items[i]['season'], items[i]['episode'], items[i]['unaired']
                    if int(watched) == 7:
                        if not unaired == 'true':
                            bookmarks.reset(1, 1, 'episode', imdb, _season, _episode)
                        else: pass
                    else:
                        bookmarks._delete_record('episode', imdb, _season, _episode)

        try: dialog.close()
        except: pass
    except:
        log_utils.log('playcount_local_shows', 'module')
        try: dialog.close()
        except: pass


    try:
        if trakt.getTraktIndicatorsInfo() == False: raise Exception()

        #log_utils.log('playcount_season: ' + str(season))
        if season:
            from resources.lib.indexers import episodes
            items = episodes.episodes().get(tvshowtitle, '0', imdb, tmdb, meta=None, season=season, idx=False)
            items = [(int(i['season']), int(i['episode'])) for i in items]
            items = [i[1] for i in items if int('%01d' % int(season)) == int('%01d' % i[0])]
            for i in items:
                if int(watched) == 7: trakt.markEpisodeAsWatched(imdb, season, i)
                else: trakt.markEpisodeAsNotWatched(imdb, season, i)
        else:
            if int(watched) == 7: trakt.markTVShowAsWatched(imdb)
            else: trakt.markTVShowAsNotWatched(imdb)
        trakt.cachesyncTVShows()
    except:
        log_utils.log('playcount_trakt_shows', 'module')
        pass

    control.refresh()
    control.idle()
