import { useEffect, useState } from 'react'
import { Link, useLocation } from 'react-router'
import { api } from '../api.js'
import Flash from '../components/Flash.jsx'
import LocationCard from '../components/LocationCard.jsx'

const PER_PAGE = 12
const SORT_OPTIONS = [
  { value: 'created_at:desc', label: 'Newest first' },
  { value: 'created_at:asc', label: 'Oldest first' },
  { value: 'name:asc', label: 'Name A–Z' },
  { value: 'country:asc', label: 'Country A–Z' },
  { value: 'rating:desc', label: 'Best rated' },
]
const EMPTY_FILTERS = { q: '', country: '', type: '', visited: '', sort: 'created_at:desc' }

export default function LocationsPage() {
  // ---- state: data that, when it changes, makes React re-render the page
  const [filters, setFilters] = useState(EMPTY_FILTERS)
  const [page, setPage] = useState(1)
  const [result, setResult] = useState(null) // { items, total, pages } from the API
  const [options, setOptions] = useState({ countries: [], types: [] })
  const [reloadKey, setReloadKey] = useState(0) // bump it to fetch again
  // A message passed by the form page after saving ("Paris was added").
  const [message, setMessage] = useState(useLocation().state?.flash || null)

  // ---- effect 1: load the dropdown options (countries/types that exist)
  useEffect(() => {
    api.stats()
      .then((s) => setOptions({
        countries: Object.keys(s.by_country).sort((a, b) => a.localeCompare(b)),
        types: Object.keys(s.by_type).sort((a, b) => a.localeCompare(b)),
      }))
      .catch(() => {}) // dropdowns just stay empty
  }, [reloadKey])

  // ---- effect 2: load the list whenever filters, page or reloadKey change
  useEffect(() => {
    let cancelled = false
    const [sort, order] = filters.sort.split(':')
    // Wait 250 ms so typing "paris" sends one request, not five.
    const timer = setTimeout(() => {
      api.listLocations({ ...filters, sort, order, page, per_page: PER_PAGE })
        .then((data) => { if (!cancelled) setResult(data) })
        .catch((err) => { if (!cancelled) setMessage({ type: 'error', text: err.message }) })
    }, 250)
    // Cleanup: runs before the next request, so an old slow response
    // can never overwrite a newer one.
    return () => { cancelled = true; clearTimeout(timer) }
  }, [filters, page, reloadKey])

  // ---- event handlers
  function updateFilter(name, value) {
    setFilters((current) => ({ ...current, [name]: value }))
    setPage(1)
  }

  async function runAction(action, successText) {
    try {
      await action()
      setMessage({ type: 'success', text: successText })
      setReloadKey((k) => k + 1)
    } catch (err) {
      setMessage({ type: 'error', text: err.message })
    }
  }

  const handleRate = (location, rating) =>
    runAction(() => api.patchLocation(location.id, { rating }), `Rated ${location.name} ${rating}★`)

  const handleMarkVisited = (location) =>
    runAction(() => api.patchLocation(location.id, { visited: true }), `${location.name} marked as visited 🎉`)

  const handleDelete = (location) => {
    if (!window.confirm(`Delete ${location.name}?`)) return
    void runAction(() => api.deleteLocation(location.id), `${location.name} was deleted.`)
  }

  const hasFilters = JSON.stringify(filters) !== JSON.stringify(EMPTY_FILTERS)

  // ---- what to show (JSX)
  return (
    <>
      <header className="page-header">
        <p>Search, filter and rate your destinations</p>
      </header>

      <div className="page-header">
        <Link to="/locations/new" className="btn btn-primary btn-pill">+ Add New Location</Link>
      </div>

      <Flash message={message} />

      <div className="toolbar">
        <input
          type="search"
          placeholder="🔍 Search name or country…"
          value={filters.q}
          onChange={(e) => updateFilter('q', e.target.value)}
          aria-label="Search"
        />
        <select value={filters.country} onChange={(e) => updateFilter('country', e.target.value)} aria-label="Country">
          <option value="">All countries</option>
          {options.countries.map((c) => <option key={c} value={c}>{c}</option>)}
        </select>
        <select value={filters.type} onChange={(e) => updateFilter('type', e.target.value)} aria-label="Type">
          <option value="">All types</option>
          {options.types.map((t) => <option key={t} value={t}>{t}</option>)}
        </select>
        <select value={filters.visited} onChange={(e) => updateFilter('visited', e.target.value)} aria-label="Status">
          <option value="">Visited + wishlist</option>
          <option value="true">Visited</option>
          <option value="false">Wishlist</option>
        </select>
        <select value={filters.sort} onChange={(e) => updateFilter('sort', e.target.value)} aria-label="Sort">
          {SORT_OPTIONS.map((o) => <option key={o.value} value={o.value}>{o.label}</option>)}
        </select>
        <button className="btn" disabled={!hasFilters} onClick={() => { setFilters(EMPTY_FILTERS); setPage(1) }}>
          Clear
        </button>
      </div>

      <section className="locations-grid">
        {!result && <p className="loading">Loading…</p>}
        {result && result.items.length === 0 && (
          <p className="empty-state">No locations match. Try clearing the filters, or add one.</p>
        )}
        {result?.items.map((location) => (
          <LocationCard
            key={location.id}
            location={location}
            onRate={handleRate}
            onMarkVisited={handleMarkVisited}
            onDelete={handleDelete}
          />
        ))}
      </section>

      {result && result.pages > 1 && (
        <nav className="pagination">
          <button className="btn" disabled={page <= 1} onClick={() => setPage(page - 1)}>← Previous</button>
          <span>Page {page} of {result.pages} · {result.total} locations</span>
          <button className="btn" disabled={page >= result.pages} onClick={() => setPage(page + 1)}>Next →</button>
        </nav>
      )}
    </>
  )
}
