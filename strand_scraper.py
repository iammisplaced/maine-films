import requests
from dateutil import parser as dtparser
from dateutil.rrule import rrulestr

def get_strand_showtimes():
    STRAND_API = "https://api.eventive.org/event_buckets/67d44b1883a80ee59cc61f2f/events?upcoming_only=true"
    VENUE = "Strand Theatre"
    VENUE_ID = "strand"
    CITY = "Rockland"
    headers = {
        "User-Agent": "Mozilla/5.0",
        "Accept": "application/json",
        "Authorization": "Basic M2QyYzFjNDZlYWY5MjBjMGY5MDBmN2NmNjc4ZDY5NDI6"
    }
    resp = requests.get(STRAND_API, headers=headers)
    resp.raise_for_status()
    data = resp.json()
    events = data.get('events', []) if 'events' in data else data.get('data', {}).get('events', [])
    films_by_title = {}
    for event in events:
        films = event.get('films', [])
        if not films:
            continue
        film = films[0]
        title = film.get('name')
        if not title:
            continue
        description = film.get('description', '')
        poster = film.get('poster_image', '') or film.get('cover_image', '')
        film_id = film.get('id', '')
        url = f'https://strandfilms.eventive.org/films/{film_id}' if film_id else 'https://strandfilms.eventive.org/schedule'
        showtimes = []
        # Main showtime
        showtime_dt = event.get('start_time')
        if showtime_dt:
            try:
                dtobj = dtparser.parse(showtime_dt)
                show_date = dtobj.strftime('%Y-%m-%d')
                show_time = dtobj.strftime('%H:%M')
            except Exception:
                show_date = showtime_dt[:10]
                show_time = showtime_dt[11:16]
            showtimes.append({
                'date': show_date,
                'time': show_time,
                'venue': VENUE,
                'venue_id': VENUE_ID,
                'city': CITY
            })
        # Recurring showtimes
        recurring = event.get('recurring_event', {})
        repeats = recurring.get('repeats', []) if recurring else []
        for repeat in repeats:
            rrule_str = repeat.get('rrule')
            if not rrule_str:
                continue
            try:
                rules = rrule_str.split('\n')
                dtstart_line = next((line for line in rules if line.startswith('DTSTART')), None)
                rrule_line = next((line for line in rules if line.startswith('RRULE')), None)
                if not dtstart_line or not rrule_line:
                    continue
                full_rrule = dtstart_line + '\n' + rrule_line
                rule = rrulestr(full_rrule)
                duration_ms = repeat.get('duration')
                for dtobj in rule:
                    show_date = dtobj.strftime('%Y-%m-%d')
                    show_time = dtobj.strftime('%H:%M')
                    showtimes.append({
                        'date': show_date,
                        'time': show_time,
                        'venue': VENUE,
                        'venue_id': VENUE_ID,
                        'city': CITY
                    })
            except Exception:
                continue
        key = title.strip().lower()
        if key not in films_by_title:
            films_by_title[key] = {
                'title': title,
                'showtimes': showtimes,
                'film_url': url,
                'description': description,
                'poster': poster
            }
        else:
            films_by_title[key]['showtimes'].extend(showtimes)
    # Deduplicate showtimes for each film
    for film in films_by_title.values():
        seen = set()
        unique_showtimes = []
        for st in film['showtimes']:
            st_key = (st['date'], st['time'])
            if st_key not in seen:
                unique_showtimes.append(st)
                seen.add(st_key)
        film['showtimes'] = unique_showtimes
    return list(films_by_title.values()) 