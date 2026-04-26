import { useEffect, useState } from 'react'
import { API_BASE_URL } from '../api'
import {
  BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer,
  PieChart, Pie, Cell, Legend, LineChart, Line, CartesianGrid,
} from 'recharts'

const COLORS = ['#22d3ee', '#3b82f6', '#a855f7', '#10b981', '#f59e0b', '#ef4444', '#f97316', '#8b5cf6']

export default function Dashboard() {
  const [stats, setStats] = useState(null)
  const [topFaults, setTopFaults] = useState([])
  const [severity, setSeverity] = useState([])
  const [categories, setCategories] = useState([])
  const [daily, setDaily] = useState([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    const load = async () => {
      try {
        const [s, tf, sv, cat, d] = await Promise.all([
          fetch(`${API_BASE_URL}/analytics/stats`).then(r => r.json()),
          fetch(`${API_BASE_URL}/analytics/top-faults?limit=10`).then(r => r.json()),
          fetch(`${API_BASE_URL}/analytics/severity-distribution`).then(r => r.json()),
          fetch(`${API_BASE_URL}/analytics/category-distribution`).then(r => r.json()),
          fetch(`${API_BASE_URL}/analytics/daily-searches?days=7`).then(r => r.json()),
        ])
        setStats(s); setTopFaults(tf); setSeverity(sv); setCategories(cat); setDaily(d)
      } catch (e) { console.error(e) }
      finally { setLoading(false) }
    }
    load()
  }, [])

  if (loading) return <div className="page-center"><div className="loader"></div></div>

  return (
    <div className="container">
      <div className="hero-container" style={{ paddingBottom: '1rem' }}>
        <div className="hero-badge">Analytics</div>
        <h1 className="hero-title" style={{ fontSize: '2.5rem' }}>Dashboard</h1>
        <p className="hero-subtitle">Real-time EV fault trends and platform statistics</p>
      </div>

      {/* Stat Cards */}
      <div className="stats-grid">
        {[
          { label: 'Fault Codes', value: stats?.total_fault_codes ?? 0, icon: '🔧' },
          { label: 'Total Searches', value: stats?.total_searches ?? 0, icon: '🔍' },
          { label: 'Feedback Received', value: stats?.total_feedback ?? 0, icon: '💬' },
          { label: 'Helpfulness', value: `${stats?.helpful_feedback_pct ?? 0}%`, icon: '✅' },
          { label: 'Registered Users', value: stats?.total_users ?? 0, icon: '👤' },
        ].map(({ label, value, icon }) => (
          <div key={label} className="stat-card glass-card">
            <div className="stat-icon">{icon}</div>
            <div className="stat-value">{value}</div>
            <div className="stat-label">{label}</div>
          </div>
        ))}
      </div>

      {/* Top Fault Codes Bar Chart */}
      <div className="glass-card chart-card">
        <h3 className="chart-title">Top Diagnosed Fault Codes</h3>
        {topFaults.length === 0 ? <p className="muted-text">No data yet. Run some diagnoses first.</p> : (
          <ResponsiveContainer width="100%" height={300}>
            <BarChart data={topFaults} margin={{ top: 10, right: 20, bottom: 60, left: 0 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.05)" />
              <XAxis dataKey="code" tick={{ fill: '#94a3b8', fontSize: 11 }} angle={-30} textAnchor="end" interval={0} />
              <YAxis tick={{ fill: '#94a3b8', fontSize: 11 }} allowDecimals={false} />
              <Tooltip contentStyle={{ background: '#111827', border: '1px solid rgba(255,255,255,0.1)', borderRadius: 8, color: '#f1f5f9' }} />
              <Bar dataKey="count" fill="#22d3ee" radius={[4, 4, 0, 0]} />
            </BarChart>
          </ResponsiveContainer>
        )}
      </div>

      <div className="chart-grid">
        {/* Severity Pie */}
        <div className="glass-card chart-card">
          <h3 className="chart-title">Severity Distribution</h3>
          {severity.length === 0 ? <p className="muted-text">No data yet.</p> : (
            <ResponsiveContainer width="100%" height={250}>
              <PieChart>
                <Pie data={severity} dataKey="count" nameKey="label" cx="50%" cy="50%" outerRadius={90} label={({ label, percent }) => `${label} ${(percent * 100).toFixed(0)}%`} labelLine={false}>
                  {severity.map((_, i) => <Cell key={i} fill={COLORS[i % COLORS.length]} />)}
                </Pie>
                <Tooltip contentStyle={{ background: '#111827', border: '1px solid rgba(255,255,255,0.1)', borderRadius: 8, color: '#f1f5f9' }} />
              </PieChart>
            </ResponsiveContainer>
          )}
        </div>

        {/* Daily Searches Line Chart */}
        <div className="glass-card chart-card">
          <h3 className="chart-title">Daily Search Volume (Last 7 Days)</h3>
          {daily.length === 0 ? <p className="muted-text">No data yet.</p> : (
            <ResponsiveContainer width="100%" height={250}>
              <LineChart data={daily}>
                <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.05)" />
                <XAxis dataKey="date" tick={{ fill: '#94a3b8', fontSize: 11 }} />
                <YAxis tick={{ fill: '#94a3b8', fontSize: 11 }} allowDecimals={false} />
                <Tooltip contentStyle={{ background: '#111827', border: '1px solid rgba(255,255,255,0.1)', borderRadius: 8, color: '#f1f5f9' }} />
                <Line type="monotone" dataKey="count" stroke="#22d3ee" strokeWidth={2} dot={{ fill: '#22d3ee', r: 4 }} />
              </LineChart>
            </ResponsiveContainer>
          )}
        </div>
      </div>

      {/* Category Distribution */}
      <div className="glass-card chart-card">
        <h3 className="chart-title">Category Breakdown</h3>
        {categories.length === 0 ? <p className="muted-text">No data yet.</p> : (
          <div className="category-grid">
            {categories.map((c, i) => (
              <div key={c.label} className="category-item">
                <div className="category-bar-bg">
                  <div className="category-bar-fill" style={{ width: `${Math.min(100, (c.count / (categories[0]?.count || 1)) * 100)}%`, background: COLORS[i % COLORS.length] }}></div>
                </div>
                <span className="category-name">{c.label}</span>
                <span className="category-count">{c.count}</span>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  )
}
