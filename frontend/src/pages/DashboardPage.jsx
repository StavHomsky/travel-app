import { useEffect, useState } from 'react'
import { Link } from 'react-router'
import {
  Bar, BarChart, CartesianGrid, Cell, Legend, Pie, PieChart, ResponsiveContainer, Tooltip, XAxis, YAxis,
} from 'recharts'
import { api } from '../api.js'
import Flash from '../components/Flash.jsx'
import { typeIcon } from '../utils.js'

const COLORS = { visited: '#22c55e', wishlist: '#f59e0b', bar: '#6366f1', bar2: '#38bdf8', star: '#facc15' }
const AXIS = { stroke: '#94a3b8', fontSize: 13 }
const TOOLTIP = {
  contentStyle: { background: '#020617', border: '1px solid #334155', borderRadius: 10 },
  itemStyle: { color: '#fff' },
  labelStyle: { color: '#cbd5e1' },
  cursor: { fill: 'rgba(255,255,255,0.05)' },
}

// Recharts wants arrays like [{ name: 'city', count: 5 }], the API gives
// objects like { city: 5 } - this converts, biggest first.
function toRows(counts, label = (key) => key) {
  return Object.entries(counts)
    .map(([key, count]) => ({ name: label(key), count }))
    .sort((a, b) => b.count - a.count)
}

export default function DashboardPage() {
  const [stats, setStats] = useState(null)
  const [error, setError] = useState(null)

  useEffect(() => {
    api.stats().then(setStats).catch((err) => setError({ type: 'error', text: err.message }))
  }, [])

  if (error) return <Flash message={error} />
  if (!stats) return <p className="loading">Loading…</p>

  const statusRows = [
    { name: 'Visited', count: stats.visited, color: COLORS.visited },
    { name: 'Wishlist', count: stats.wishlist, color: COLORS.wishlist },
  ]
  const typeRows = toRows(stats.by_type, (t) => `${typeIcon(t)} ${t}`)
  const countryRows = toRows(stats.by_country)
  const ratingRows = [5, 4, 3, 2, 1].map((n) => ({ name: '★'.repeat(n), count: stats.by_rating[n] || 0 }))

  return (
    <>
      <header className="page-header">
        <h1>🌍</h1>
        <p>Track yourdestinations</p>
      </header>

      <section className="stats-container">
        <StatCard value={stats.total} label="Total Locations" />
        <StatCard value={stats.visited} label="Visited" />
        <StatCard value={stats.wishlist} label="Wishlist" />
        <StatCard value={Object.keys(stats.by_country).length} label="Countries" />
        <StatCard value={stats.average_rating ? `${stats.average_rating}★` : '–'} label="Average Rating" />
      </section>

      {stats.total === 0 ? (
        <div className="page-header">
          <p className="empty-state">No locations yet.</p>
          <Link to="/locations/new" className="btn btn-primary btn-pill">+ Add your first location</Link>
        </div>
      ) : (
        <section className="charts-grid">
          <ChartCard title="Visited vs Wishlist">
            <PieChart>
              <Pie data={statusRows} dataKey="count" nameKey="name" innerRadius={60} outerRadius={100}
                paddingAngle={3} stroke="none">
                {statusRows.map((row) => <Cell key={row.name} fill={row.color} />)}
              </Pie>
              <Tooltip {...TOOLTIP} />
              <Legend formatter={(name, entry) => `${name}: ${entry.payload.count}`} />
            </PieChart>
          </ChartCard>

          <ChartCard title="Locations by Type">
            <BarChart data={typeRows}>
              <CartesianGrid strokeDasharray="3 3" stroke="#334155" />
              <XAxis dataKey="name" {...AXIS} />
              <YAxis allowDecimals={false} {...AXIS} />
              <Tooltip {...TOOLTIP} />
              <Bar dataKey="count" name="Locations" fill={COLORS.bar} radius={[8, 8, 0, 0]} />
            </BarChart>
          </ChartCard>

          <ChartCard title="Locations by Country">
            <BarChart data={countryRows} layout="vertical" margin={{ left: 20 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="#334155" />
              <XAxis type="number" allowDecimals={false} {...AXIS} />
              <YAxis type="category" dataKey="name" width={100} {...AXIS} />
              <Tooltip {...TOOLTIP} />
              <Bar dataKey="count" name="Locations" fill={COLORS.bar2} radius={[0, 8, 8, 0]} />
            </BarChart>
          </ChartCard>

          <ChartCard title="My Ratings">
            <BarChart data={ratingRows} layout="vertical" margin={{ left: 20 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="#334155" />
              <XAxis type="number" allowDecimals={false} {...AXIS} />
              <YAxis type="category" dataKey="name" width={90} {...AXIS} stroke={COLORS.star} />
              <Tooltip {...TOOLTIP} />
              <Bar dataKey="count" name="Places" fill={COLORS.star} radius={[0, 8, 8, 0]} />
            </BarChart>
          </ChartCard>
        </section>
      )}
    </>
  )
}

function StatCard({ value, label }) {
  return (
    <div className="stat-card">
      <h2>{value}</h2>
      <p>{label}</p>
    </div>
  )
}

function ChartCard({ title, children }) {
  return (
    <div className="chart-card">
      <h3>{title}</h3>
      <ResponsiveContainer width="100%" height={280}>
        {children}
      </ResponsiveContainer>
    </div>
  )
}
