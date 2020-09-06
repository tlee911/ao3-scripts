import requests, urllib
from bs4 import BeautifulSoup

FANDOM = 'Warrior Nun (TV)'
START_PAGE = 2
NUM_PAGES = 1

def print_dict(d, indent=2, depth=0):
  '''
  Pretty print a nested dictionary
  '''
  tab = lambda depth: indent * depth * ' '
  
  print(tab(depth) + '{')
  for key, value in d.items():
    if isinstance(value, dict):
      print(tab(depth+1) + key + ':')
      print_dict(value, indent, depth=depth+1)
    else:
      print('{0}{1}: {2}'.format(tab(depth+1), key, value))
  print(tab(depth) + '}')
  return

def build_search_url(fandom, page=1):
  fandom_urlencode = urllib.parse.quote(fandom)
  base_url = 'https://archiveofourown.org/tags/{fandom}/works?page={page}'
  url = base_url.format(fandom=fandom_urlencode, page=page)
  return url

def get_work_id(work_dom):
  work_id_str = work_dom.get_attribute_list('id')[0]
  work_id = work_id_str.split('_')[-1]
  return work_id

def get_work_byline(work_dom):
  info = work_dom.find('div', 'header module')
  byline = list(info.find('h4').stripped_strings)
  return {
    'Title': byline[0],
    'Author': byline[-1]
  }

def get_work_stats(work_dom):
  stats_strings = iter(work_dom.find('dl', 'stats').stripped_strings)
  print(list(stats_strings))
  raw_stats = dict(zip(stats_strings, stats_strings))

  stats = {}
  for key, value in raw_stats.items():
    normalized_key= key[:-1] if key.endswith(':') else key
    stats[normalized_key] = value
  
  #stats['Chapters Total'] = int(stats['Chapters'].split('/')[-1])
  #stats['Chapters Published'] = int(stats['Chapters'].split('/')[0])
  stats['Words'] = int(stats['Words'].replace(',', ''))
  return stats

def get_work_tags(work_dom):
  return {}

def get_work_data(work_dom):
  data = {}
  data['ID'] = get_work_id(work_dom)
  data.update(get_work_byline(work_dom))
  data.update(get_work_tags(work_dom))
  data.update(get_work_stats(work_dom))
  return data


if __name__ == '__main__':
  for i in range(START_PAGE, START_PAGE + NUM_PAGES):
    url = build_search_url(FANDOM, page=i)
    page = requests.get(url)
    search_dom = BeautifulSoup(page.content, 'html.parser')
    works_dom = search_dom.find_all('li', 'work blurb group')

    if not works_dom:
      break

    for work_dom in works_dom:
      data = get_work_data(work_dom)
      print_dict(data)
      break
