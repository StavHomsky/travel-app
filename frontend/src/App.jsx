import { lazy, Suspense } from 'react'
import { NavLink, Route, Routes } from 'react-router'
import LocationsPage from './pages/LocationsPage.jsx'
import LocationFormPage from './pages/LocationFormPage.jsx'
import ImportPage from './pages/ImportPage.jsx'
import NotFoundPage from './pages/NotFoundPage.jsx'

// Charts (Recharts) and the map (Leaflet) are big libraries, so these two
// pages are downloaded only when the user opens them ("code splitting").
const DashboardPage = lazy(() => import('./pages/DashboardPage.jsx'))
const MapPage = lazy(() => import('./pages/MapPage.jsx'))

// The layout (navbar) is always shown; <Routes> swaps the page below it
// based on the URL - without reloading the browser.
export default function App() {
  return (
    <>
      <nav className="navbar">
        <NavLink to="/" className="navbar-brand">🌍 Location Manager</NavLink>
        <div className="nav-links">
          <NavLink to="/" end>Dashboard</NavLink>
          <NavLink to="/locations">Locations</NavLink>
          <NavLink to="/map">Map</NavLink>
          <NavLink to="/import">Import / Export</NavLink>
        </div>
      </nav>

      <main className="container">
        <Suspense fallback={<p className="loading">Loading…</p>}>
          <Routes>
            <Route path="/" element={<DashboardPage />} />
            <Route path="/locations" element={<LocationsPage />} />
            <Route path="/locations/new" element={<LocationFormPage />} />
            <Route path="/locations/:id/edit" element={<LocationFormPage />} />
            <Route path="/map" element={<MapPage />} />
            <Route path="/import" element={<ImportPage />} />
            <Route path="*" element={<NotFoundPage />} />
          </Routes>
        </Suspense>
      </main>
    </>
  )
}
