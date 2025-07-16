import requests
import time
from bs4 import BeautifulSoup
from bs4.element import Tag
from datetime import datetime, timedelta

def get_eveningstar_showtimes():
    BASE_URL = "https://www.eveningstarcinema.com"
    MOVIES_URL = f"{BASE_URL}/movies/"
    # Step 1: Scrape movie IDs and titles
    resp = requests.get(MOVIES_URL)
    resp.raise_for_status()
    soup = BeautifulSoup(resp.text, "html.parser")
    movie_id_map = {}
    for a in soup.find_all("a", href=True):
        if not isinstance(a, Tag):
            continue
        href = a.get("href")
        if not isinstance(href, str):
            continue
        if href.startswith("/movies/") and '-' in href:
            try:
                movie_id = href.split("/movies/")[1].split("-")[0]
            except Exception:
                continue
            movie_url = BASE_URL + href
            try:
                movie_resp = requests.get(movie_url)
                movie_resp.raise_for_status()
                movie_soup = BeautifulSoup(movie_resp.text, "html.parser")
                h1 = movie_soup.find("h1")
                title = h1.text.strip() if h1 else None
                if title:
                    movie_id_map[movie_id] = {"title": title, "film_url": movie_url}
                time.sleep(0.5)
            except Exception as e:
                print(f"Failed to fetch {movie_url}: {e}")
    # Step 2: Fetch showtimes from API
    schedule_url = "https://www.eveningstarcinema.com/api/gatsby-source-boxofficeapi/schedule"
    headers = {
        "User-Agent": "Mozilla/5.0 (compatible; MSIE 10.0; Windows NT 6.1; Trident/6.0)",
        "Accept": "application/json",
        "Content-Type": "application/json"
    }
    today = datetime.now()
    from_date = today.strftime("%Y-%m-%dT03:00:00")
    to_date = (today + timedelta(days=365)).strftime("%Y-%m-%dT03:00:00")
    payload = {
        "circuit": None,
        "theaters": [{"id": "X020R", "timeZone": "America/New_York"}],
        "movieIds": list(movie_id_map.keys()),
        "from": from_date,
        "to": to_date,
        "websiteId": "V2Vic2l0ZU1hbmFnZXJXZWJzaXRlOmU5M2Y3NDcxLTA0NzktNGRhYS04NTYyLTY2YmQxODc4OTA5Yw==",
        "nin": [],
        "sin": []
    }
    # Retry logic for POST
    def fetch_with_retry_post(url, payload, headers, retries=3, delay=2):
        for attempt in range(retries):
            try:
                resp = requests.post(url, headers=headers, json=payload)
                resp.raise_for_status()
                return resp
            except requests.exceptions.HTTPError as e:
                print(f"Attempt {attempt+1} to fetch {url} failed: {e}")
                if attempt < retries - 1:
                    time.sleep(delay)
                else:
                    print(f"All {retries} attempts to fetch {url} failed.")
                    return None
    resp = fetch_with_retry_post(schedule_url, payload, headers)
    if resp is None:
        print("Could not retrieve schedule data. Exiting.")
        return []
    schedule_data = resp.json()
    films = []
    found_movie_ids = set()
    for venue_id, venue_data in schedule_data.items():
        schedule = venue_data.get("schedule", {})
        for movie_id, dates in schedule.items():
            if movie_id not in movie_id_map:
                continue
            found_movie_ids.add(movie_id)
            showtimes = []
            for date, showings in dates.items():
                for showing in showings:
                    starts_at = showing.get("startsAt")
                    if starts_at:
                        try:
                            dt = datetime.fromisoformat(starts_at)
                            show_date = dt.strftime("%Y-%m-%d")
                            show_time = dt.strftime("%H:%M")
                        except Exception:
                            show_date = date
                            show_time = None
                    else:
                        show_date = date
                        show_time = None
                    showtime = {
                        "date": show_date,
                        "time": show_time,
                        "venue": "Eveningstar Cinema",
                        "venue_id": venue_id,
                        "city": "Brunswick"
                    }
                    showtimes.append(showtime)
            films.append({
                "title": movie_id_map[movie_id]["title"],
                "showtimes": showtimes,
                "film_url": movie_id_map[movie_id].get("film_url", "")
            })
    # Add coming soon films (no showtimes)
    for movie_id, info in movie_id_map.items():
        if movie_id not in found_movie_ids:
            films.append({
                "title": info["title"],
                "showtimes": [{
                    "date": None,
                    "time": None,
                    "venue": "Eveningstar Cinema",
                    "venue_id": "X020R",
                    "city": "Brunswick",
                    "coming_soon": True
                }],
                "film_url": info.get("film_url", "")
            })
    return films 