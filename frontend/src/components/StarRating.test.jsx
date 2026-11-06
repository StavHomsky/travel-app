import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, expect, it, vi } from 'vitest'
import StarRating from './StarRating.jsx'

describe('StarRating', () => {
  it('shows a read-only rating', () => {
    render(<StarRating value={3} />)
    expect(screen.getByLabelText('3 out of 5 stars')).toBeInTheDocument()
    expect(screen.queryByRole('button')).not.toBeInTheDocument()
  })

  it('reports the clicked star', async () => {
    const onChange = vi.fn()
    render(<StarRating value={2} onChange={onChange} />)
    await userEvent.click(screen.getByLabelText('Rate 4 stars'))
    expect(onChange).toHaveBeenCalledWith(4)
  })
})
