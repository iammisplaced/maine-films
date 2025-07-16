import requests
from bs4 import BeautifulSoup, Tag
import re
from datetime import datetime
from urllib.parse import urljoin

KINONIK_URL = "https://www.kinonik.org/"
VENUE = "Kinonik"
VENUE_ID = "kinonik"
CITY = "Portland"
FALLBACK_POSTER = "/no-poster.png"

# Helper to parse date(s) from strings like 'ON 7/16 AT |KINONIK|' or 'ON 9/3 and 9/6 AT |Kinonik|'
def extract_dates(date_str):
    # e.g. 'ON 9/3 and 9/6 AT |Kinonik|'
    date_str = date_str.strip()
    m = re.search(r'ON (.+?) AT', date_str, re.IGNORECASE)
    if not m:
        return []
    dates_part = m.group(1)
    # Split on 'and' and ','
    date_tokens = re.split(r'and|,', dates_part)
    # Try to parse each date as MM/DD
    dates = []
    this_year = datetime.now().year
    for token in date_tokens:
        token = token.strip()
        m2 = re.match(r'(\d{1,2})/(\d{1,2})', token)
        if m2:
            month, day = int(m2.group(1)), int(m2.group(2))
            try:
                dt = datetime(this_year, month, day)
                dates.append(dt.strftime('%Y-%m-%d'))
            except Exception:
                continue
    return dates

def extract_title_and_dates(text):
    # Try to match 'TITLE ON [dates] AT'
    m = re.match(r'(.+?)\s+ON\s+(.+?)\s+AT', text, re.IGNORECASE)
    if m:
        title = m.group(1).strip()
        dates_part = m.group(2).strip()
    else:
        # Try to match 'TITLE [dates] AT'
        m2 = re.match(r'(.+?)\s+((?:\d{1,2}/\d{1,2}(?:\s*(?:and|,)\s*)?)+)\s+AT', text, re.IGNORECASE)
        if m2:
            title = m2.group(1).strip()
            dates_part = m2.group(2).strip()
        else:
            # Fallback: treat everything before 'AT' as title, no dates
            at_idx = text.upper().find(' AT')
            title = text[:at_idx].strip() if at_idx != -1 else text.strip()
            dates_part = ''
    # Split on 'and' and ','
    date_tokens = re.split(r'and|,', dates_part)
    # Try to parse each date as MM/DD
    parsed_dates = []
    for token in date_tokens:
        token = token.strip()
        if re.match(r'\d{1,2}/\d{1,2}', token):
            # Assume current year
            try:
                dt = datetime.strptime(f'{datetime.now().year}/{token}', '%Y/%m/%d')
                parsed_dates.append(dt.strftime('%Y-%m-%d'))
            except Exception:
                continue
    return title, parsed_dates

def slugify_title(title):
    # Remove special characters, replace spaces with hyphens, lowercase
    import re
    slug = re.sub(r'[^a-zA-Z0-9 ]', '', title)
    slug = slug.lower().strip().replace(' ', '-')
    return slug

def get_kinonik_showtimes():
    resp = requests.get(KINONIK_URL)
    resp.raise_for_status()
    soup = BeautifulSoup(resp.text, "html.parser")
    films = []
    upcoming_div = soup.find('div', id='upcoming-films-list')
    if not upcoming_div or not isinstance(upcoming_div, Tag):
        return films
    for a in upcoming_div.select('ul li a'):
        if not isinstance(a, Tag):
            continue
        text = a.get_text(strip=True)
        # Extract title and date(s) robustly
        title, dates = extract_title_and_dates(text)
        showtimes = []
        for date in dates:
            showtimes.append({
                'date': date,
                'time': '19:00',  # Assume 7:00pm for all showtimes
                'venue': VENUE,
                'venue_id': VENUE_ID,
                'city': CITY,
                'coming_soon': False
            })
        # If no dates found, mark as coming soon
        if not showtimes:
            showtimes.append({
                'date': '',
                'time': '',
                'venue': VENUE,
                'venue_id': VENUE_ID,
                'city': CITY,
                'coming_soon': True
            })
        # Use the actual href from the <a> tag
        href = a.get('href', '')
        if isinstance(href, str) and href and not href.startswith('http'):
            href = urljoin(KINONIK_URL, href)
        film_urls = {VENUE_ID: href} if isinstance(href, str) and href else {}
        films.append({
            'title': title,
            'poster': FALLBACK_POSTER,
            'description': '',
            'showtimes': showtimes,
            'film_urls': film_urls
        })
    return films

if __name__ == "__main__":
    import json
    print(json.dumps(get_kinonik_showtimes(), indent=2)) 