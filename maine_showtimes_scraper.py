import json
import time
from datetime import datetime, timedelta
from bs4 import BeautifulSoup, Tag
import requests
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from urllib.parse import urljoin
import re
from space_gallery_scraper import scrape_space_gallery
from eveningstar_scraper import get_eveningstar_showtimes
from strand_scraper import get_strand_showtimes
from mainefilmcenter_scraper import get_mainefilmcenter_showtimes
from nickelodeon_scraper import scrape_nickelodeon
from concurrent.futures import ThreadPoolExecutor
from kinonik_scraper import get_kinonik_showtimes
from bs4.element import Tag
from collections import defaultdict
from blackbear_scraper import scrape_blackbear
from colonial_scraper import scrape_colonial

TMDB_API_KEY = "2da147e5e6f08b12f071c89946f17de2"

def levenshtein(s1, s2):
    if len(s1) < len(s2):
        return levenshtein(s2, s1)
    if len(s2) == 0:
        return len(s1)
    previous_row = range(len(s2) + 1)
    for i, c1 in enumerate(s1):
        current_row = [i + 1]
        for j, c2 in enumerate(s2):
            insertions = previous_row[j + 1] + 1
            deletions = current_row[j] + 1
            substitutions = previous_row[j] + (c1 != c2)
            current_row.append(min(insertions, deletions, substitutions))
        previous_row = current_row
    return previous_row[-1]

def extract_year_and_description_from_zeffy(url):
    try:
        session = requests.Session()
        headers = {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36',
            'Referer': 'https://www.zeffy.com',
            'Cookie': '_dd_s=aid=81476ab3-2929-48c3-aea1-9d9993a6d9f7&logs=1&id=6f1e6735-c225-4602-9627-1a3e0eaeed2b&created=1752678634782&expire=1752684539628&rum=0; AMP_ef17265876=JTdCJTIyZGV2aWNlSWQlMjIlM0ElMjI3YzBhOWZhMy00MDNjLTRhODQtYmI2My0yMDc5MTUzMWQyYmIlMjIlMkMlMjJzZXNzaW9uSWQlMjIlM0ExNzQ4NTM4NTIxNDE4JTJDJTIyb3B0T3V0JTIyJTNBZmFsc2UlMkMlMjJsYXN0RXZlbnRUaW1lJTIyJTNBMTc0ODUzODUyMTcwOSUyQyUyMmxhc3RFdmVudElkJTIyJTNBMjMlMkMlMjJwYWdlQ291bnRlciUyMiUzQTAlN0Q=; AMP_MKTG_ef17265876=JTdCJTIycmVmZXJyZXIlMjIlM0ElMjJodHRwcyUzQSUyRiUyRnd3dy5raW5vbmlrLm9yZyUyRiUyMiUyQyUyMnJlZmVycmluZ19kb21haW4lMjIlM0ElMjJ3d3cua2lub25pay5vcmclMjIlN0Q=; __stripe_mid=4ec1a302-14d6-4cb1-87a6-bf2cf7761698af3a66; __stripe_sid=3c2ef51c-e648-47bb-ab64-ce51a8515a3916f2e8'
        }
        # First, visit the Kinonik homepage to establish cookies
        session.get('https://www.kinonik.org/', headers=headers, timeout=8)
        # Now, visit the Zeffy event page
        resp = session.get(url, headers=headers, timeout=8)
        soup = BeautifulSoup(resp.text, 'html.parser')
        # Only use the <meta property="og:description"> tag
        og_desc = ''
        meta = soup.find('meta', attrs={'property': 'og:description'})
        if meta and isinstance(meta, Tag):
            content = meta.get('content')
            if isinstance(content, str):
                og_desc = content
        # Look for a 4-digit year in og:description only
        import re
        year = None
        if og_desc:
            years = re.findall(r'(19\d{2}|20\d{2}|2100)', og_desc)
            for y in years:
                y_int = int(y)
                if 1900 <= y_int <= datetime.now().year:
                    year = y_int
                    break
        return year, og_desc
    except Exception as e:
        return None, ''

