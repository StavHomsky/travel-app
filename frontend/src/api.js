// All calls to the Flask REST API go through this file, so components never
// build URLs or parse errors themselves.

const BASE = '/api/v1'

export class ApiError extends Error {
  constructor(status, body) {
    super(body?.message || `Request failed (${status})`)
    this.status = status
    this.details = body?.details || {} // e.g. { rating: "Only visited locations can be rated." }
  }
}

async function request(path, { method = 'GET', body, params } = {}) {
  const query = new URLSearchParams()
  for (const [key, value] of Object.entries(params || {})) {
    if (value !== undefined && value !== null && value !== '') query.set(key, value)
  }
  const url = `${BASE}${path}${query.size ? `?${query}` : ''}`

  const isForm = body instanceof FormData
  const response = await fetch(url, {
    method,
    headers: body && !isForm ? { 'Content-Type': 'application/json' } : {},
    body: body && !isForm ? JSON.stringify(body) : body,
  })

  if (response.status === 204) return null
  const data = await response.json().catch(() => null)
  if (!response.ok) throw new ApiError(response.status, data)
  return data
}

export const api = {
  listLocations: (params) => request('/locations', { params }),
  getLocation: (id) => request(`/locations/${id}`),
  createLocation: (data) => request('/locations', { method: 'POST', body: data }),
  updateLocation: (id, data) => request(`/locations/${id}`, { method: 'PUT', body: data }),
  patchLocation: (id, data) => request(`/locations/${id}`, { method: 'PATCH', body: data }),
  deleteLocation: (id) => request(`/locations/${id}`, { method: 'DELETE' }),
  enrichLocation: (id) => request(`/locations/${id}/enrich`, { method: 'POST' }),
  enrichMissing: () => request('/locations/enrich-missing', { method: 'POST' }),
  stats: () => request('/stats'),
  importLocations: (file, mode) => {
    const form = new FormData()
    form.append('file', file)
    return request('/locations/import', { method: 'POST', body: form, params: { mode } })
  },
  exportUrl: `${BASE}/locations/export`,
}
