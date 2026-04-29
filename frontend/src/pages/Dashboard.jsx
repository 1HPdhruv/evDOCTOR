import { useEffect, useState } from 'react'
import { API_BASE_URL } from '../api'
import {
  PieChart, Pie, Cell, Tooltip, ResponsiveContainer,
  LineChart, Line, CartesianGrid, XAxis, YAxis,
  BarChart, Bar
} from 'recharts'

const COLORS = ['#22d3ee', '#3b82f6', '#a855f7', '#10b981', '#f59e0b', '#ef4444', '#f97316', '#8b5cf6']

const SEVERITY_CONFIG = {
  Critical: { color: '#ef4444', bg: 'rgba(239,68,68,0.12)', icon: '🔴', label: 'Critical' },
  High:     { color: '#f97316', bg: 'rgba(249,115,22,0.12)', icon: '🟠', label: 'High' },
  Medium:   { color: '#f59e0b', bg: 'rgba(245,158,11,0.12)', icon: '🟡', label: 'Medium' },
  Low:      { color: '#10b981', bg: 'rgba(16,185,129,0.12)', icon: '🟢', label: 'Low' },
  Unknown:  { color: '#94a3b8', bg: 'rgba(148,163,184,0.08)', icon: '⚪', label: 'Unknown' },
}

const CATEGORY_ICONS = {
  Battery:       '🔋',
  Motor:         '⚙️',
  Charging:      '⚡',
  BMS:           '🖥️',
  Thermal:       '🌡️',
  'High Voltage':'⚠️',
  Drivetrain:    '🔩',
  Communication: '📡',
  Safety:        '🛡️',
  Brake:         '🛑',
  Suspension:    '🔧',
  Software:      '💾',
  Unknown:       '❓',
}

// Human-friendly card for each problem
function ProblemCard({ item, rank }) {
  const sev = SEVERITY_CONFIG[item.severity] || SEVERITY_CONFIG.Unknown
  const catIcon = Object.entries(CATEGORY_ICONS).find(([k]) => item.category?.toLowerCase().includes(k.toLowerCase()))?.[1] || '🔧'

  return (
    <div className="problem-card" style={{ borderLeft: `3px solid ${sev.color}` }}>
      <div className="problem-card-rank">#{rank}</div>
      <div className="problem-card-body">
        <div className="problem-card-top">
          <span className="problem-cat-icon">{catIcon}</span>
          <span className="problem-issue">{item.issue}</span>
          <span className="problem-sev-badge" style={{ background: sev.bg, color: sev.color }}>
            {sev.icon} {sev.label}
          </span>
        </div>
        <div className="problem-card-meta">
          <span className="problem-code">Code: <code>{item.code}</code></span>
          <span className="problem-cat">{item.category}</span>
          <span className="problem-count-badge">{item.count} {item.count === 1 ? 'report' : 'reports'}</span>
        </div>
        <div className="problem-bar-track">
          <div
            className="problem-bar-fill"
            style={{ width: `${Math.min(100, item._pct || 0)}%`, background: sev.color }}
          />
        </div>
      </div>
    </div>
  )
}

const CustomTooltip = ({ active, payload, label }) => {
  if (!active || !payload?.length) return null
  return (
    <div style={{ background: '#0f172a', border: '1px solid rgba(255,255,255,0.1)', borderRadius: '8px', padding: '10px 14px', fontSize: '0.85rem' }}>
      <div style={{ color: '#94a3b8', marginBottom: '4px' }}>{label}</div>
      {payload.map((p, i) => (
        <div key={i} style={{ color: p.color || '#22d3ee', fontWeight: 700 }}>{p.name}: {p.value}</div>
      ))}
    </div>
  )
}