def get_tmdb_info(title, film=None):
    # Check for generic manual override
    film_overrides = {}
    try:
        with open('film_overrides.json', 'r', encoding='utf-8') as f:
            film_overrides = json.load(f)
    except Exception:
        pass
    # Normalize override keys for robust matching
    normalized_overrides = {normalize_title(k): v for k, v in film_overrides.items()}
    norm_title = normalize_title(title)
    override = normalized_overrides.get(norm_title)
    # Fuzzy match if no exact match
    if not override and normalized_overrides:
        min_dist = float('inf')
        best_key = None
        for k in normalized_overrides:
            dist = levenshtein(norm_title, k)
            if dist < min_dist:
                min_dist = dist
                best_key = k
        # Use a threshold of 2 for fuzzy match
        if best_key is not None and min_dist <= 2:
            override = normalized_overrides[best_key]
    venue_id = None
    if film:
        # Try to get the first venue_id from showtimes or film_urls
        if film.get('showtimes') and len(film['showtimes']) > 0:
            venue_id = film['showtimes'][0].get('venue_id')
        elif film.get('film_urls') and len(film['film_urls']) > 0:
            venue_id = next(iter(film['film_urls'].keys()))
    if override:
        venues = override.get('venues')
        if not venues or (venue_id and venue_id in venues):
            year = override.get('year')
            description = override.get('description', '')
            poster = override.get('poster', '')
            # Try TMDb with year if possible, else just use override description
            url = "https://api.themoviedb.org/3/search/movie"
            params = {
                "api_key": TMDB_API_KEY,
                "query": title,
                "include_adult": False,
                "language": "en-US"
            }
            if year:
                params['year'] = year
            resp = requests.get(url, params=params)
            data = resp.json()
            if data.get("results"):
                movie = data["results"][0]
                poster_path = movie.get("poster_path")
                poster_url = f"https://image.tmdb.org/t/p/w500{poster_path}" if poster_path else poster
                tmdb_desc = movie.get("overview", "")
                # Prefer override description if TMDb is empty
                return poster_url, tmdb_desc or description
            return poster, description
    # If this is a Kinonik film, try to extract year and og:description from Zeffy page
    year = None
    og_desc = ''
    if film and 'film_urls' in film and 'kinonik' in film['film_urls']:
        zeffy_url = film['film_urls']['kinonik']
        year, og_desc = extract_year_and_description_from_zeffy(zeffy_url)
        if not year:
            return '', og_desc or ''
    url = "https://api.themoviedb.org/3/search/movie"
    params = {
        "api_key": TMDB_API_KEY,
        "query": title,
        "include_adult": False,
        "language": "en-US"
    }
    if year:
        params['year'] = year
    resp = requests.get(url, params=params)
    data = resp.json()
    if data.get("results"):
        movie = data["results"][0]
        poster_path = movie.get("poster_path")
        poster_url = f"https://image.tmdb.org/t/p/w500{poster_path}" if poster_path else ""
        description = movie.get("overview", "")
        # If TMDb returns no description, use og:description as fallback
        if not description and og_desc:
            description = og_desc
        return poster_url, description
    return "", ""
    
def normalize_title(title):
    # Lowercase
    title = title.lower()
    # Replace parentheses with space and keep content
    title = re.sub(r'\(([^)]+)\)', r' \1 ', title)
    # Remove dashes, punctuation except alphanum and space
    title = re.sub(r'[^a-z0-9 ]', '', title)
    # Collapse multiple spaces
    title = re.sub(r'\s+', ' ', title).strip()
    return title

def normalize_time_24h(time_str):
    if not time_str:
        return None
    import re
    time_str = time_str.strip().lower().replace(' ', '')
    match = re.match(r'^(\d{1,2}):(\d{2})(am|pm)?$', time_str)
    if match:
        hour, minute, period = match.groups()
        hour = int(hour)
        minute = int(minute)
        if period == 'pm' and hour != 12:
            hour += 12
        if period == 'am' and hour == 12:
            hour = 0
        return f"{hour:02d}:{minute:02d}"
    # Already 24-hour or invalid, return as is
    return time_str

def merge_films_by_title(films1, films2):
    merged = {}
    for film in films1 + films2:
        key = normalize_title(film['title'])
        # Use film_urls dict if present, else fallback to film_url
        film_urls = film.get('film_urls', {})
        if not film_urls and 'film_url' in film:
            # Backward compatibility: single film_url
            venue_ids = set(st['venue_id'] for st in film['showtimes'])
            film_urls = {vid: film['film_url'] for vid in venue_ids if film.get('film_url')}
        if key not in merged:
            merged[key] = {
                "title": film["title"],
                "showtimes": film["showtimes"][:],
                "film_urls": dict(film_urls) if film_urls else {}
            }
        else:
            existing_showtimes = merged[key]["showtimes"]
            for st in film["showtimes"]:
                if st not in existing_showtimes:
                    existing_showtimes.append(st)
            # Merge film_urls dicts
            for vid, url in (film_urls or {}).items():
                if url and vid not in merged[key]["film_urls"]:
                    merged[key]["film_urls"][vid] = url
    return list(merged.values())

