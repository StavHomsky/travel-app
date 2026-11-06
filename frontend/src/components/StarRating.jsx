// Shows 1-5 stars. If an onChange function is passed, the stars are
// clickable buttons; otherwise they are just a display.
export default function StarRating({ value, onChange }) {
  const stars = [1, 2, 3, 4, 5]

  if (!onChange) {
    return (
      <span className="stars" aria-label={`${value || 0} out of 5 stars`}>
        {stars.map((n) => (
          <span key={n} className={n <= value ? 'on' : ''}>★</span>
        ))}
      </span>
    )
  }

  return (
    <span className="stars">
      {stars.map((n) => (
        <button
          key={n}
          type="button"
          className={n <= value ? 'on' : ''}
          aria-label={`Rate ${n} star${n > 1 ? 's' : ''}`}
          onClick={() => onChange(n)}
        >
          ★
        </button>
      ))}
    </span>
  )
}
