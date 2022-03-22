import importlib
import pprint
import re
import time
from zrodla import resolvers
pp = pprint.PrettyPrinter(indent=2)
hostDict = resolvers.hosts
hostprDict = resolvers.hostspr

'''
plik żródła do folderu zrodla
nazwa testowanego źródła 
bez .py
'''

tested_source = 'external'

# show peaky blinders
#meta = {'imdb': 'tt2442560', 'tvdb': 'None', 'tvshowtitle': 'Peaky Blinders', 'localtvshowtitle': 'Peaky Blinders', 'aliases': [{'country': 'us', 'title': 'Peaky Blinders'}], 'year': '2013', 'title': 'Odcinek 3', 'premiered': '2014-10-16', 'season': '2', 'episode': '3'}
#  Show   Witcher
#meta = { 'imdb': 'tt5180504', 'tvdb':'None', 'tvshowtitle': 'The Witcher', 'localtvshowtitle': 'Wiedźmin', 'aliases': [{'country': 'us', 'title': 'The Witcher'}], 'year': '2013', 'title': 'Księżyc zdrajcy', 'premiered': '2019-12-20', 'season': '2', 'episode': '3'}
#meta = { 'imdb': 'tt5180504', 'tvdb':'None', 'tvshowtitle': 'Behaviorist', 'localtvshowtitle': 'Behawiorysta', 'aliases': [{'country': 'us', 'title': 'The Witcher'}], 'year': '2013', 'title': 'Księżyc zdrajcy', 'premiered': '2019-12-20', 'season': '1', 'episode': '3'}

#movie dict Shang shi
#meta = {'imdb': 'tt9376612', 'title':  'Shang-Chi and the Legend of the Ten Rings', 'localtitle': 'Shang-Chi i legenda dziesięciu pierścieni', 'aliases': [{'title': 'Shang-Chi and the Legend of the Ten Rings', 'country': 'us'}, {'title': 'Steamboat', 'country': 'us'}], 'year': '2021'}
#movie dict  tenet
#meta = {'imdb': 'tt6723592', 'title':  'Tenet', 'localtitle': 'Tenet', 'aliases': [{'title': 'Merry-Go-Round', 'country': 'us'}, {'title': 'i ordered my hot sauce an hour ago', 'country': 'us'}], 'year': '2020'}
#movie Lord of the rings
#meta = {'imdb': 'tt0120737', 'title': 'The Lord of the Rings: The Fellowship of the Ring', 'localtitle': 'Władca Pierścieni: Drużyna Pierścienia', 'aliases': [{'title': 'Lord of The Rings I - The Fellowship of The Ring', 'country': 'us'}, {'title': 'The Lord of the Rings 1 - The Fellowship of the Ring', 'country': 'us'}, {'title': 'The Lord of the Rings - The Fellowship of the Ring', 'country': 'us'}, {'title': 'TLOTR The Fellowship of the Ring', 'country': 'us'}, {'title': 'LOTR', 'country': 'us'}, {'title': 'The Lord of the Rings 1 - The Fellowship of the Ring - Extended Edition', 'country': 'us'}, {'title': 'The Lord of the Rings I - The Fellowship of the Ring - Extended Edition', 'country': 'us'}, {'title': 'Lord of the Rings I - The Fellowship of the Ring - Extended Edition', 'country': 'us'}, {'title': 'Lord of the Rings 1 - The Fellowship of the Ring - Extended Edition', 'country': 'us'}, {'title': 'Druzyna Pierscienia Dysk 2', 'country': 'pl'}, {'title': 'The Lord of the Rings - The Fellowship of the Ring (Special Extended Edition)', 'country': 'us'}, {'title': 'Lord of the Rings 1 - The Fellowship of the Ring - Extended Edition Part 2', 'country': 'us'}, {'title': 'The Lord of the Rings The Fellowship of the Ring disc-1', 'country': 'us'}, {'title': 'The Lord of the Rings The Fellowship of the Ring disc-2', 'country': 'us'}, {'title': 'El Señor de los Anillos 1', 'country': 'us'}, {'title': 'Lord of the Rings, the 01 Lord of the Rings the Fellowship of the Ring, The', 'country': 'us'}, {'title': 'The  Lord of the Rings: The Fellowship of the Ring (Theatrical Edition)', 'country': 'us'}, {'title': 'TLOTR The Fellowship of the Ring  - Extended edition', 'country': 'us'}, {'title': 'The Lord of the Rings Extended Edition - The Fellowship of the Ring 2001', 'country': 'us'}, {'title': 'The Lord of the Rings Extended Edition 1 - The Fellowship of the Ring 2001', 'country': 'us'}, {'title': 'TLOR The Fellowship of the Ring - Part 1', 'country': 'us'}, {'title': 'TLOR The Fellowship of the Ring - Part 2', 'country': 'us'}, {'title': 'The Fellowship of the Ring', 'country': 'us'}, {'title': 'LOTR The Fellowship of the ring', 'country': 'us'}, {'title': 'The Lord of the Rings 1：The Fellowship of the Ring', 'country': 'us'}], 'year': '2001'}
# movie diune
#meta = {'imdb': 'tt1160419', 'title':  'Dune', 'localtitle': 'Diuna', 'aliases': [{'title': 'Merry-Go-Round', 'country': 'us'}, {'title': 'i ordered my hot sauce an hour ago', 'country': 'us'}], 'year': '2021'}
# movie thor ragnarok
#meta = {'imdb': 'tt3501632', 'title':  'Thor: Ragnarok', 'localtitle': 'Thor: Ragnarok', 'aliases': [{'title': 'Merry-Go-Round', 'country': 'us'}, {'title': 'i ordered my hot sauce an hour ago', 'country': 'us'}], 'year': '2017'}
# movie spider-man no way home
meta = {'imdb': 'tt10872600', 'title':  'Spider-Man: No Way Home', 'localtitle': 'Spider-Man: Bez drogi do domu', 'aliases': [{'title': 'Merry-Go-Round', 'country': 'us'}, {'title': 'i ordered my hot sauce an hour ago', 'country': 'us'}], 'year': '2021'}



tested_source = 'zrodla.' + tested_source
mod = importlib.import_module(tested_source)
module = mod.source()

start = time.time()
if 'tvshowtitle' in meta:
     urls = module.tvshow(meta['imdb'], meta['tvdb'], meta['tvshowtitle'], meta['localtvshowtitle'], meta['aliases'], meta['year'])
     url = module.episode(urls, meta['imdb'], meta['tvdb'], meta['title'], meta['premiered'], meta['season'], meta['episode'])
else:
    url = module.movie(meta['imdb'], meta['title'], meta['localtitle'], meta['aliases'], meta['year'])


sources_list = (module.sources(url, hostDict=hostDict, hostprDict=hostprDict))
stop = time.time()





pp.pprint(sources_list)

print(stop-start)

fire_up = module.resolve(sources_list[0]['url'])
print('dupa')

