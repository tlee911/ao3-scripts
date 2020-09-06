import requests, urllib
from bs4 import BeautifulSoup

FANDOM = 'Warrior Nun (TV)'
MAX_PAGES = 2

def build_search_url(fandom, page=1):
  fandom_urlencode = urllib.parse.quote(fandom)
  base_url = 'https://archiveofourown.org/tags/{fandom}/works?page={page}'
  url = base_url.format(fandom=fandom_urlencode, page=page)
  return url

def get_work_data(work_dom):
  data = {}

  info = work_dom.find('div', 'header module').stripped_strings
  data['info'] = list(info)

  relationships = work_dom.find('li', 'relationships').stripped_strings
  raw_pairings = list(relationships)
  data['relationships'] = raw_pairings

  stats = iter(work_dom.find('dl', 'stats').stripped_strings)
  raw_stats = dict(zip(stats, stats))
  data['stats'] = raw_stats

  return data


if __name__ == '__main__':
  for i in range(MAX_PAGES):
    url = build_search_url(FANDOM, page=i+1)
    page = requests.get(url)
    search_dom = BeautifulSoup(page.content, 'html.parser')
    works_dom = search_dom.find_all('li', 'work blurb group')

    if not works_dom:
      break

    for work_dom in works_dom:
      data = get_work_data(work_dom)
      print(data)