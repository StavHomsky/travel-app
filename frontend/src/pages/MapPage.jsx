import { useEffect, useState } from 'react'
import { Link } from 'react-router'
import { CircleMarker, MapContainer, Popup, TileLayer } from 'react-leaflet'
import 'leaflet/dist/leaflet.css'
import { api } from '../api.js'
import Flash from '../components/Flash.jsx'
import StarRating from '../components/StarRating.jsx'
import { tripAdvisorUrl, typeIcon } from '../utils.js'

// Standard OpenStreetMap tiles: free, no API key, attribution required.
// They are light-colored; index.css inverts them to match the dark theme.
const TILES = 'https://tile.openstreetmap.org/{z}/{x}/{y}.png'
const ATTRIBUTION = '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'

export default function MapPage() {
  const [locations, setLocations] = useState(null)
  const [error, setError] = useState(null)

  useEffect(() => {
    api.listLocations({ per_page: 100 })
      .then((data) => setLocations(data.items))
      .catch((err) => setError({ type: 'error', text: err.message }))
  }, [])

  if (error) return <Flash message={error} />
  if (!locations) return <p className="loading">Loading…</p>

  const mapped = locations.filter((l) => l.latitude !== null && l.longitude !== null)
  const unmapped = locations.length - mapped.length
  // Zoom the map so every pin fits; fall back to a world view.
  const bounds = mapped.length > 1 ? mapped.map((l) => [l.latitude, l.longitude]) : null

  return (
    <>
      <header className="page-header">
        <h1>Map</h1>
        <p>{mapped.length} places on the map</p>
      </header>

      <div className="map-legend">
        <span><span className="dot" style={{ background: '#22c55e' }} />Visited</span>
        <span><span className="dot" style={{ background: '#f59e0b' }} />Wishlist</span>
      </div>

      {unmapped > 0 && (
        <div className="flash flash-error">
          {unmapped} location{unmapped > 1 ? 's have' : ' has'} no map position yet.{' '}
          <Link to="/import">Fetch missing info</Link>
        </div>
      )}

      <div className="map-wrapper">
        <MapContainer
          bounds={bounds || undefined}
          boundsOptions={{ padding: [40, 40] }}
          center={bounds ? undefined : mapped[0] ? [mapped[0].latitude, mapped[0].longitude] : [30, 10]}
          zoom={bounds ? undefined : mapped[0] ? 6 : 2}
          scrollWheelZoom
        >
          <TileLayer url={TILES} attribution={ATTRIBUTION} />
          {mapped.map((location) => (
            <CircleMarker
              key={location.id}
              center={[location.latitude, location.longitude]}
              radius={10}
              pathOptions={{
                color: '#fff',
                weight: 2,
                fillColor: location.visited ? '#22c55e' : '#f59e0b',
                fillOpacity: 0.9,
              }}
            >
              <Popup>
                <LocationPopup location={location} />
              </Popup>
            </CircleMarker>
          ))}
        </MapContainer>
      </div>
    </>
  )
}

function LocationPopup({ location }) {
  return (
    <div className="map-popup">
      {location.image_url && <img src={location.image_url} alt={location.name} />}
      <strong>{typeIcon(location.type)} {location.name}</strong>
      <div>{location.country}</div>
      <div style={{ margin: '6px 0' }}>
        {location.visited
          ? <StarRating value={location.rating} />
          : <a href={tripAdvisorUrl(location)} target="_blank" rel="noreferrer">♡ Wishlist – see TripAdvisor ↗</a>}
      </div>
      <Link to={`/locations/${location.id}/edit`}>Edit</Link>
    </div>
  )
}
