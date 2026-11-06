import { afterEach, describe, expect, it, vi } from 'vitest'
import { api, ApiError } from './api.js'

function mockFetch(status, body) {
  globalThis.fetch = vi.fn().mockResolvedValue({
    status,
    ok: status < 400,
    json: () => Promise.resolve(body),
  })
}

describe('api client', () => {
  afterEach(() => vi.restoreAllMocks())

  it('builds query strings and skips empty values', async () => {
    mockFetch(200, { items: [] })
    await api.listLocations({ q: 'par', country: '', page: 2 })
    expect(fetch).toHaveBeenCalledWith('/api/v1/locations?q=par&page=2', expect.any(Object))
  })

  it('sends JSON bodies', async () => {
    mockFetch(201, { id: 1 })
    await api.createLocation({ name: 'Rome' })
    const [, options] = fetch.mock.calls[0]
    expect(options.method).toBe('POST')
    expect(options.headers['Content-Type']).toBe('application/json')
    expect(JSON.parse(options.body)).toEqual({ name: 'Rome' })
  })

  it('throws ApiError with field details', async () => {
    mockFetch(422, { message: 'Validation failed.', details: { rating: 'Only visited locations can be rated.' } })
    const error = await api.createLocation({}).catch((e) => e)
    expect(error).toBeInstanceOf(ApiError)
    expect(error.status).toBe(422)
    expect(error.details.rating).toMatch(/visited/)
  })
})
