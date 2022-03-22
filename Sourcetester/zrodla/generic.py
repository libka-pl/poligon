import re
import urllib
import urlparse
from resources.lib.modules import cleantitle
from resources.lib.modules import client
from resources.lib.modules import proxy


class source:
    def __init__(self):
        self.priority = 1  # Set to '0' or '1'. This should always be set to '1', as '0' will double the timeout scraper time.
        self.language = ['en']  # The language of the source.
        self.domains = ['yourwebsite.com']  # The domain(s) of the source. Seperate with a comma like so: ['domain1.com','domain2.com,'domain3.com']
        self.base_link = 'https://yourwebsite.com'  # The full URL of the site, including 'http://' or 'https://'
        self.search_link = '/search/%s'  # The search URL. We use %s in place of where the search term would go.

    def movie(self, imdb, title, localtitle, aliases, year):

        # Different websites may require different search terms, or different ways of finding streams.
        # For this website, to find a movie all we need is the title and the year.

        try:

            # We need to turn the title into a string that can be used in a URL.
            # If you do a search for a random movie on filepursuit.com, you will notice that it uses a '+' or '-' in place of spaces.
            # To replicate this we use the 'cleantitle' module from lib.modules.cleantitle... We have already imported this at the top of the file.
            # There are many different things we can do with the cleantitle module and you can view them all by opening the python file in notepad.

            # For now, we will concentrate just on 'geturl'.
            # 'geturl' will change the string to make it websafe, and replace any encoding, including making spaces, ':', etc. into a '-'.
            # We use 'title = cleantitle.geturl(title)' to make the string websafe. The entry in the brackets is what we need to convert.
            # If a URL uses the '+' sign into stead of '-' we can change that by adding the following line: title = title.replace('-','+')

            title = cleantitle.geturl(title)

            # We are defining the search term as 'url', so that the add-on has no issue passing it onto the next stage (which is 'sources').
            # The search term we want is the title and year, ie: 'Deadpool 2 2018'.
            # What we actually want it to look like is 'deadpool-2-2018', so that it can be used in the search url.
            # We have already converted the title, so now we just need to add the year. We do that in the following way:

            url = '%s+%s' % (title, year)

            # We then return the search term as 'url' for it to pass on to the next stage.

            return url
        except:
            return

    def tvshow(self, imdb, tvdb, tvshowtitle, localtvshowtitle, aliases, year):
        # Searching for a TV show / episode is much the same as for a movie, except it is broken into two parts.
        # First we must get the TV show title, and then the episode. Here is how get the TV show title.
        try:
            # We need to do a cleantitle.geturl like in the above movie example.
            # Because this is the only information we need for this source, we can tag it straight away as 'url' to send it to the next part.

            url = cleantitle.geturl(tvshowtitle)
            return url
        except:
            return

    def episode(self, url, imdb, tvdb, title, premiered, season, episode):
        try:
            if not url: return

            # To make things easier, we will import the 'url' from the tvshow entry as 'tvshowtitle'.
            # We do that as below:

            tvshowtitle = url

            # We do this purely just to stop confusion later on. We now know that when we need the title for the TV show, we can just call on 'tvshowtitle'.

            # A lot of the time, for an episode, we only need the single digit number.
            # ie: for Season 1, we just need '1'.
            # Sometimes, however, we will need the double digit. ie: '01'.
            # For this website, we need the double digit so that we can use the 'S01E01' style search term.
            # Do that, we do it like this:

            season = '%02d' % int(season)
            episode = '%02d' % int(episode)

            # Now, when we reference season and episode it will give us the double digit entry.
            # We can now put our search term together. Like with other parts of this file, the search term will be put down as 'url'.
            # For this search term we want it to read 'TV Show SxxExx', so we do it as follows:

            url = '%s+s%se%s' % (tvshowtitle, str(season), str(episode))

            # We are using the additional str() parameters on season and episode to make sure that python reads those as a string and not an integer.
            # We then return the 'url' so that it can be used in the next section.

            return url
        except:
            return

    def sources(self, url, hostDict, hostprDict):

        # This is the part of the file where we actually grab the URL's for the streams.
        # This can get quite complicated, but practice makes perfect, and you must have patience and learn to trial and error everything.

        try:
            sources = []

            # We need to now set a URL for the scraper to look at to grab the streams. We do this by combining the base_link, search_link and search term.
            # First, for ease, lets define the search term from the previous section as 'query'. We do that like so:

            query = url

            # We can now set the url by simply combining the base_link and search_link with a '+'.
            # We use thw '% query' at the end of the line to tell it to place the query string in the place of the %s in the search_link string.
            # So, we define the URL that we want to search as such:

            url = self.base_link + self.search_link % query

            # We now want to give the scraper a command to go onto the internet. We do that with 'client.request()', and we have already imported 'client'.
            # We put the url definition inside the brackets, like this:

            r = client.request(url)

            # We then use a 'try' and 'except' command to search the website.
            # This is used so that if it cannot read the website it does not hang up the task.

            try:
                # The following line is used to find the line of code in the webpage where the link to the stream is.
                # We use (.+?) where the link would be.
                # To find this information, you can right click the link in Chrome and select 'Inspect'.
                # For other web browsers, you can right click and select 'View Source'.

                match = re.compile('data-clipboard-text="(.+?)"').findall(r)

                # We can use multiple instances of (.+?) to grab certain data, from the link, to quality, or filename.

                # Once we have pointed the code where we need it to look, we can do a 'for in match'.
                # We need to tell it what each (.+?) in the match definition is. We list these in order of how it finds them.
                # For this website we are only finding the stream link, so we just do this:

                for url in match:

                    # If there were multiple (.+?) then we would list it like this:
                    # for match1, match2, match3 in match:

                    # Because this website links direct to .mp4 and .mkv files, we have some additional information in the filename.
                    # We can use the filename to grab the video quality. To do this, we will use an 'if' statement.

                    # We can use 'if', 'elif' and 'else' here to tell your add-on what the quality is.
                    # We do this by asking it if a certain string is in the string defined 'url', and then setting the quality, like this:

                    if '2160' in url:
                        quality = '4K'

                    # We then use an elif command, which tells it that if the above string isn't in url, then try this one. We can have multiple elif's, like so:

                    elif '4k' in url:
                        quality = '4K'
                    elif '1080' in url:
                        quality = '1080p'
                    elif '720' in url:
                        quality = 'HD'
                    elif '480' in url:
                        quality = 'SD'

                    # Finally, we use an else command. This tells the scraper that if it doesn't find any of the terms above then to just set the quality as 'SD'.

                    else:
                        quality = 'SD'

                    # Finally, we append all the information for the add-on to use as sources, like so:

                    sources.append({
                        'source': 'Direct',
                        # The host of the source, ie: Openload, GDrive, etc. This will often be scraped in the match command
                        'quality': quality,  # The quality (4K, 1080P, 720P, HD, SD, etc.)
                        'language': 'en',  # The language of the stream.
                        'url': url,  # The link to the stream.
                        # 'info': info,      # Additional info, such as filename. Not used in this example.
                        'direct': False,  # This will usually be set to False.
                        'debridonly': False
                        # If the source is only available to stream via a Debrid service, set this to True.
                    })
            except:
                return
        except Exception:
            return

        # Once everything above is complete, we tell it to return the sources, so that it can use them to stream.

        return sources

    def resolve(self, url):
        return url

# Congratulations, we are done. :)


# If you have any improvements or comments to make to this file, please comment where it was posted (Facebook, Reddit, whatever) and I will see it.