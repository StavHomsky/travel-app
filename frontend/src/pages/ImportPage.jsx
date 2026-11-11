import { useState } from 'react'
import { api } from '../api.js'
import Flash from '../components/Flash.jsx'

export default function ImportPage() {
  const [file, setFile] = useState(null)
  const [mode, setMode] = useState('append')
  const [message, setMessage] = useState(null)
  const [busy, setBusy] = useState(false)
  const [progress, setProgress] = useState(null) // text while enriching

  async function handleImport(event) {
    event.preventDefault()
    if (!file) {
      setMessage({ type: 'error', text: 'Please choose a JSON file.' })
      return
    }
    if (mode === 'replace' && !window.confirm('Replace ALL current locations with this file?')) return

    setBusy(true)
    try {
      const result = await api.importLocations(file, mode)
      setMessage({
        type: 'success',
        text: `Imported ${result.created} locations (${result.skipped} duplicates skipped). Fetching map info…`,
      })
      await fetchMissingInfo()
    } catch (err) {
      // For a bad file the API lists errors per item: { "2": { "name": "..." } }
      const details = Object.keys(err.details).length ? ` ${JSON.stringify(err.details)}` : ''
      setMessage({ type: 'error', text: `${err.message}${details}` })
    } finally {
      setBusy(false)
    }
  }

  // The backend enriches 10 places per call (OpenStreetMap allows 1 request
  // per second), so we call it in a loop until there is nothing left to do.
  async function fetchMissingInfo() {
    setBusy(true)
    let total = 0
    try {
      for (;;) {
        const result = await api.enrichMissing()
        total += result.updated
        setProgress(`Found map info for ${total} places, ${result.remaining} still missing…`)
        if (result.remaining === 0 || result.updated === 0) break
      }
      setMessage({ type: 'success', text: `Done: map + Wikipedia info added for ${total} places.` })
    } catch (err) {
      setMessage({ type: 'error', text: err.message })
    } finally {
      setProgress(null)
      setBusy(false)
    }
  }

  return (
    <div className="form-page">
      <form className="form-card" onSubmit={handleImport}>
        <h1>Import / Export</h1>
        <p>Upload a JSON file, or download all your locations</p>

        <Flash message={message} />
        {progress && <div className="flash flash-success">⏳ {progress}</div>}

        <label htmlFor="file">Choose JSON File</label>
        <input id="file" type="file" accept=".json,application/json"
          onChange={(e) => setFile(e.target.files[0] || null)} />

        {/* fieldset + legend: the accessible way to label a group of radios */}
        <fieldset>
          <legend>Import Method</legend>
          <div className="checkbox-row">
            <input type="radio" id="append" name="mode" value="append"
              checked={mode === 'append'} onChange={() => setMode('append')} />
            <label htmlFor="append">Append to existing data (duplicates are skipped)</label>
          </div>
          <div className="checkbox-row">
            <input type="radio" id="replace" name="mode" value="replace"
              checked={mode === 'replace'} onChange={() => setMode('replace')} />
            <label htmlFor="replace">Replace current data</label>
          </div>
        </fieldset>

        <button type="submit" className="submit-btn" disabled={busy}>
          {busy ? 'Working…' : 'Import Locations'}
        </button>

        <div className="card-actions" style={{ marginTop: 16 }}>
          <a className="btn btn-sky" href={api.exportUrl} download="locations.json">⬇ Export JSON</a>
          <button type="button" className="btn btn-purple" disabled={busy} onClick={fetchMissingInfo}>
            🔄 Fetch missing map info
          </button>
        </div>
      </form>
    </div>
  )
}
