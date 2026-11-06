import { Link } from 'react-router'

export default function NotFoundPage() {
  return (
    <>
      <header className="page-header">
        <h1>404</h1>
        <p>That page does not exist.</p>
      </header>
      <div className="page-header">
        <Link to="/" className="btn btn-primary btn-pill">← Back to dashboard</Link>
      </div>
    </>
  )
}