def main():
    # Load previous data for fallback
    try:
        with open("maine_showtimes.json", "r") as f:
            previous_data = json.load(f)
    except Exception:
        previous_data = []
    # Build mapping: venue_id -> list of films from previous data
    prev_films_by_venue = defaultdict(list)
    for film in previous_data:
        for st in film.get("showtimes", []):
            venue_id = st.get("venue_id")
            if venue_id:
                prev_films_by_venue[venue_id].append(film)
                break  # Only need to map each film once

    with ThreadPoolExecutor() as executor:
        future_nick = executor.submit(scrape_nickelodeon)
        future_eveningstar = executor.submit(get_eveningstar_showtimes)
        future_strand = executor.submit(get_strand_showtimes)
        future_mainefilmcenter = executor.submit(get_mainefilmcenter_showtimes)
        future_space = executor.submit(scrape_space_gallery)
        future_kinonik = executor.submit(get_kinonik_showtimes)
        future_blackbear = executor.submit(scrape_blackbear)
        future_colonial = executor.submit(scrape_colonial)

        print("Scraping Nickelodeon...")
        nickelodeon_results = future_nick.result()
        if not nickelodeon_results:
            nickelodeon_results = prev_films_by_venue.get("nickelodeon", [])
        print(f"Nickelodeon: {len(nickelodeon_results)} movies scraped.")
        print("Scraping Eveningstar...")
        eveningstar_results = future_eveningstar.result()
        if not eveningstar_results:
            eveningstar_results = prev_films_by_venue.get("eveningstar", [])
        print(f"Eveningstar: {len(eveningstar_results)} movies scraped.")
        print("Scraping Strand...")
        strand_results = future_strand.result()
        if not strand_results:
            strand_results = prev_films_by_venue.get("strand", [])
        print(f"Strand: {len(strand_results)} movies scraped.")
        print("Scraping Maine Film Center...")
        mainefilmcenter_results = future_mainefilmcenter.result()
        if not mainefilmcenter_results:
            mainefilmcenter_results = prev_films_by_venue.get("mainefilmcenter", [])
        print(f"Maine Film Center: {len(mainefilmcenter_results)} movies scraped.")
        print("Scraping SPACE Gallery...")
        space_results = future_space.result()
        if not space_results:
            space_results = prev_films_by_venue.get("space", [])
        print(f"SPACE Gallery: {len(space_results)} movies scraped.")
        print("Scraping Kinonik...")
        kinonik_results = future_kinonik.result()
        if not kinonik_results:
            kinonik_results = prev_films_by_venue.get("kinonik", [])
        print(f"Kinonik: {len(kinonik_results)} movies scraped.")
        print("Scraping Black Bear Cinemas...")
        blackbear_results = future_blackbear.result()
        if not blackbear_results:
            blackbear_results = prev_films_by_venue.get("blackbear", [])
        print(f"Black Bear Cinemas: {len(blackbear_results)} movies scraped.")
        print("Scraping Colonial Theatre...")
        colonial_results = future_colonial.result()
        if not colonial_results:
            colonial_results = prev_films_by_venue.get("colonial", [])
        print(f"Colonial Theatre: {len(colonial_results)} movies scraped.")

    all_showtimes = merge_films_by_title(
        nickelodeon_results,
        eveningstar_results + strand_results + mainefilmcenter_results + space_results + kinonik_results + blackbear_results + colonial_results
    )

    # Normalize all showtime times to 24-hour format
    for film in all_showtimes:
        for st in film.get('showtimes', []):
            st['time'] = normalize_time_24h(st.get('time'))

    print("Fetching posters and descriptions from TMDb...")
    for film in all_showtimes:
        poster, description = get_tmdb_info(film["title"], film)
        if not film.get("poster"):
            film["poster"] = poster
        if not film.get("description"):
            film["description"] = description
    total_showtimes = sum(len(f["showtimes"]) for f in all_showtimes)
    with open("maine_showtimes.json", "w") as f:
        json.dump(all_showtimes, f, indent=2)
    print(f"Combined {len(all_showtimes)} movies with {total_showtimes} showtimes saved to maine_showtimes.json")

if __name__ == "__main__":
    main()
