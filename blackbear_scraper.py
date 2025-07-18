import requests
from bs4 import BeautifulSoup, Tag
from datetime import datetime
import json
import re

MAIN_URL = "https://www.blackbearcinemas.com/ViewByDay"
AJAX_URL = "https://www.blackbearcinemas.com/include/doShowtimesNew.php?starttime={date}"

headers = {
    "accept": "application/json, text/javascript, */*; q=0.01",
    "accept-language": "en-US,en;q=0.9",
    "referer": "https://www.blackbearcinemas.com/",
    "user-agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/138.0.0.0 Safari/537.36",
    "x-requested-with": "XMLHttpRequest"
}
cookies = {
    "hasSeenPopup": "yes",
    "acceptCookies": "user%20has%20ackn.%20cookie%20policy",
    "listView": "list",
    "siteID": "00001-00001-00001"
}

def slugify(title):
    slug = title.lower()
    slug = re.sub(r'[^a-z0-9\s-]', '', slug)
    slug = re.sub(r'\s+', '-', slug)
    slug = re.sub(r'-+', '-', slug)
    slug = slug.strip('-')
    return slug

def scrape_blackbear():
    session = requests.Session()
    session.headers.update(headers)
    resp = session.get(MAIN_URL, cookies=cookies)
    soup = BeautifulSoup(resp.text, "html.parser")
    date_divs = soup.find_all("div", class_="calNew")
    dates = []
    for div in date_divs:
        if not isinstance(div, Tag):
            continue
        class_list = div.get("class")
        if not isinstance(class_list, list):
            class_list = []
        onclick = div.get("onclick")
        date_val = None
        if isinstance(onclick, str) and "getST(" in onclick:
            date_val = onclick.split("getST(")[-1].split(")")[0].strip("'\"")
        if date_val:
            try:
                datetime.strptime(date_val, "%Y%m%d")
                dates.append(date_val)
            except Exception:
                continue
    all_movies = {}
    for date in dates:
        url = AJAX_URL.format(date=date)
        r = session.get(url, cookies=cookies)
        try:
            data = r.json()
        except Exception:
            continue
        listings_html = data.get('listings', '')
        soup = BeautifulSoup(listings_html, "html.parser")
        for row in soup.find_all("div", class_="row"):
            if not isinstance(row, Tag):
                continue
            title_tag = row.find("span", class_="link listingTitle") if isinstance(row, Tag) else None
            if not (title_tag and isinstance(title_tag, Tag)):
                continue
            title = title_tag.get_text(strip=True)
            # Poster
            poster = None
            poster_tag = row.find("img") if isinstance(row, Tag) else None
            if poster_tag and isinstance(poster_tag, Tag) and poster_tag.has_attr("src"):
                poster = poster_tag["src"]
            # Description
            desc_tag = None
            for div2 in row.find_all("div") if isinstance(row, Tag) else []:
                if isinstance(div2, Tag):
                    style = div2.get("style", "")
                    if "font-size: 20px;" in str(style):
                        desc_tag = div2
                        break
            description = desc_tag.get_text(strip=True) if desc_tag else ""
            # Showtimes
            showtimes = []
            for st in row.find_all("div", class_="showtimeTicketGenAdmit showtimeTicket") if isinstance(row, Tag) else []:
                if not isinstance(st, Tag):
                    continue
                time_str = st.get_text(strip=True)
                showtimes.append({
                    "date": datetime.strptime(date, "%Y%m%d").strftime("%Y-%m-%d"),
                    "time": time_str,
                    "venue": "Black Bear Cinemas",
                    "venue_id": "blackbear",
                    "city": "Orono"
                })
            # Film URL
            slug = slugify(title)
            film_url = f"https://www.blackbearcinemas.com/movie/{slug}" if slug else None
            # Merge showtimes for the same movie
            key = title.strip().lower()
            if key in all_movies:
                all_movies[key]["showtimes"].extend(showtimes)
            else:
                all_movies[key] = {
                    "title": title,
                    "poster": poster,
                    "description": description,
                    "showtimes": showtimes,
                    "film_urls": {"blackbear": film_url} if film_url else {}
                }
    return list(all_movies.values())

if __name__ == "__main__":
    films = scrape_blackbear()
    print(json.dumps(films, indent=2)) 