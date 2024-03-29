import calendar, csv, datetime, json, requests, time, urllib
from bs4 import BeautifulSoup

FANDOM = 'Warrior Nun (TV)'
START_PAGE = 62
END_PAGE = 70
PAUSE = 70 #seconds to wait in between batches to avoid rate-limits
OUTPUT_FILE = 'output/{fandom}_{date}.csv'.format(
  fandom=FANDOM, 
  date=datetime.datetime.isoformat(datetime.datetime.now())
)
FIELDS = [
  'ID',
  'Crossover',
  'Title',
  'Author',
  'Ship_1',
  'Ship_2',
  'Ship_3',
  'Char_1',
  'Char_2',
  'Char_3',
  'Char_4',
  'Rating',
  'Category',
  'Warnings',
  'Completion',
  'Language',
  'Words',
  'Published_Year',
  'Published_Month',
  'Published_Day',
  'Published_Date',
  'Updated_Year',
  'Updated_Month',
  'Updated_Day',
  'Updated_Date'
]

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
  base_url = 'https://archiveofourown.org/tags/{fandom}/works?commit=Sort+and+Filter&tos=yes&page={page}'
  url = base_url.format(fandom=fandom_urlencode, page=page)
  print('\n' + url)
  return url

def get_work_id(work_dom):
  work_id_str = work_dom.get_attribute_list('id')[0]
  work_id = work_id_str.split('_')[-1]
  return work_id

def get_work_fandoms(work_dom):
  raw_fandoms = work_dom.find('h5', 'fandoms heading').stripped_strings
  fandoms = filter(lambda x: x != ',', list(raw_fandoms)[1:])
  return list(fandoms)

def is_multi_fandom(work_dom):
  return True if len(get_work_fandoms(work_dom)) > 1 else False

def get_date_str(date_dict):
  date_str = '{yr}-{mth}-{day}'.format(
    yr=date_dict['Year'],
    mth=str(date_dict['Month']).zfill(2),
    day=str(date_dict['Day']).zfill(2)
  )
  return date_str

def get_work_updated(work_dom):
  # Note that this is the latest update date for multi-chapter works
  # We don't have the original publish date without viewing the work
  date = work_dom.find('p', 'datetime').get_text()
  (day, month, year) = tuple(date.split(' '))
  updated = {
    'Year': int(year),
    'Month': list(calendar.month_abbr).index(month.capitalize()),
    'Day': int(day)
  }
  updated['Date'] = get_date_str(updated)
  return {'Updated': updated}

def get_work_url(work_dom):
  work_url = 'https://archiveofourown.org/works/{id}'.format(id=get_work_id(work_dom))
  return work_url

def get_work_published(work_dom):
  # For multi-chapter works, we need to see the work details to get original
  # publish date
  stats = get_work_stats(work_dom)
  if stats['Chapters'] > 1:
    # Don't get rate limited by AO3
    work_url = get_work_url(work_dom)
    #print(work_url)
    res = requests.get(work_url, cookies={'view_adult':'true'})
    content = res.text
    detail_dom = BeautifulSoup(content, 'html.parser')
    publish_date_str = detail_dom.find('dd', 'published').getText()
    publish_date = publish_date_str.split('-')
    published = {
      'Year': int(publish_date[0]),
      'Month': int(publish_date[1]),
      'Day': int(publish_date[2]),
    }
    published['Date'] = get_date_str(published)
  else:
    published = get_work_updated(work_dom)['Updated']
  return {'Published': published}

def get_work_byline(work_dom):
  info = work_dom.find('div', 'header module')
  byline = list(info.find('h4').stripped_strings)
  return {
    'Title': byline[0],
    'Author': byline[2]
  }

