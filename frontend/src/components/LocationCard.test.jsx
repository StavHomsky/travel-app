import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter } from 'react-router'
import { describe, expect, it, vi } from 'vitest'
import LocationCard from './LocationCard.jsx'

const base = { id: 1, name: 'Seoul', country: 'South Korea', type: 'city', rating: null, image_url: null }

function renderCard(location, handlers = {}) {
  const props = { onRate: vi.fn(), onMarkVisited: vi.fn(), onDelete: vi.fn(), ...handlers }
  render(<MemoryRouter><LocationCard location={location} {...props} /></MemoryRouter>)
  return props
}

describe('LocationCard', () => {
  it('wishlist places get a TripAdvisor link and a mark-visited button', async () => {
    const { onMarkVisited } = renderCard({ ...base, visited: false })
    const link = screen.getByRole('link', { name: /TripAdvisor/ })
    expect(link).toHaveAttribute('href', 'https://www.tripadvisor.com/Search?q=Seoul%20South%20Korea')
    await userEvent.click(screen.getByRole('button', { name: /Mark visited/ }))
    expect(onMarkVisited).toHaveBeenCalled()
  })

  it('visited places show clickable stars and no TripAdvisor link', async () => {
    const { onRate } = renderCard({ ...base, visited: true, rating: 4 })
    expect(screen.queryByRole('link', { name: /TripAdvisor/ })).not.toBeInTheDocument()
    await userEvent.click(screen.getByLabelText('Rate 5 stars'))
    expect(onRate).toHaveBeenCalledWith(expect.objectContaining({ id: 1 }), 5)
  })

  it('links to the edit page', () => {
    renderCard({ ...base, visited: false })
    expect(screen.getByRole('link', { name: 'Edit' })).toHaveAttribute('href', '/locations/1/edit')
  })
})
