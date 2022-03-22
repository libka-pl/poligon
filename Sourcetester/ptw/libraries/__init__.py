try:
    from ptw.libraries import cfscrape

    cfScraper = cfscrape.create_scraper()
except:
    pass

try:
    from kodi_six import xbmcaddon

    __addon__ = xbmcaddon.Addon(id="script.module.ptw")
except:
    __addon__ = None
    pass


def enabledCheck(module_name):
    if __addon__ is not None:
        if __addon__.getSetting("provider." + module_name) == "true":
            return True
        else:
            return False
    return True


def custom_base_link(scraper):
    try:
        url = __addon__.getSetting("url." + scraper)
        if url and url.startswith("http"):
            if url.endswith("/"):
                url = url[:-1]
            return url
        else:
            return None
    except:
        return None
