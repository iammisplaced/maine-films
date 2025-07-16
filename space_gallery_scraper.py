import requests
from bs4 import BeautifulSoup, Tag
import re
from datetime import datetime

SPACE_URL = "https://space538.org/events/?subcats=998"
VENUE = "SPACE Gallery"
VENUE_ID = "space"
CITY = "Portland"

def normalize_time_24h(time_str):
    if not time_str:
        return None
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
    return time_str

def scrape_space_gallery():
    SPACE_URL = "https://space538.org/events/?subcats=998"
    try:
        resp = requests.get(SPACE_URL, timeout=15)
        resp.raise_for_status()
    except requests.exceptions.RequestException as e:
        print(f"Failed to fetch SPACE Gallery: {e}")
        return []
    soup = BeautifulSoup(resp.text, "html.parser")
    films = []

    section = soup.find("section", class_="events-section")
    if not (section and isinstance(section, Tag)):
        return films

    for event in section.find_all("div", class_="related-block") if isinstance(section, Tag) else []:
        if not isinstance(event, Tag):
            continue
        a_tag = event.find("a", class_="related-link") if isinstance(event, Tag) else None
        film_url = ""
        if a_tag and isinstance(a_tag, Tag):
            film_url = str(a_tag.get("href", ""))
            if film_url and not film_url.startswith("http"):
                film_url = "https://space538.org" + film_url
        else:
            continue

        # Poster
        poster = ""
        img_div = a_tag.find("div", class_="center-cropped-image") if a_tag and isinstance(a_tag, Tag) else None
        if img_div and isinstance(img_div, Tag) and img_div.has_attr("style"):
            style_str = str(img_div["style"])
            m = re.search(r'url\((.*?)\)', style_str)
            if m:
                poster = m.group(1)

        # Title
        title_tag = a_tag.find("div", class_="event-title-grid") if a_tag and isinstance(a_tag, Tag) else None
        title = title_tag.get_text(strip=True) if title_tag and isinstance(title_tag, Tag) else None
        if not title:
            continue

        # --- Extract showtimes from event-info ---
        event_info = a_tag.find("div", class_="event-info") if a_tag and isinstance(a_tag, Tag) else None
        showtimes = []
        coming_soon = False
        if event_info and isinstance(event_info, Tag):
            date_tag = event_info.find("div", class_="event-date")
            date_str = date_tag.get_text(strip=True) if date_tag and isinstance(date_tag, Tag) else None

            time_tag = event_info.find("div", class_="event-time")
            times = []
            if time_tag and isinstance(time_tag, Tag):
                for t in re.split(r'[,&]', time_tag.get_text()):
                    t = t.strip()
                    if t:
                        times.append(t)

            if date_str and times:
                try:
                    date_part = re.sub(r'^[A-Za-z]+,?\s+', '', date_str)
                    if not re.search(r'\d{4}', date_part):
                        date_part += f" {datetime.now().year}"
                    dt_base = datetime.strptime(date_part, "%B %d %Y")
                    for t in times:
                        t24 = normalize_time_24h(t)
                        showtimes.append({
                            "date": dt_base.strftime("%Y-%m-%d"),
                            "time": t24,
                            "venue": VENUE,
                            "venue_id": VENUE_ID,
                            "city": CITY
                        })
                except Exception:
                    coming_soon = True
            else:
                coming_soon = True
        else:
            coming_soon = True

        if coming_soon:
            showtimes = [{
                "date": None,
                "time": None,
                "venue": VENUE,
                "venue_id": VENUE_ID,
                "city": CITY,
                "coming_soon": True
            }]

        films.append({
            "title": title,
            "showtimes": showtimes,
            "film_url": film_url,
            "poster": poster,
            "coming_soon": coming_soon
        })
    return films

if __name__ == "__main__":
    import json
    films = scrape_space_gallery()
    print(json.dumps(films, indent=2)) 