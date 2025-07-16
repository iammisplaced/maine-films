import json
import time
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from bs4 import BeautifulSoup
from urllib.parse import urljoin
from bs4 import Tag
import re

BASE_URL = "https://www.eveningstarcinema.com"
MOVIES_URL = f"{BASE_URL}/movies/"

options = Options()
options.add_argument("--headless")
driver = webdriver.Chrome(options=options)

# STEP 1: Get all movie links from the "All Movies" page
driver.get(MOVIES_URL)
WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.TAG_NAME, "a")))
soup = BeautifulSoup(driver.page_source, "html.parser")

movie_links = set()
for a in soup.find_all("a", href=True):
    if isinstance(a, Tag):
        href = a.get("href")
        if href and isinstance(href, str) and "/movies/" in href and href != "/movies/":
            full_url = urljoin(BASE_URL, href)
            movie_links.add(full_url)

print(f"Found {len(movie_links)} movie links.")

results = []

for link in movie_links:
    driver.get(link)
    WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.TAG_NAME, "body")))

    # Wait for the "Next showtimes on" button if it might appear
    try:
        WebDriverWait(driver, 5).until(
            EC.presence_of_element_located(
                (By.XPATH, "//button[starts-with(normalize-space(text()), 'Next showtimes on')]")
            )
        )
    except Exception:
        pass  # It's OK if it doesn't appear

    # Now parse the page
    movie_soup = BeautifulSoup(driver.page_source, "html.parser")
    title_tag = movie_soup.find("h1") or movie_soup.find("h2")
    title = title_tag.get_text(strip=True) if title_tag else None

    # --- NO SHOWTIMES CHECK ---
    no_showtimes_phrase = "There are no showtimes on the selected time period"
    if no_showtimes_phrase in movie_soup.get_text():
        # Use Selenium to find the button and click it if present
        try:
            next_showtimes_buttons = driver.find_elements(
                By.XPATH, "//button[starts-with(normalize-space(text()), 'Next showtimes on')]"
            )
            if next_showtimes_buttons:
                next_showtimes_buttons[0].click()
                # Wait for the showtimes to appear after clicking
                WebDriverWait(driver, 5).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, "time"))
                )
                # Re-parse the updated page
                movie_soup = BeautifulSoup(driver.page_source, "html.parser")
            else:
                print(f"Skipping {title} ({link}) - no showtimes and no 'Next showtimes on' button.")
                continue  # Skip to the next movie
        except Exception as e:
            print(f"Skipping {title} ({link}) - error clicking 'Next showtimes on' button: {e}")
            continue  # Skip to the next movie
    # else: continue to try to find showtimes

    # Poster: first <img> on the page (refine if needed)
    img_tag = movie_soup.find("img")
    poster_url = img_tag.get("src") if isinstance(img_tag, Tag) else ""

    # Description: try to find a <p> or <div> with description (refine as needed)
    desc_tag = movie_soup.find("p") or movie_soup.find("div", {"data-role": "description"})
    description = desc_tag.get_text(strip=True) if desc_tag else ""

    showtimes_flat = []
    seen_dates = set()
    last_seen_count = -1

    while True:
        visible_cards = driver.find_elements(By.CSS_SELECTOR, "div[data-role='card'][aria-hidden='false']")
        new_date_found = False
        for card in visible_cards:
            try:
                button = card.find_element(By.CSS_SELECTOR, "div[role='button'][tabindex='0']")
                date_text = " ".join([d.text for d in button.find_elements(By.XPATH, ".//div") if d.text.strip()])
                if date_text in seen_dates:
                    continue
                new_date_found = True
                seen_dates.add(date_text)
                driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", button)
                button.click()
                WebDriverWait(driver, 5).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, "time"))
                )
                soup = BeautifulSoup(driver.page_source, "html.parser")
                for t in soup.find_all("time"):
                    # Clean up date_text: extract "DAY NUM" (e.g., "FRI 18")
                    match = re.search(r"\b([A-Z]{3})\s?(\d{1,2})\b", date_text)
                    if match:
                        clean_date = f"{match.group(1)} {match.group(2)}"
                    else:
                        clean_date = date_text.strip()  # fallback

                    showtimes_flat.append({
                        "date": clean_date,
                        "time": t.get_text(strip=True)
                    })
            except Exception as e:
                print(f"Error processing visible date card on {link}")

        if not new_date_found or len(seen_dates) == last_seen_count:
            break
        last_seen_count = len(seen_dates)

        try:
            next_arrow = driver.find_element(By.CSS_SELECTOR, "div[role='button'][aria-label='next'][tabindex='0']")
            driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", next_arrow)
            next_arrow.click()
            time.sleep(0.5)
        except Exception:
            break

    results.append({
        "title": title,
        "poster": poster_url,
        "description": description,
        "showtimes": showtimes_flat,
        "venue": "Eveningstar Cinema",
        "venue_id": "eveningstar",
        "city": "Brunswick"
    })

# Write to JSON file
with open("eveningstar_showtimes.json", "w") as f:
    json.dump(results, f, indent=2)

driver.quit()
