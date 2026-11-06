const TYPE_ICONS = {
  city: '🏙️',
  beach: '🏖️',
  ski: '⛷️',
  nature: '🌲',
  mountain: '🏔️',
  island: '🏝️',
  desert: '🏜️',
  lake: '🛶',
  museum: '🏛️',
}

export function typeIcon(type) {
  return TYPE_ICONS[type] || '📍'
}

// TripAdvisor has no free public API, but its search page works with a
// plain URL and shows hotels, restaurants and things to do for the place.
export function tripAdvisorUrl(location) {
  return `https://www.tripadvisor.com/Search?q=${encodeURIComponent(`${location.name} ${location.country}`)}`
}
