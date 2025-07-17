import requests
from bs4 import BeautifulSoup, Tag
import json
from datetime import datetime

MAIN_URL = "https://www.patriotcinemas.com/movie-theatres/maine/portland/nickelodeon-6"
AJAX_URL = "https://www.patriotcinemas.com/include/doShowtimesNew.php?starttime={date}"

headers = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept-Language": "en-US,en;q=0.9",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
    "Referer": "https://www.patriotcinemas.com/movie-theatres/maine/portland/nickelodeon-6",
}

cookies = {
    "siteID": "00001-00001-00003"
}

def get_date_info(div):
    day_name = div.find("span", class_="calNewDayName")
    day_number = div.find("span", class_="calNewDayNumber")
    if day_name and day_number:
        return f"{day_name.text.strip().upper()} {day_number.text.strip()}"
    return ""

def yyyymmdd_to_date(date_str):
    return datetime.strptime(date_str, "%Y%m%d").date()

now = datetime.now().date()

# Step 1: Get all available future dates from the main page
resp = requests.get(MAIN_URL, headers=headers, cookies=cookies)
# Log the raw HTML from the main page for debugging
with open("nickelodeon_raw_main.html", "w", encoding="utf-8") as f:
    f.write(resp.text)
soup = BeautifulSoup(resp.text, "html.parser")
date_divs = soup.find_all("div", class_="calNew")
dates = []
date_display_map = {}
for div in date_divs:
    if not isinstance(div, Tag):
        continue
    if div.has_attr("class") and "noPort" in div["class"]:
        continue
    onclick = div.get("onclick")
    if not isinstance(onclick, str):
        continue
    if "getST(" in onclick:
        date_val = onclick.split("getST(")[-1].split(")")[0]
        try:
            date_obj = yyyymmdd_to_date(date_val)
            if date_obj >= now:
                dates.append(date_val)
                date_display_map[date_val] = get_date_info(div)
        except Exception:
            continue
print(f"Collected {len(dates)} future dates: {dates}")

# Step 2: For each date, fetch and parse movies and showtimes
per_date_movies = {}
for date in dates:
    ajax_url = AJAX_URL.format(date=date)
    r = requests.get(ajax_url, headers=headers, cookies=cookies)
    # Log the raw JSON response from the AJAX endpoint for debugging
    with open(f"nickelodeon_raw_{date}.json", "w", encoding="utf-8") as f:
        f.write(r.text)
    data = r.json()
    html = data.get('html') or data.get('content') or next((v for v in data.values() if isinstance(v, str) and '<div' in v), "")
    if not html:
        print(f"No HTML for date {date}")
        continue
    # Optionally, log the HTML for each date
    with open(f"nickelodeon_html_{date}.html", "w", encoding="utf-8") as f:
        f.write(html)
    soup = BeautifulSoup(html, "html.parser")
    rows = soup.find_all("div", class_="row")
    date_str = date_display_map.get(date, date)
    print(f"Date {date_str}: Found {len(rows)} movies")
    for row in rows:
        if not isinstance(row, Tag):
            continue
        title_tag = row.find("span", class_="link listingTitle")
        if not title_tag:
            continue
        title = title_tag.get_text(strip=True)
        # Extract movie_url from onclick attribute
        movie_url = ""
        if isinstance(title_tag, Tag) and title_tag.has_attr("onclick"):
            onclick_val = title_tag["onclick"]
            if isinstance(onclick_val, str) and "location.href=" in onclick_val:
                parts = onclick_val.split("location.href=")[-1].split("'")
                if len(parts) > 1:
                    movie_url = parts[1]
                else:
                    movie_url = parts[0].strip("'; ")
        poster_tag = row.find("img")
        poster = poster_tag.get("src") if isinstance(poster_tag, Tag) else ""
        # Find description by style
        desc_div = None
        for div2 in row.find_all("span"):
            if not isinstance(div2, Tag):
                continue
            style = str(div2.get("style", ""))
            if "italic" in style:
                desc_div = div2
                break
        description = desc_div.get_text(strip=True) if desc_div else ""
        showtimes = []
        for st in row.find_all("div", class_="showtimeTicketGenAdmit showtimeTicket"):
            if not isinstance(st, Tag):
                continue
            showtimes.append(st.get_text(strip=True))
        showtime_objs = [{"date": date_str, "time": t} for t in showtimes]
        movie_key = (title, movie_url)
        if movie_key not in per_date_movies:
            per_date_movies[movie_key] = {
                "title": title,
                "movie_url": movie_url,
                "poster": poster,
                "description": description,
                "showtimes": showtime_objs,
                "venue": "Nickelodeon Cinemas",
                "venue_id": "nickelodeon",
                "city": "Portland"
            }
        else:
            existing = per_date_movies[movie_key]["showtimes"]
            for st in showtime_objs:
                if st not in existing:
                    existing.append(st)
    print(f"  Parsed {len(rows)} movies for {date_str}")

# Step 3: Output final merged list
films = list(per_date_movies.values())
total_showtimes = sum(len(f["showtimes"]) for f in films)
print(f"Final: {len(films)} movies with {total_showtimes} total showtimes.")

with open("nickelodeon_showtimes.json", "w") as f:
    json.dump(films, f, indent=2)

print(f"Scraped showtimes saved to nickelodeon_showtimes.json")
