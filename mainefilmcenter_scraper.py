import re
from bs4 import BeautifulSoup, Tag
import requests

def normalize_title(title):
    title = title.lower()
    title = re.sub(r'\(([^)]+)\)', r' \1 ', title)
    title = re.sub(r'[^a-z0-9 ]', '', title)
    title = re.sub(r'\s+', ' ', title).strip()
    return title

def get_mainefilmcenter_showtimes():
    MAIN_URL = "https://www.watervillecreates.org/mainefilmcenter/home"
    VENUE = "Maine Film Center"
    VENUE_ID = "mainefilmcenter"
    CITY = "Waterville"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }
    resp = requests.get(MAIN_URL, headers=headers)
    resp.raise_for_status()
    soup = BeautifulSoup(resp.text, "html.parser")
    films_by_title = {}
    # --- Now Showing Section ---
    for tab in soup.find_all('div', class_='tab-pane'):
        if not isinstance(tab, Tag):
            continue
        date_header = tab.find(name=re.compile(r'^h[2-4]$'))
        if date_header and isinstance(date_header, Tag):
            date_str = date_header.get_text(strip=True)
            try:
                from dateutil import parser as dtparser
                date_obj = dtparser.parse(date_str)
                show_date = date_obj.strftime('%Y-%m-%d')
            except Exception:
                continue
        else:
            continue
        for film_div in tab.find_all('div', class_='event span-3'):
            if not isinstance(film_div, Tag):
                continue
            film_title_tag = film_div.find(name=re.compile(r'^h[3-4]$'))
            film_title = film_title_tag.get_text(strip=True) if film_title_tag and isinstance(film_title_tag, Tag) else None
            if not film_title:
                continue
            showtimes = []
            for time_tag in film_div.find_all(string=re.compile(r'\d{1,2}:\d{2}(am|pm)', re.I)):
                if isinstance(time_tag, str):
                    showtimes.append(time_tag.strip())
            film_url = ""
            more_info_link = film_div.find('a', string=re.compile(r'More Info', re.I))
            if not more_info_link:
                more_info_link = film_div.find('a')
            if more_info_link and isinstance(more_info_link, Tag):
                href_val = more_info_link.get('href', '')
                if href_val and not str(href_val).startswith('http'):
                    film_url = 'https://www.watervillecreates.org' + str(href_val)
                else:
                    film_url = str(href_val)
            key = film_title.strip().lower()
            showtime_objs = [{
                'date': show_date,
                'time': t,
                'venue': VENUE,
                'venue_id': VENUE_ID,
                'city': CITY,
                'coming_soon': False
            } for t in showtimes]
            if key not in films_by_title:
                films_by_title[key] = {
                    'title': film_title,
                    'showtimes': showtime_objs,
                    'film_url': film_url,
                    'coming_soon': False
                }
            else:
                films_by_title[key]['showtimes'].extend(showtime_objs)
                if not films_by_title[key].get('film_url') and film_url:
                    films_by_title[key]['film_url'] = film_url
    # --- Coming Soon Section ---
    coming_soon_grid = soup.find('div', id='shows-grid-4')
    if coming_soon_grid and isinstance(coming_soon_grid, Tag):
        for show_div in coming_soon_grid.find_all('div', class_=lambda c: isinstance(c, str) and c.split()[0] == 'single-show'):
            if not isinstance(show_div, Tag):
                continue
            title_tag = show_div.find(['h3', 'h4'])
            film_title = title_tag.get_text(strip=True) if title_tag else None
            if not film_title:
                continue
            key = normalize_title(film_title)
            if key in films_by_title:
                continue
            show_date = None
            date_text = show_div.get_text()
            date_match = re.search(r'(Opening|Returning|at|on)\s+([A-Za-z]+\s+\d{1,2}(,\s*\d{4})?)', date_text, re.I)
            if date_match:
                date_str = date_match.group(2)
                try:
                    from dateutil import parser as dtparser
                    date_obj = dtparser.parse(date_str)
                    show_date = date_obj.strftime('%Y-%m-%d')
                except Exception:
                    pass
            film_url = ""
            link_tag = show_div.find('a')
            if link_tag and isinstance(link_tag, Tag):
                href_val = link_tag.get('href', '')
                if href_val and not str(href_val).startswith('http'):
                    film_url = 'https://www.watervillecreates.org' + str(href_val)
                else:
                    film_url = str(href_val)
            showtime_objs = []
            if show_date:
                showtime_objs.append({
                    'date': show_date,
                    'time': None,
                    'venue': VENUE,
                    'venue_id': VENUE_ID,
                    'city': CITY,
                    'coming_soon': True
                })
            films_by_title[key] = {
                'title': film_title,
                'showtimes': showtime_objs,
                'film_url': film_url,
                'coming_soon': True
            }
    return list(films_by_title.values()) 