def get_work_stats(work_dom):
  stats_dom = work_dom.find('dl', 'stats')
  # This is needed due to multi-chapter works
  dt = [ elem.get_text() for elem in stats_dom.find_all('dt') ]
  dd = [ elem.get_text() for elem in stats_dom.find_all('dd') ]
  raw_stats = dict(zip(dt, dd))

  stats = {}
  for key, value in raw_stats.items():
    normalized_key = key[:-1] if key.endswith(':') else key
    stats[normalized_key] = value
  
  # Can't coerce to int since throws if unknown chapter count "?"
  stats['Chapters Total'] = stats['Chapters'].split('/')[-1]
  stats['Chapters'] = int(stats['Chapters'].split('/')[0])

  words = stats['Words'].replace(',', '')
  try:
    stats['Words'] = int(words)
  except ValueError:
    # https://otwarchive.atlassian.net/browse/AO3-3498
    stats['Words'] = 0
  return stats

def get_work_symbols(work_dom):
  elements = work_dom.find_all(title='Symbols key')
  values = [ elem.get_text() for elem in elements ]
  # Order matters!
  keys = [
    'Rating',
    'Warnings',
    'Category',
    'Completion'
  ]
  symbols = dict(zip(keys, values))
  symbols['Warnings'] = [ s.strip() for s in symbols['Warnings'].split(',') ]
  return symbols

def get_work_tags(work_dom):
  tags_dom = work_dom.find('ul', 'tags commas')
  relationships = [ tag.get_text() for tag in tags_dom.find_all('li', 'relationships') ]
  characters = [ tag.get_text() for tag in tags_dom.find_all('li', 'characters') ]
  freeforms = [ tag.get_text() for tag in tags_dom.find_all('li', 'freeforms') ]
  return {
    'Relationships': relationships,
    'Characters': characters,
    'Freeforms': freeforms
  }

def get_work_data(work_dom):
  data = {
    'ID': get_work_id(work_dom),
    'Fandoms': get_work_fandoms(work_dom),
    'Crossover': is_multi_fandom(work_dom)
  }
  data.update(get_work_byline(work_dom))
  data.update(get_work_tags(work_dom))
  data.update(get_work_symbols(work_dom))
  data.update(get_work_stats(work_dom))
  data.update(get_work_updated(work_dom))
  data.update(get_work_published(work_dom))
  return data

def get_works(fandom, search_page):
  url = build_search_url(fandom, page=search_page)
  search = requests.get(url)
  content = search.text
  search_dom = BeautifulSoup(content, 'html.parser')
  works_dom = search_dom.find_all('li', 'work')
  return works_dom

if __name__ == '__main__':
  errors = []
  with open(OUTPUT_FILE, 'w', newline='') as output:
    writer = csv.DictWriter(output, fieldnames=FIELDS, extrasaction='ignore')
    writer.writeheader()

    step = 1 if END_PAGE > START_PAGE else -1
    search_pages = range(START_PAGE, END_PAGE, step)
    for i in search_pages:
      works = get_works(FANDOM, i)
      print('Retrieved {count} works from page {num}'.format(
        count=len(works),
        num=i)
      )

      if not works:
        print('Reached end of search results on page {num}'.format(num=i-1))
        break

      count = 1
      for work in works:
        print('#', end='', flush=True)
        try:
          data = get_work_data(work)
        except:
          work_url = get_work_url(work)
          print('Failed to extract data for {url}'.format(url=work_url))
          errors.append(work_url)
        
        # DEBUG STATEMENTS
        #print_dict(data)
        #print(json.dumps(data)) #write this to file then post-process to CSV

        ships = data.get('Relationships', [])
        for ship in ships:
          data['Ship_{num}'.format(num=ships.index(ship)+1)] = ship

        chars = data.get('Characters', [])
        for char in chars:
          data['Char_{num}'.format(num=chars.index(char)+1)] = char

        for date_type in ['Published', 'Updated']:
          for key in ['Year', 'Month', 'Day', 'Date']:
            data[date_type + '_' + key] = data.get(date_type, {}).get(key)

        #if data['Published_Date'] == None:
        #  data['Published_Date'] == data['Updated_Date']

        writer.writerow(data)
        count += 1
      
      if i != search_pages[-1]:
        # Don't bother waiting on the last batch
        print('\nWait {seconds}s between batches to avoid rate-limiting'.format(seconds=PAUSE))
        for j in range(0,PAUSE):
          if (j+1) % 10 == 0:
            print(j+1, end='', flush=True)
          else:
            print('.', end='', flush=True)
          time.sleep(1)

  print('\n')
