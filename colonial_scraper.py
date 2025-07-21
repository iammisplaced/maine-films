import requests
import json
from datetime import datetime

def scrape_colonial():
    URL = "https://app.formovietickets.com/schedules/scheduleV1/L244286.json"
    VENUE = "Colonial Theatre"
    VENUE_ID = "colonial"
    CITY = "Belfast"
    COLONIAL_URL = "https://colonialtheatre.com"
    try:
        resp = requests.get(URL, timeout=10)
        data = resp.json()
    except Exception as e:
        print(f"Failed to fetch Colonial Theatre data: {e}")
        return []
    results = []
    for film in data.get("location", {}).get("Titles", []):
        title = film.get("title", "").strip()
        if title.startswith("LIVE SHOW:"):
            continue  # Omit live shows
        # Remove prefix before colon only for specific cases
        for prefix in ["NEW:", "INDIE FILM:", "INAUGURAL:"]:
            if title.startswith(prefix):
                title = title.split(":", 1)[1].strip()
                break
        description = film.get("synopsis", "") or ""
        poster = ""  # No poster in JSON; can be filled by aggregator
        film_urls = {VENUE_ID: COLONIAL_URL}
        showtimes = []
        for show in film.get("Shows", []):
            dt = show.get("time")
            if not dt:
                continue
            try:
                dt_obj = datetime.fromisoformat(dt)
                date_str = dt_obj.strftime("%Y-%m-%d")
                time_str = dt_obj.strftime("%H:%M")
            except Exception:
                # fallback: split T
                if "T" in dt:
                    date_str, time_str = dt.split("T")
                    time_str = time_str[:5]
                else:
                    date_str, time_str = dt, ""
            showtimes.append({
                "date": date_str,
                "time": time_str,
                "venue": VENUE,
                "venue_id": VENUE_ID,
                "city": CITY
            })
        results.append({
            "title": title,
            "showtimes": showtimes,
            "film_urls": film_urls,
            "poster": poster,
            "description": description
        })
    return results

if __name__ == "__main__":
    films = scrape_colonial()
    with open("colonial_showtimes.json", "w") as f:
        json.dump(films, f, indent=2)
    print(f"Wrote {len(films)} films to colonial_showtimes.json") 