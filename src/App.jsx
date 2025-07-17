import { useState, useEffect, useRef, createRef } from 'react';
import './App.css';
import { Flipper, Flipped } from 'react-flip-toolkit';

// Utility to prevent single-word line breaks (widows)
function widowFix(text) {
  if (!text) return '';
  return text.replace(/\s+([^\s]+)\s*$/, '\u00A0$1');
}

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
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedVenue, setSelectedVenue] = useState('');
  const nodeRefs = useRef([]);
  const [showContentMap, setShowContentMap] = useState({});
  const prevKeysRef = useRef([]);
  // Fade-in for new cards, fade-out for removed cards
  const [fadingInKeys, setFadingInKeys] = useState([]);
  const [fadingOutKeys, setFadingOutKeys] = useState([]);
  const [removedCards, setRemovedCards] = useState([]); // [{film, idx}]

  useEffect(() => {
    fetch('https://raw.githubusercontent.com/iammisplaced/maine-films/main/maine_showtimes.json')
      .then(res => res.json())
      .then(data => setFilms(data));
  }, []);

  // Get all unique venues from films
  const allVenues = Array.from(
    new Set(
      films.flatMap(film => film.showtimes.map(st => st.venue).filter(Boolean))
    )
  ).sort();

  // Sort films by soonest showtime
  const sortedFilms = [...films].sort((a, b) => {
    const aEarliest = getEarliestShowtime(a);
    const bEarliest = getEarliestShowtime(b);
    if (!aEarliest && !bEarliest) return 0;
    if (!aEarliest) return 1;
    if (!bEarliest) return -1;
    return aEarliest - bEarliest;
  });

  // Filter films by search and venue
  const filteredFilms = sortedFilms.filter(film => {
    const matchesSearch = film.title.toLowerCase().includes(searchQuery.toLowerCase());
    const matchesVenue = !selectedVenue || film.showtimes.some(st => st.venue === selectedVenue);
    return matchesSearch && matchesVenue;
  });

  // Fade-in for new cards, fade-out for removed cards
  useEffect(() => {
    const currentKeys = filteredFilms.map(film => film.title);
    const prevKeys = prevKeysRef.current;
    // New cards
    const newKeys = currentKeys.filter(key => !prevKeys.includes(key));
    if (newKeys.length > 0) {
      setFadingInKeys(keys => [...keys, ...newKeys]);
      setTimeout(() => {
        setFadingInKeys(keys => keys.filter(key => !newKeys.includes(key)));
      }, 500);
    }
    // Removed cards
    const removedKeys = prevKeys.filter(key => !currentKeys.includes(key));
    if (removedKeys.length > 0) {
      // Find the film/idx for each removed key
      const removed = prevKeys
        .map((key, idx) => {
          const film = prevKeysRef.currentFilms ? prevKeysRef.currentFilms[idx] : null;
          return removedKeys.includes(key) && film ? { film, idx } : null;
        })
        .filter(Boolean);
      setFadingOutKeys(keys => [...keys, ...removedKeys]);
      setRemovedCards(cards => [...cards, ...removed]);
      setTimeout(() => {
        setFadingOutKeys(keys => keys.filter(key => !removedKeys.includes(key)));
        setRemovedCards(cards => cards.filter(card => !removedKeys.includes(card.film.title)));
      }, 500);
    }
    prevKeysRef.current = currentKeys;
    prevKeysRef.currentFilms = filteredFilms;
  }, [filteredFilms]);

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

  function handleClearFilters() {
    setSearchQuery('');
    setSelectedVenue('');
  }

  return (
    <div className="app-container">
      <div className="now-showing-title">Now Showing</div>
      {/* Filter Controls */}
      <div className="filter-controls">
        <input
          type="text"
          placeholder="Search by title..."
          value={searchQuery}
          onChange={e => setSearchQuery(e.target.value)}
          style={{ padding: '0.5rem 1rem', borderRadius: 6, border: '1px solid #ccc', fontSize: '1rem', minWidth: 180 }}
        />
        <select
          value={selectedVenue}
          onChange={e => setSelectedVenue(e.target.value)}
          style={{ padding: '0.5rem 1rem', borderRadius: 6, border: '1px solid #ccc', fontSize: '1rem', minWidth: 180 }}
        >
          <option value="">All Venues</option>
          {allVenues.map(venue => (
            <option key={venue} value={venue}>{venue}</option>
          ))}
        </select>
        <button
          onClick={handleClearFilters}
          style={{ padding: '0.5rem 1.2rem', borderRadius: 6, border: 'none', background: '#eee', fontSize: '1rem', cursor: 'pointer' }}
          disabled={!searchQuery && !selectedVenue}
        >
          Clear Filters
        </button>
      </div>
      {/* Debug info */}
      <div style={{ color: '#888', fontSize: '0.95rem', marginBottom: '0.5rem', textAlign: 'center' }}>
        films: {films.length} | sorted: {sortedFilms.length} | filtered: {filteredFilms.length}
      </div>
      <Flipper flipKey={filteredFilms.map(f => f.title).join(',')} spring={{ stiffness: 60, damping: 22 }}>
        <div className="film-card-grid">
          {filteredFilms.map((film, idx) => {
            const cardKey = film.title;
            return (
              <Flipped
                key={cardKey}
                flipId={cardKey}
              >
                <div
                  className={
                    'film-card' + (fadingInKeys.includes(cardKey) ? ' fade-in-card' : '')
                  }
                  onClick={() => setSelectedFilm(film)}
                  tabIndex={0}
                  role="button"
                  aria-label={`View details for ${film.title}`}
                  onMouseMove={e => handleCardMouseMove(e, idx)}
                  onMouseLeave={() => handleCardMouseLeave(idx)}
                  onMouseEnter={() => handleCardMouseEnter(idx)}
                  style={
                    hoveredCard === idx
                      ? {
                          transform: cardTransforms[idx],
                          zIndex: 2,
                          boxShadow:
                            '0 2px 12px 0 rgba(106,130,251,0.18), 0 4px 24px 0 rgba(252,92,125,0.12)',
                        }
                      : {}
                  }
                >
                  <div className="film-card-content">
                    <div className="film-poster-container">
                      <img
                        src={film.poster || '/no-poster.png'}
                        alt={film.title + ' poster'}
                        className="film-poster"
                        onError={e => { e.target.src = '/no-poster.png'; }}
                      />
                    </div>
                    <div className="film-card-info">
                      <div className="film-card-title">{widowFix(film.title)}</div>
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
                          const blocks = [];
                          if (venuesNow.length > 0) {
                            blocks.push(
                              <div className="now-showing-block" key="now">
                                <span style={{ color: '#2ecc40', fontWeight: 600, fontSize: '1.05em' }}>Now Showing</span>
                                <ul className="venue-list">
                                  {venuesNow.map(venue => (
                                    <li key={venue}>{venue}</li>
                                  ))}
                                </ul>
                              </div>
                            );
                          }
                          if (venuesSoon.length > 0) {
                            blocks.push(
                              <div className="coming-soon-block" key="soon">
                                <span style={{ color: '#ff9800', fontWeight: 600, fontSize: '1.05em' }}>Coming Soon</span>
                                <ul className="venue-list">
                                  {venuesSoon.map(venue => (
                                    <li key={venue}>{venue}</li>
                                  ))}
                                </ul>
                              </div>
                            );
                          }
                          return blocks;
                        })()}
                      </div>
                    </div>
                  </div>
                </div>
              </Flipped>
            );
          })}
          {removedCards.map(({ film, idx }) => {
            const cardKey = film.title;
            if (!fadingOutKeys.includes(cardKey)) return null;
            return (
              <Flipped
                key={cardKey}
                flipId={cardKey}
              >
                <div
                  className="film-card fade-out-card"
                  onClick={() => setSelectedFilm(film)}
                  tabIndex={0}
                  role="button"
                  aria-label={`View details for ${film.title}`}
                  onMouseMove={e => handleCardMouseMove(e, idx)}
                  onMouseLeave={() => handleCardMouseLeave(idx)}
                  onMouseEnter={() => handleCardMouseEnter(idx)}
                >
                  <div className="film-card-content">
                    <div className="film-poster-container">
                      <img
                        src={film.poster || '/no-poster.png'}
                        alt={film.title + ' poster'}
                        className="film-poster"
                        onError={e => { e.target.src = '/no-poster.png'; }}
                      />
                    </div>
                    <div className="film-card-title">{widowFix(film.title)}</div>
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
                        const blocks = [];
                        if (venuesNow.length > 0) {
                          blocks.push(
                            <div className="now-showing-block" key="now">
                              <span style={{ color: '#2ecc40', fontWeight: 600, fontSize: '1.05em' }}>Now Showing</span>
                              <ul className="venue-list">
                                {venuesNow.map(venue => (
                                  <li key={venue}>{venue}</li>
                                ))}
                              </ul>
                            </div>
                          );
                        }
                        if (venuesSoon.length > 0) {
                          blocks.push(
                            <div className="coming-soon-block" key="soon">
                              <span style={{ color: '#ff9800', fontWeight: 600, fontSize: '1.05em' }}>Coming Soon</span>
                              <ul className="venue-list">
                                {venuesSoon.map(venue => (
                                  <li key={venue}>{venue}</li>
                                ))}
                              </ul>
                            </div>
                          );
                        }
                        return blocks;
                      })()}
                    </div>
                  </div>
                </div>
              </Flipped>
            );
          })}
          {filteredFilms.length === 0 && (
            <div style={{ width: '100%', textAlign: 'center', color: '#888', fontSize: '1.2rem', marginTop: '2rem' }}>
              No films found.
            </div>
          )}
        </div>
      </Flipper>
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
            <h2>{widowFix(selectedFilm.title)}</h2>
            <div className="modal-description">{widowFix(selectedFilm.description)}</div>
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