export default function Dashboard() {
  const [stats, setStats] = useState(null)
  const [topFaults, setTopFaults] = useState([])
  const [severity, setSeverity] = useState([])
  const [categories, setCategories] = useState([])
  const [daily, setDaily] = useState([])
  const [loading, setLoading] = useState(true)
  const [activeTab, setActiveTab] = useState('overview')

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
        setStats(s)
        // Compute percentage for bar fill
        const maxCount = tf[0]?.count || 1
        setTopFaults(tf.map(f => ({ ...f, _pct: Math.round((f.count / maxCount) * 100) })))
        setSeverity(sv)
        setCategories(cat)
        setDaily(d)
      } catch (e) { console.error(e) }
      finally { setLoading(false) }
    }
    load()
  }, [])

  if (loading) return <div className="page-center"><div className="loader"></div></div>

  // Quick tip derived from top fault
  const topProblem = topFaults[0]
  const weekTotal = daily.reduce((s, d) => s + d.count, 0)
  const critCount = topFaults.filter(f => f.severity === 'Critical').length

  return (
    <div className="container">
      <div className="hero-container" style={{ paddingBottom: '1rem' }}>
        <div className="hero-badge">Analytics</div>
        <h1 className="hero-title" style={{ fontSize: '2.5rem' }}>Dashboard</h1>
        <p className="hero-subtitle">Real-time EV health trends and community insights</p>
      </div>

      {/* Stat Cards */}
      <div className="stats-grid">
        {[
          { label: 'Known Fault Codes', value: stats?.total_fault_codes ?? 0, icon: '🔧', sub: 'in database' },
          { label: 'Diagnoses Run', value: stats?.total_searches ?? 0, icon: '🔍', sub: 'total searches' },
          { label: 'User Feedback', value: stats?.total_feedback ?? 0, icon: '💬', sub: 'responses' },
          { label: 'Helpful Rate', value: `${stats?.helpful_feedback_pct ?? 0}%`, icon: '✅', sub: 'accuracy' },
          { label: 'Registered Users', value: stats?.total_users ?? 0, icon: '👤', sub: 'accounts' },
        ].map(({ label, value, icon, sub }) => (
          <div key={label} className="stat-card glass-card">
            <div className="stat-icon">{icon}</div>
            <div className="stat-value">{value}</div>
            <div className="stat-label">{label}</div>
            <div style={{ fontSize: '0.72rem', color: 'var(--muted)', marginTop: '2px' }}>{sub}</div>
          </div>
        ))}
      </div>

      {/* Insight Banner */}
      {topProblem && (
        <div className="glass-card insight-banner">
          <span className="insight-icon">💡</span>
          <div>
            <strong>Community Insight:</strong> The most commonly reported EV issue this period is{' '}
            <strong style={{ color: 'var(--cyan)' }}>{topProblem.issue}</strong> ({topProblem.count} reports).
            {critCount > 0 && <> There are <strong style={{ color: '#ef4444' }}>{critCount} critical</strong> issues in the top 10 — prompt attention recommended.</>}
            {weekTotal > 0 && <> Total diagnoses this week: <strong style={{ color: 'var(--cyan)' }}>{weekTotal}</strong>.</>}
          </div>
        </div>
      )}

      {/* Sub-tabs */}
      <div className="garage-tabs" style={{ marginTop: '1.5rem', marginBottom: '1rem' }}>
        <button className={`garage-tab ${activeTab === 'overview' ? 'active' : ''}`} onClick={() => setActiveTab('overview')}>
          ⚠️ Common Problems
        </button>
        <button className={`garage-tab ${activeTab === 'trends' ? 'active' : ''}`} onClick={() => setActiveTab('trends')}>
          📈 Trends
        </button>
        <button className={`garage-tab ${activeTab === 'categories' ? 'active' : ''}`} onClick={() => setActiveTab('categories')}>
          🗂️ Categories
        </button>
      </div>

      {/* ── COMMON PROBLEMS TAB ── */}
      {activeTab === 'overview' && (
        <div className="glass-card chart-card">
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1rem' }}>
            <div>
              <h3 className="chart-title" style={{ marginBottom: '2px' }}>⚠️ Most Reported EV Problems</h3>
              <p style={{ color: 'var(--muted)', fontSize: '0.82rem', margin: 0 }}>Based on real diagnosis data from users like you</p>
            </div>
          </div>

          {topFaults.length === 0 ? (
            <div style={{ textAlign: 'center', padding: '2rem' }}>
              <div style={{ fontSize: '3rem', marginBottom: '0.5rem' }}>🔍</div>
              <p className="muted-text">No diagnosis data yet. Run some diagnoses from the home page first.</p>
            </div>
          ) : (
            <div className="problems-list">
              {topFaults.map((item, i) => (
                <ProblemCard key={item.code} item={item} rank={i + 1} />
              ))}
            </div>
          )}

          {/* Legend */}
          <div className="problem-legend">
            {Object.entries(SEVERITY_CONFIG).filter(([k]) => k !== 'Unknown').map(([key, cfg]) => (
              <span key={key} style={{ display: 'inline-flex', alignItems: 'center', gap: '4px', fontSize: '0.78rem', color: cfg.color }}>
                {cfg.icon} {cfg.label}
              </span>
            ))}
          </div>
        </div>
      )}

      {/* ── TRENDS TAB ── */}
      {activeTab === 'trends' && (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
          {/* Daily Searches */}
          <div className="glass-card chart-card">
            <h3 className="chart-title">📅 Diagnosis Activity — Last 7 Days</h3>
            <p style={{ color: 'var(--muted)', fontSize: '0.82rem', marginBottom: '1rem' }}>How many people ran EV diagnoses each day</p>
            {daily.length === 0 ? <p className="muted-text">No data yet.</p> : (
              <ResponsiveContainer width="100%" height={250}>
                <LineChart data={daily}>
                  <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.05)" />
                  <XAxis dataKey="date" tick={{ fill: '#94a3b8', fontSize: 11 }} />
                  <YAxis tick={{ fill: '#94a3b8', fontSize: 11 }} allowDecimals={false} />
                  <Tooltip content={<CustomTooltip />} />
                  <Line type="monotone" dataKey="count" name="Diagnoses" stroke="#22d3ee" strokeWidth={2.5} dot={{ fill: '#22d3ee', r: 5 }} activeDot={{ r: 7 }} />
                </LineChart>
              </ResponsiveContainer>
            )}
          </div>

          {/* Severity Bar Chart */}
          <div className="glass-card chart-card">
            <h3 className="chart-title">🚦 How Serious Are the Problems?</h3>
            <p style={{ color: 'var(--muted)', fontSize: '0.82rem', marginBottom: '1rem' }}>
              Breakdown of fault severity — <span style={{ color: '#ef4444' }}>Critical</span> means drive to a service center now, <span style={{ color: '#10b981' }}>Low</span> can wait.
            </p>
            {severity.length === 0 ? <p className="muted-text">No data yet.</p> : (
              <ResponsiveContainer width="100%" height={220}>
                <BarChart data={severity} layout="vertical" margin={{ left: 10, right: 30 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.05)" horizontal={false} />
                  <XAxis type="number" tick={{ fill: '#94a3b8', fontSize: 11 }} allowDecimals={false} />
                  <YAxis type="category" dataKey="label" tick={{ fill: '#94a3b8', fontSize: 12 }} width={70} />
                  <Tooltip content={<CustomTooltip />} />
                  <Bar dataKey="count" name="Count" radius={[0, 4, 4, 0]}>
                    {severity.map((s, i) => {
                      const cfg = SEVERITY_CONFIG[s.label] || SEVERITY_CONFIG.Unknown
                      return <Cell key={i} fill={cfg.color} />
                    })}
                  </Bar>
                </BarChart>
              </ResponsiveContainer>
            )}
          </div>
        </div>
      )}

      {/* ── CATEGORIES TAB ── */}
      {activeTab === 'categories' && (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
          {/* Pie Chart */}
          <div className="glass-card chart-card">
            <h3 className="chart-title">🗂️ Which EV System Has the Most Issues?</h3>
            <p style={{ color: 'var(--muted)', fontSize: '0.82rem', marginBottom: '1rem' }}>Fault distribution across EV subsystems — battery, motor, charging, etc.</p>
            {categories.length === 0 ? <p className="muted-text">No data yet.</p> : (
              <ResponsiveContainer width="100%" height={260}>
                <PieChart>
                  <Pie
                    data={categories}
                    dataKey="count"
                    nameKey="label"
                    cx="50%"
                    cy="50%"
                    outerRadius={100}
                    label={({ label, percent }) => percent > 0.05 ? `${label} ${(percent * 100).toFixed(0)}%` : ''}
                    labelLine={false}
                  >
                    {categories.map((_, i) => <Cell key={i} fill={COLORS[i % COLORS.length]} />)}
                  </Pie>
                  <Tooltip content={<CustomTooltip />} />
                </PieChart>
              </ResponsiveContainer>
            )}
          </div>

          {/* Category breakdown bars */}
          <div className="glass-card chart-card">
            <h3 className="chart-title">Subsystem Breakdown</h3>
            <div className="category-grid">
              {categories.map((c, i) => {
                const catIcon = Object.entries(CATEGORY_ICONS).find(([k]) => c.label?.toLowerCase().includes(k.toLowerCase()))?.[1] || '🔧'
                const pct = Math.min(100, Math.round((c.count / (categories[0]?.count || 1)) * 100))
                return (
                  <div key={c.label} className="category-item">
                    <span style={{ fontSize: '1rem', width: '24px' }}>{catIcon}</span>
                    <span className="category-name">{c.label}</span>
                    <div className="category-bar-bg" style={{ flex: 1 }}>
                      <div className="category-bar-fill" style={{ width: `${pct}%`, background: COLORS[i % COLORS.length] }} />
                    </div>
                    <span className="category-count">{c.count}</span>
                  </div>
                )
              })}
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
