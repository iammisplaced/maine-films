import { useState, useEffect } from 'react';
import './App.css';

function getDaySuffix(day) {
  if (day >= 11 && day <= 13) return 'th';
  switch (day % 10) {
    case 1: return 'st';
    case 2: return 'nd';
    case 3: return 'rd';
    default: return 'th';
  }
}

function formatShowDate(dateStr) {
  // dateStr is YYYY-MM-DD
  const d = new Date(dateStr + 'T00:00:00');
  const dayOfWeek = d.toLocaleDateString(undefined, { weekday: 'long' });
  const month = d.toLocaleDateString(undefined, { month: 'long' });
  const day = d.getDate();
  const suffix = getDaySuffix(day);
  return `${dayOfWeek} ${month} ${day}${suffix}`;
}

function formatShowTime(timeStr) {
  // timeStr is HH:MM (24-hour)
  if (!timeStr) return '';
  const [hour, minute] = timeStr.split(':').map(Number);
  if (isNaN(hour) || isNaN(minute)) return timeStr;
  const d = new Date();
  d.setHours(hour);
  d.setMinutes(minute);
  return d.toLocaleTimeString(undefined, { hour: 'numeric', minute: '2-digit', hour12: true }).replace(/^0/, '');
}

function groupShowtimesByVenueAndDate(showtimes) {
  const venues = {};
  showtimes.forEach(st => {
    const vkey = st.venue_id;
    if (!venues[vkey]) {
      venues[vkey] = {
        name: st.venue,
        city: st.city,
        venue_id: st.venue_id,
        dates: {}
      };
    }
    if (!venues[vkey].dates[st.date]) {
      venues[vkey].dates[st.date] = [];
    }
    venues[vkey].dates[st.date].push(st.time);
  });
  return Object.values(venues);
}

function getEarliestShowtime(film) {
  if (!film.showtimes || film.showtimes.length === 0) return null;
  // Combine date and time into a Date object for each showtime
  const showtimeDates = film.showtimes
    .filter(st => st.date)
    .map(st => new Date(st.date + 'T' + (st.time || '00:00')));
  if (showtimeDates.length === 0) return null;
  return new Date(Math.min(...showtimeDates));
}

