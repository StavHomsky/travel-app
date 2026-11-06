import { useEffect, useState } from 'react'
import { Link, useNavigate, useParams } from 'react-router'
import { api } from '../api.js'
import Flash from '../components/Flash.jsx'
import StarRating from '../components/StarRating.jsx'

const EMPTY_FORM = {
  name: '',
  country: '',
  type: '',
  visited: false,
  rating: null,
  latitude: '',
  longitude: '',
}

// One page for both "add" (/locations/new) and "edit" (/locations/:id/edit).
export default function LocationFormPage() {
  const { id } = useParams() // undefined when adding
  const isEdit = Boolean(id)
  const navigate = useNavigate()

  const [form, setForm] = useState(EMPTY_FORM)
  const [errors, setErrors] = useState({}) // { field: "message" } from the API
  const [message, setMessage] = useState(null)
  const [saving, setSaving] = useState(false)
  const [loading, setLoading] = useState(isEdit)
  const [knownTypes, setKnownTypes] = useState([])

  // Suggest types that already exist (city, ski, ...) to keep them consistent.
  useEffect(() => {
    api.stats().then((s) => setKnownTypes(Object.keys(s.by_type).sort())).catch(() => {})
  }, [])

  // In edit mode, load the location and fill the form with it.
  useEffect(() => {
    if (!isEdit) return
    api.getLocation(id)
      .then((loc) => setForm({
        name: loc.name,
        country: loc.country,
        type: loc.type,
        visited: loc.visited,
        rating: loc.rating,
        latitude: loc.latitude ?? '',
        longitude: loc.longitude ?? '',
      }))
      .catch((err) => setMessage({ type: 'error', text: err.message }))
      .finally(() => setLoading(false))
  }, [id, isEdit])

  // "Controlled inputs": every input shows form[field] and writes back here.
  function update(field, value) {
    setForm((current) => ({ ...current, [field]: value }))
    setErrors((current) => ({ ...current, [field]: undefined }))
  }

  function toggleVisited(visited) {
    // Same rule as the backend: only visited places keep a rating.
    setForm((current) => ({ ...current, visited, rating: visited ? current.rating : null }))
  }

  function buildPayload() {
    const payload = {
      name: form.name,
      country: form.country,
      type: form.type,
      visited: form.visited,
      rating: form.visited ? form.rating : null,
    }
    // Coordinates are optional: only sent when the user typed both.
    if (form.latitude !== '' && form.longitude !== '') {
      payload.latitude = Number(form.latitude)
      payload.longitude = Number(form.longitude)
    }
    return payload
  }

  async function handleSubmit(event) {
    event.preventDefault() // stop the browser's own full-page form submit
    setSaving(true)
    setMessage(null)
    try {
      const saved = isEdit
        ? await api.updateLocation(id, buildPayload())
        : await api.createLocation(buildPayload())
      navigate('/locations', {
        state: { flash: { type: 'success', text: `${saved.name} was ${isEdit ? 'updated' : 'added'}.` } },
      })
    } catch (err) {
      setErrors(err.details || {})
      setMessage({ type: 'error', text: err.message })
      setSaving(false)
    }
  }

  async function handleRefreshInfo() {
    try {
      const loc = await api.enrichLocation(id)
      setForm((current) => ({ ...current, latitude: loc.latitude ?? '', longitude: loc.longitude ?? '' }))
      setMessage({
        type: loc.latitude ? 'success' : 'error',
        text: loc.latitude ? 'Map location and Wikipedia info refreshed.' : 'Could not find this place on the map.',
      })
    } catch (err) {
      setMessage({ type: 'error', text: err.message })
    }
  }

  if (loading) return <p className="loading">Loading…</p>

  return (
    <div className="form-page">
      <form className="form-card" onSubmit={handleSubmit} noValidate>
        <h1>{isEdit ? 'Edit Location' : 'Add New Location'}</h1>
        <p>
          {isEdit
            ? 'Update your destination details'
            : 'The map position, photo and description are found automatically.'}
        </p>

        <Flash message={message} />

        <label htmlFor="name">Location Name</label>
        <input id="name" type="text" value={form.name} maxLength={120} required
          placeholder="Example: Paris" onChange={(e) => update('name', e.target.value)} />
        <FieldError message={errors.name} />

        <label htmlFor="country">Country</label>
        <input id="country" type="text" value={form.country} maxLength={80} required
          placeholder="Example: France" onChange={(e) => update('country', e.target.value)} />
        <FieldError message={errors.country} />

        <label htmlFor="type">Type</label>
        <input id="type" type="text" value={form.type} maxLength={50} required list="known-types"
          placeholder="Example: city / beach / ski" onChange={(e) => update('type', e.target.value)} />
        <datalist id="known-types">
          {knownTypes.map((t) => <option key={t} value={t} />)}
        </datalist>
        <FieldError message={errors.type} />

        <div className="checkbox-row">
          <input id="visited" type="checkbox" checked={form.visited}
            onChange={(e) => toggleVisited(e.target.checked)} />
          <label htmlFor="visited">I already visited this place</label>
        </div>

        {/* Conditional rendering: the rating only exists for visited places. */}
        {form.visited && (
          <>
            <label>Your rating</label>
            <StarRating value={form.rating} onChange={(stars) => update('rating', stars)} />
            {form.rating && (
              <button type="button" className="btn" style={{ marginLeft: 12, padding: '6px 12px' }}
                onClick={() => update('rating', null)}>
                Clear
              </button>
            )}
            <FieldError message={errors.rating} />
          </>
        )}

        <details className="advanced">
          <summary>Advanced: set map coordinates by hand</summary>
          <div className="form-row">
            <div>
              <label htmlFor="latitude">Latitude</label>
              <input id="latitude" type="number" step="any" min="-90" max="90" value={form.latitude}
                onChange={(e) => update('latitude', e.target.value)} />
              <FieldError message={errors.latitude} />
            </div>
            <div>
              <label htmlFor="longitude">Longitude</label>
              <input id="longitude" type="number" step="any" min="-180" max="180" value={form.longitude}
                onChange={(e) => update('longitude', e.target.value)} />
              <FieldError message={errors.longitude} />
            </div>
          </div>
          {isEdit && (
            <button type="button" className="btn btn-sky" style={{ marginTop: 14 }} onClick={handleRefreshInfo}>
              🔄 Look up map + Wikipedia info again
            </button>
          )}
        </details>

        <button type="submit" className="submit-btn" disabled={saving}>
          {saving ? 'Saving…' : isEdit ? 'Update Location' : 'Save Location'}
        </button>

        <Link to="/locations" className="back-link">← Back to locations</Link>
      </form>
    </div>
  )
}

function FieldError({ message }) {
  return message ? <p className="field-error">{message}</p> : null
}
