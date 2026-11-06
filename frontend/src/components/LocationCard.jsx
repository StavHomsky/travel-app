import { Link } from 'react-router'
import StarRating from './StarRating.jsx'
import { tripAdvisorUrl, typeIcon } from '../utils.js'

// A "presentational" component: it only displays one location and reports
// clicks upwards through the on... props. The page decides what to do
// (call the API, reload the list).
export default function LocationCard({ location, onRate, onMarkVisited, onDelete }) {
  return (
    <article className="location-card">
      <div className="card-image">
        {location.image_url
          ? <img src={location.image_url} alt={location.name} loading="lazy" />
          : <span aria-hidden="true">{typeIcon(location.type)}</span>}
        <span className={`status ${location.visited ? 'visited' : 'wishlist'}`}>
          {location.visited ? '✓ Visited' : '♡ Wishlist'}
        </span>
      </div>

      <div className="card-content">
        <div className="card-title">
          <h3>{location.name}</h3>
          <span>{typeIcon(location.type)} {location.type} · {location.country}</span>
        </div>

        {location.description && <p className="card-description">{location.description}</p>}

        <div className="card-meta">
          {location.visited
            ? <StarRating value={location.rating} onChange={(stars) => onRate(location, stars)} />
            : <span>Not visited yet</span>}
          {location.wiki_url && (
            <a href={location.wiki_url} target="_blank" rel="noreferrer">Wikipedia ↗</a>
          )}
        </div>

        <div className="card-actions">
          {!location.visited && (
            <>
              <a className="btn btn-tripadvisor" href={tripAdvisorUrl(location)} target="_blank" rel="noreferrer">
                TripAdvisor ↗
              </a>
              <button className="btn btn-green" onClick={() => onMarkVisited(location)}>
                ✓ Mark visited
              </button>
            </>
          )}
          <Link className="btn btn-blue" to={`/locations/${location.id}/edit`}>Edit</Link>
          <button className="btn btn-red" onClick={() => onDelete(location)}>Delete</button>
        </div>
      </div>
    </article>
  )
}