function App() {
  const [films, setFilms] = useState([]);
  const [selectedFilm, setSelectedFilm] = useState(null);
  const [hoveredCard, setHoveredCard] = useState(null); // index of hovered card
  const [cardTransforms, setCardTransforms] = useState({}); // { idx: transformString }

  useEffect(() => {
    fetch('https://raw.githubusercontent.com/iammisplaced/maine-films/main/maine_showtimes.json')
      .then(res => res.json())
      .then(data => setFilms(data));
  }, []);

  // Sort films by soonest showtime
  const sortedFilms = [...films].sort((a, b) => {
    const aEarliest = getEarliestShowtime(a);
    const bEarliest = getEarliestShowtime(b);
    if (!aEarliest && !bEarliest) return 0;
    if (!aEarliest) return 1;
    if (!bEarliest) return -1;
    return aEarliest - bEarliest;
  });

  // Mouse move handler for 3D tilt
  function handleCardMouseMove(e, idx) {
    const card = e.currentTarget;
    const rect = card.getBoundingClientRect();
    const x = e.clientX - rect.left;
    const y = e.clientY - rect.top;
    const centerX = rect.width / 2;
    const centerY = rect.height / 2;
    const rotateX = ((y - centerY) / centerY) * 5; // max 5deg (was 10)
    const rotateY = ((x - centerX) / centerX) * 5; // max 5deg (was 10)
    const transform = `perspective(600px) rotateX(${-rotateX}deg) rotateY(${rotateY}deg) scale(1.03)`;
    setCardTransforms(t => ({ ...t, [idx]: transform }));
    setHoveredCard(idx);
  }
  function handleCardMouseLeave(idx) {
    setCardTransforms(t => ({ ...t, [idx]: '' }));
    setHoveredCard(null);
  }
  function handleCardMouseEnter(idx) {
    setHoveredCard(idx);
  }

  return (
    <div className="app-container">
      <div className="now-showing-title">Now Showing</div>
      <div className="film-card-grid">
        {sortedFilms.map((film, idx) => (
          <div
            key={film.title}
            className="film-card"
            onClick={() => setSelectedFilm(film)}
            tabIndex={0}
            role="button"
            aria-label={`View details for ${film.title}`}
            onMouseMove={e => handleCardMouseMove(e, idx)}
            onMouseLeave={() => handleCardMouseLeave(idx)}
            onMouseEnter={() => handleCardMouseEnter(idx)}
            style={hoveredCard === idx ? { transform: cardTransforms[idx], zIndex: 2 } : {}}
          >
            <img
              src={film.poster || '/no-poster.png'}
              alt={film.title + ' poster'}
              className="film-poster"
              onError={e => { e.target.src = '/no-poster.png'; }}
            />
            <div className="film-card-title">{film.title}</div>
            <div className="film-card-venues">
              {(() => {
                const now = new Date();
                const venuesMap = {};

                film.showtimes.forEach(st => {
                  if (!st.venue) return;
                  if (!venuesMap[st.venue]) venuesMap[st.venue] = [];
                  venuesMap[st.venue].push(st);
                });

                const venuesNow = [];
                const venuesSoon = [];

                Object.entries(venuesMap).forEach(([venue, sts]) => {
                  // Is there any showtime today or earlier?
                  const anyNow = sts.some(st => {
                    if (!st.date) return false;
                    const showDate = new Date(st.date + 'T' + (st.time || '00:00'));
                    // Compare only the date part
                    const today = new Date();
                    today.setHours(0,0,0,0);
                    showDate.setHours(0,0,0,0);
                    return showDate <= today;
                  });
                  if (anyNow) {
                    venuesNow.push(venue);
                  } else if (sts.some(st => st.coming_soon || (st.date && new Date(st.date) > new Date()))) {
                    venuesSoon.push(venue);
                  }
                });

                return (
                  <>
                    {venuesNow.length > 0 && (
                      <div className="now-showing-block">
                        <span className="film-tag now-showing-tag">Now Showing</span>
                        <ul className="venue-list">
                          {venuesNow.map(venue => (
                            <li key={venue}>{venue}</li>
                          ))}
                        </ul>
                      </div>
                    )}
                    {venuesSoon.length > 0 && (
                      <div className="coming-soon-block">
                        <span className="film-tag coming-soon-tag">Coming Soon</span>
                        <ul className="venue-list">
                          {venuesSoon.map(venue => (
                            <li key={venue}>{venue}</li>
                          ))}
                        </ul>
                      </div>
                    )}
                  </>
                );
              })()}
            </div>
          </div>
        ))}
      </div>
      {selectedFilm && (
        <div className="modal-overlay" onClick={() => setSelectedFilm(null)}>
          <div className="modal-content" onClick={e => e.stopPropagation()}>
            <button className="modal-close" onClick={() => setSelectedFilm(null)}>&times;</button>
            <img
              src={selectedFilm.poster || '/no-poster.png'}
              alt={selectedFilm.title + ' poster'}
              className="modal-poster"
              onError={e => { e.target.src = '/no-poster.png'; }}
            />
            <h2>{selectedFilm.title}</h2>
            <div className="modal-description">{selectedFilm.description}</div>
            <h3>Showtimes</h3>
            {groupShowtimesByVenueAndDate(selectedFilm.showtimes).map((venue, idx) => (
              <div key={venue.name + venue.city} className="modal-showtime-block">
                <strong>
                  {selectedFilm.film_urls && selectedFilm.film_urls[venue.venue_id] ? (
                    <a
                      href={selectedFilm.film_urls[venue.venue_id]}
                      target="_blank"
                      rel="noopener noreferrer"
                      style={{ color: 'inherit', textDecoration: 'underline' }}
                    >
                      {venue.name}
                    </a>
                  ) : (
                    venue.name
                  )} ({venue.city}):
                </strong>
                <ul>
                  {Object.entries(venue.dates).map(([date, times]) => {
                    // Find the showtime objects for this date and venue
                    const showtimeObjs = selectedFilm.showtimes.filter(
                      st => st.date === date && st.venue_id === venue.venue_id
                    );
                    const allTimesMissing = showtimeObjs.every(st => !st.time);
                    const anyComingSoon = showtimeObjs.some(st => st.coming_soon);

                    // If the date is missing or invalid, show "Coming Soon!"
                    if (!date || date === 'null' || date === 'undefined' || isNaN(new Date(date))) {
                      return (
                        <li key={date}>
                          <span style={{ fontWeight: 'bold' }}>Coming Soon!</span>
                        </li>
                      );
                    }

                    if (allTimesMissing && anyComingSoon) {
                      return (
                        <li key={date}>
                          <span style={{ fontWeight: 'bold' }}>Coming {formatShowDate(date)}</span>
                        </li>
                      );
                    }
                    return (
                      <li key={date}>
                        <span style={{ fontWeight: 'bold' }}>{formatShowDate(date)}:</span>
                        <span style={{ marginLeft: 8 }}>
                          {times.filter(Boolean).map(formatShowTime).join(', ')}
                        </span>
                      </li>
                    );
                  })}
                </ul>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

export default App;
