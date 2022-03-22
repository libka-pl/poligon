# -*- coding: utf-8 -*-

"""
    FanFilm Add-on

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
import json
import re
import sys
from urllib.parse import quote_plus

from ptw.libraries import client
from ptw.libraries import control
from ptw.libraries.youtube_search import YoutubeSearch


class trailer:
    def __init__(self):
        self.youtube_watch = "https://www.youtube.com/watch?v=%s"

    def play(self, name="", url="", windowedtrailer=0):
        try:
            url = self.worker(name, url)
            if not url:
                control.idle()
                return

            title = control.infoLabel("ListItem.Title")
            if not title:
                title = control.infoLabel("ListItem.Label")
            icon = control.infoLabel("ListItem.Icon")

            item = control.item(
                label=name, path=url
            )
            #iconImage=icon, thumbnailImage=icon
            item.setArt({"thumb": icon, "icon": icon})
            item.setInfo(type="Video", infoLabels={"Title": name})

            item.setProperty("IsPlayable", "true")
            control.resolve(handle=int(sys.argv[1]), succeeded=True, listitem=item)
            if windowedtrailer == 1:
                # The call to the play() method is non-blocking. So we delay further script execution to keep the script alive at this spot.
                # Otherwise this script will continue and probably already be garbage collected by the time the trailer has ended.
                control.sleep(
                    1000
                )  # Wait until playback starts. Less than 900ms is too short (on my box). Make it one second.
                while control.player.isPlayingVideo():
                    control.sleep(1000)
                # Close the dialog.
                # Same behaviour as the fullscreenvideo window when :
                # the media plays to the end,
                # or the user pressed one of X, ESC, or Backspace keys on the keyboard/remote to stop playback.
                control.execute("Dialog.Close(%s, true)" % control.getCurrentDialogId)
        except:
            pass

    def worker(self, name, url):
        query = name + " trailer"
        #query = self.search_link % quote_plus(query)
        return self.search(query)

    def search(self, url):
        try:
            results = json.loads(YoutubeSearch(url, max_results=1).to_json())
            url = self.resolve(results['videos'][0]['id'])
            if url:
                return url
        except:
            return

    def resolve(self, url):
        try:
            id = url.split("?v=")[-1].split("/")[-1].split("?")[0].split("&")[0]
            result = client.request(self.youtube_watch % id)

            message = client.parseDOM(
                result, "div", attrs={"id": "unavailable-submessage"}
            )
            message = "".join(message)

            alert = client.parseDOM(
                result, "div", attrs={"id": "watch7-notification-area"}
            )

            if len(alert) > 0:
                raise Exception()
            if re.search("[a-zA-Z]", message):
                raise Exception()

            url = "plugin://plugin.video.youtube/play/?video_id=%s" % id
            return url
        except:
            return
