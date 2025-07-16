import requests
from bs4 import BeautifulSoup, Tag
from datetime import datetime, timedelta

def scrape_nickelodeon():
    MAIN_URL = "https://www.patriotcinemas.com/movie-theatres/maine/portland/nickelodeon-6"
    AJAX_URL = "https://www.patriotcinemas.com/include/doShowtimesNew.php?starttime={date}"
    headers = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept-Language": "en-US,en;q=0.9",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
        "Referer": MAIN_URL,
    }
    cookies = {
        "siteID": "00001-00001-00003"
    }
    def yyyymmdd_to_yyyy_mm_dd(date_str):
        return datetime.strptime(date_str, "%Y%m%d").strftime("%Y-%m-%d")
    def normalize_time(t):
        t = t.strip().lower().replace(' ', '')
        import re
        match = re.match(r'^(\d{1,2}):(\d{2})(a|am|p|pm)?$', t)
        if match:
            hour, minute, period = match.groups()
            hour = int(hour)
            minute = int(minute)
            if period in ('p', 'pm') and hour != 12:
                hour += 12
            if period in ('a', 'am') and hour == 12:
                hour = 0
            return f"{hour:02d}:{minute:02d}"
        try:
            dt = datetime.strptime(t, "%H:%M")
            return dt.strftime("%H:%M")
        except Exception:
            return t
    def slugify(title):
        import re
        slug = title.lower()
        slug = re.sub(r'[^a-z0-9\s-]', '', slug)  # remove non-alphanumeric except space and hyphen
        slug = re.sub(r'\s+', '-', slug)  # replace spaces with hyphens
        slug = re.sub(r'-+', '-', slug)  # collapse multiple hyphens
        slug = slug.strip('-')
        return slug
    today = datetime.now().date()
    num_days = 30
    dates = [(today + timedelta(days=i)).strftime("%Y%m%d") for i in range(num_days)]
    per_date_movies = {}
    for date in dates:
        ajax_url = AJAX_URL.format(date=date)
        r = requests.get(ajax_url, headers=headers, cookies=cookies)
        try:
            data = r.json()
        except Exception:
            continue
        html = data.get('html') or data.get('content') or next((v for v in data.values() if isinstance(v, str) and '<div' in v), "")
        if not html:
            continue
        soup = BeautifulSoup(html, "html.parser")
        rows = soup.find_all("div", class_="row")
        date_str = yyyymmdd_to_yyyy_mm_dd(date)
        for row in rows:
            if not isinstance(row, Tag):
                continue
            title_tag = row.find("span", class_="link listingTitle")
            if not title_tag:
                continue
            title = title_tag.get_text(strip=True)
            # Construct the correct film_url
            slug = slugify(title)
            movie_url = f"https://patriotcinemas.com/movie/{slug}" if slug else ""
            showtimes = []
            for st in row.find_all("div", class_="showtimeTicketGenAdmit showtimeTicket"):
                if not isinstance(st, Tag):
                    continue
                showtimes.append(normalize_time(st.get_text(strip=True)))
            showtime_objs = [{
                "date": date_str,
                "time": t,
                "venue": "Nickelodeon Cinemas",
                "venue_id": "nickelodeon",
                "city": "Portland"
            } for t in showtimes]
            movie_key = (title, movie_url)
            if movie_key not in per_date_movies:
                per_date_movies[movie_key] = {
                    "title": title,
                    "showtimes": showtime_objs,
                    "film_url": movie_url or ""
                }
            else:
                existing = per_date_movies[movie_key]["showtimes"]
                for st in showtime_objs:
                    if st not in existing:
                        existing.append(st)
    return list(per_date_movies.values())

if __name__ == "__main__":
    import json
    films = scrape_nickelodeon()
    print(json.dumps(films, indent=2)) 