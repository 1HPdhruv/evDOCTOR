import { useEffect, useState } from 'react'
import { apiFetch, getUser } from '../api'
import jsPDF from 'jspdf'

const EV_MAKES = ['Tata', 'MG', 'Hyundai', 'Mahindra', 'BYD', 'Kia', 'Ola Electric', 'Ather', 'Revolt', 'BMW', 'Mercedes', 'Audi', 'Other']
const EV_MODELS = {
  Tata: ['Nexon EV', 'Tiago EV', 'Punch EV', 'Tigor EV', 'Curvv EV'],
  MG: ['ZS EV', 'Comet EV', 'Windsor EV'],
  Hyundai: ['Ioniq 5', 'Kona Electric', 'Creta Electric'],
  Mahindra: ['XUV400', 'BE6', 'XEV9e', 'e2o'],
  BYD: ['Atto 3', 'Seal', 'e6'],
  Kia: ['EV6', 'EV9'],
  'Ola Electric': ['S1 Pro', 'S1 Air', 'S1 X'],
  Ather: ['450X', '450S', 'Rizta'],
  Revolt: ['RV400', 'RV300'],
  BMW: ['iX', 'i4', 'i7', 'iX3'],
  Mercedes: ['EQS', 'EQE', 'EQB', 'EQA'],
  Audi: ['Q8 e-tron', 'e-tron GT', 'Q4 e-tron'],
  Other: ['Other'],
}
const COLORS = ['Pearl White', 'Midnight Black', 'Deep Blue', 'Silver', 'Red', 'Grey', 'Green', 'Other']

function BatteryIndicator({ value }) {
  if (value == null) return <span style={{ color: 'var(--muted)', fontSize: '0.82rem' }}>Not set</span>
  const color = value >= 80 ? 'var(--green)' : value >= 60 ? 'var(--amber)' : 'var(--red)'
  return (
    <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
      <div style={{ flex: 1, height: '8px', background: 'rgba(255,255,255,0.08)', borderRadius: '4px', overflow: 'hidden' }}>
        <div style={{ width: `${value}%`, height: '100%', background: color, borderRadius: '4px', transition: 'width 1s ease' }} />
      </div>
      <span style={{ color, fontWeight: 700, fontSize: '0.85rem', minWidth: '36px' }}>{value}%</span>
    </div>
  )
}

function VehicleCard({ v, onDelete, onUpdate }) {
  const [editMode, setEditMode] = useState(false)
  const [patch, setPatch] = useState({
    mileage: v.mileage || '',
    battery_health: v.battery_health || '',
    color: v.color || '',
    nickname: v.nickname || '',
    service_notes: v.service_notes || '',
  })
  const [saving, setSaving] = useState(false)
  const [diagLoading, setDiagLoading] = useState(false)

  const handleSave = async () => {
    setSaving(true)
    try {
      const res = await apiFetch(`/vehicles/${v.id}`, {
        method: 'PATCH',
        body: JSON.stringify({
          ...patch,
          mileage: patch.mileage ? Number(patch.mileage) : null,
          battery_health: patch.battery_health ? Number(patch.battery_health) : null,
          last_service_date: new Date().toISOString(),
        })
      })
      if (res.ok) {
        const updated = await res.json()
        onUpdate(updated)
        setEditMode(false)
      }
    } catch { /* ignore */ }
    finally { setSaving(false) }
  }

  const downloadCard = () => {
    const doc = new jsPDF()
    doc.setFontSize(18); doc.setTextColor(34, 211, 238)
    doc.text('evTROUBLESHOOTER — Vehicle Health Card', 15, 20)
    doc.setFontSize(12); doc.setTextColor(50, 50, 50)
    doc.text(`Vehicle: ${v.year} ${v.make} ${v.model}`, 15, 35)
    if (v.nickname) doc.text(`Nickname: "${v.nickname}"`, 15, 45)
    if (v.color) doc.text(`Color: ${v.color}`, 15, 55)
    if (v.vin) doc.text(`VIN: ${v.vin}`, 15, 65)
    doc.text(`Mileage: ${v.mileage != null ? v.mileage + ' km' : 'Not recorded'}`, 15, 75)
    doc.text(`Battery Health (SOH): ${v.battery_health != null ? v.battery_health + '%' : 'Not recorded'}`, 15, 85)
    if (v.service_notes) {
      doc.setFontSize(10)
      const lines = doc.splitTextToSize(`Service Notes: ${v.service_notes}`, 170)
      doc.text(lines, 15, 95)
    }
    doc.save(`evDOCTOR_${v.make}_${v.model}_${v.year}.pdf`)
  }

  const diagnoseMakeModel = () => {
    const query = `${v.year} ${v.make} ${v.model}`
    window.location.href = `/?q=${encodeURIComponent(query)}`
  }

  const colorDot = v.color ? (
    <span style={{
      display: 'inline-block', width: '10px', height: '10px', borderRadius: '50%',
      background: v.color.toLowerCase().includes('white') ? '#f8fafc' :
                  v.color.toLowerCase().includes('black') ? '#0f172a' :
                  v.color.toLowerCase().includes('blue') ? '#3b82f6' :
                  v.color.toLowerCase().includes('red') ? '#ef4444' :
                  v.color.toLowerCase().includes('green') ? '#10b981' :
                  v.color.toLowerCase().includes('grey') || v.color.toLowerCase().includes('silver') ? '#94a3b8' : '#a855f7',
      border: '1px solid rgba(255,255,255,0.2)', marginRight: '4px', verticalAlign: 'middle'
    }} />
  ) : null

  return (
    <div className="vehicle-card-enhanced">
      {/* Header */}
      <div className="veh-header">
        <div>
          <div className="vehicle-year">{v.year}</div>
          <div className="vehicle-name">{v.make} {v.model}</div>
          {v.nickname && <div className="vehicle-nick">"{v.nickname}"</div>}
          {v.color && <div style={{ fontSize: '0.78rem', color: 'var(--muted)', marginTop: '2px' }}>{colorDot}{v.color}</div>}
        </div>
        <div className="veh-emoji">
          {v.make === 'Ola Electric' || v.make === 'Ather' || v.make === 'Revolt' ? '🛵' : '🚗'}
        </div>
      </div>

      {/* Stats */}
      <div className="veh-stats">
        <div className="veh-stat">
          <div className="veh-stat-label">Odometer</div>
          <div className="veh-stat-value">{v.mileage != null ? `${v.mileage.toLocaleString()} km` : '—'}</div>
        </div>
        <div className="veh-stat">
          <div className="veh-stat-label">Battery SOH</div>
          <BatteryIndicator value={v.battery_health} />
        </div>
      </div>

      {v.service_notes && (
        <div className="veh-notes">
          <span style={{ fontSize: '0.7rem', color: 'var(--muted)', textTransform: 'uppercase', letterSpacing: '0.5px' }}>Service Notes</span>
          <p style={{ fontSize: '0.82rem', color: 'var(--txt2)', margin: '3px 0 0' }}>{v.service_notes}</p>
        </div>
      )}

      {v.vin && <div className="vehicle-vin">VIN: {v.vin}</div>}

      {/* Edit Mode */}
      {editMode && (
        <div className="veh-edit-form">
          <div className="form-row">
            <input className="auth-input" placeholder="Nickname" value={patch.nickname} onChange={e => setPatch({ ...patch, nickname: e.target.value })} />
            <select className="auth-input" value={patch.color} onChange={e => setPatch({ ...patch, color: e.target.value })}>
              <option value="">Select color</option>
              {COLORS.map(c => <option key={c} value={c}>{c}</option>)}
            </select>
          </div>
          <div className="form-row">
            <input className="auth-input" type="number" placeholder="Mileage (km)" value={patch.mileage} onChange={e => setPatch({ ...patch, mileage: e.target.value })} />
            <input className="auth-input" type="number" placeholder="Battery Health %" min="0" max="100" value={patch.battery_health} onChange={e => setPatch({ ...patch, battery_health: e.target.value })} />
          </div>
          <textarea className="feedback-comment" placeholder="Service notes..." value={patch.service_notes} onChange={e => setPatch({ ...patch, service_notes: e.target.value })} rows={2} />
          <div style={{ display: 'flex', gap: '0.5rem', marginTop: '0.5rem' }}>
            <button className="btn-primary" style={{ maxWidth: '120px', padding: '0.5rem' }} onClick={handleSave} disabled={saving}>{saving ? 'Saving...' : '✓ Save'}</button>
            <button className="btn-ghost" style={{ padding: '0.5rem 1rem' }} onClick={() => setEditMode(false)}>Cancel</button>
          </div>
        </div>
      )}

      {/* Actions */}
      {!editMode && (
        <div className="veh-actions">
          <button className="btn-ghost-sm" onClick={() => setEditMode(true)}>✏️ Edit</button>
          <button className="btn-ghost-sm" onClick={diagnoseMakeModel}>🔍 Diagnose</button>
          <button className="btn-ghost-sm" onClick={downloadCard}>📄 PDF</button>
          <button className="delete-btn" onClick={() => onDelete(v.id)}>✕</button>
        </div>
      )}
    </div>
  )
}

export default function Garage({ onAuthClick }) {
  const user = getUser()
  const [vehicles, setVehicles] = useState([])
  const [saved, setSaved] = useState([])
  const [loading, setLoading] = useState(true)
  const [activeTab, setActiveTab] = useState('vehicles')
  const [form, setForm] = useState({ make: '', model: '', year: new Date().getFullYear(), vin: '', nickname: '', color: '' })
  const [addMode, setAddMode] = useState(false)
  const [expandedSaved, setExpandedSaved] = useState(null)
  const [editNote, setEditNote] = useState('')

  useEffect(() => {
    if (user) loadAll()
    else setLoading(false)
  }, [])

  const loadAll = async () => {
    setLoading(true)
    try {
      const [v, s] = await Promise.all([
        apiFetch('/vehicles').then(r => r.json()),
        apiFetch('/saved').then(r => r.json()),
      ])
      setVehicles(Array.isArray(v) ? v : [])
      setSaved(Array.isArray(s) ? s : [])
    } catch { /* ignore */ }
    finally { setLoading(false) }
  }

  const handleAddVehicle = async (e) => {
    e.preventDefault()
    try {
      const res = await apiFetch('/vehicles', { method: 'POST', body: JSON.stringify({ ...form, year: Number(form.year) }) })
      if (res.ok) {
        setAddMode(false)
        setForm({ make: '', model: '', year: new Date().getFullYear(), vin: '', nickname: '', color: '' })
        loadAll()
      }
    } catch { /* ignore */ }
  }

  const handleDeleteVehicle = async (id) => {
    await apiFetch(`/vehicles/${id}`, { method: 'DELETE' })
    setVehicles(prev => prev.filter(v => v.id !== id))
  }

  const handleUpdateVehicle = (updated) => {
    setVehicles(prev => prev.map(v => v.id === updated.id ? updated : v))
  }

  const handleDeleteSaved = async (id) => {
    await apiFetch(`/saved/${id}`, { method: 'DELETE' })
    setSaved(prev => prev.filter(s => s.id !== id))
  }

  const handleUpdateNote = async (id) => {
    try {
      const s = saved.find(s => s.id === id)
      if (!s) return
      const res = await apiFetch('/saved', {
        method: 'POST',
        body: JSON.stringify({ search_id: s.search_id, notes: editNote })
      })
      if (res.ok) {
        setSaved(prev => prev.map(x => x.id === id ? { ...x, notes: editNote } : x))
        setExpandedSaved(null)
      }
    } catch { /* ignore */ }
  }

  const fmtDate = (d) => d ? new Date(d).toLocaleDateString('en-IN', { day: '2-digit', month: 'short', year: 'numeric' }) : '—'
  const getSeverityColor = (conf) => conf >= 0.7 ? 'var(--red)' : conf >= 0.4 ? 'var(--amber)' : 'var(--green)'

  if (!user) return (
    <div className="container">
      <div className="hero-container">
        <h1 className="hero-title" style={{ fontSize: '2rem' }}>My Garage</h1>
        <p className="hero-subtitle">Login to manage your vehicles and saved diagnoses</p>
        <button className="btn-primary" style={{ maxWidth: '200px', margin: '1rem auto' }} onClick={onAuthClick}>Login / Register</button>
      </div>
    </div>
  )

  const availableModels = EV_MODELS[form.make] || []

  return (
    <div className="container">
      <div className="hero-container" style={{ paddingBottom: '1rem' }}>
        <div className="hero-badge">My Garage</div>
        <h1 className="hero-title" style={{ fontSize: '2.5rem' }}>Vehicles & Saves</h1>
        <p className="hero-subtitle">Manage your EVs, track health, and bookmark important diagnoses</p>
      </div>

      {/* Stats Row */}
      <div className="stats-grid" style={{ marginBottom: '1.5rem' }}>
        <div className="glass-card stat-card">
          <div className="stat-icon">🚗</div>
          <div className="stat-value">{vehicles.length}</div>
          <div className="stat-label">My Vehicles</div>
        </div>
        <div className="glass-card stat-card">
          <div className="stat-icon">🔖</div>
          <div className="stat-value">{saved.length}</div>
          <div className="stat-label">Saved Diagnoses</div>
        </div>
        <div className="glass-card stat-card">
          <div className="stat-icon">🔋</div>
          <div className="stat-value">
            {vehicles.length > 0 && vehicles.some(v => v.battery_health != null)
              ? Math.round(vehicles.filter(v => v.battery_health != null).reduce((s, v) => s + v.battery_health, 0) / vehicles.filter(v => v.battery_health != null).length) + '%'
              : '—'}
          </div>
          <div className="stat-label">Avg Battery SOH</div>
        </div>
      </div>

      {/* Tabs */}
      <div className="garage-tabs">
        <button className={`garage-tab ${activeTab === 'vehicles' ? 'active' : ''}`} onClick={() => setActiveTab('vehicles')}>
          🚗 My Vehicles ({vehicles.length})
        </button>
        <button className={`garage-tab ${activeTab === 'saved' ? 'active' : ''}`} onClick={() => setActiveTab('saved')}>
          🔖 Saved Diagnoses ({saved.length})
        </button>
      </div>

      {/* ── VEHICLES TAB ── */}
      {activeTab === 'vehicles' && (
        <div className="glass-card" style={{ marginTop: '1rem' }}>
          <div className="section-header">
            <h3 className="section-title">My Electric Vehicles</h3>
            <button className="btn-ghost-sm" onClick={() => setAddMode(!addMode)}>
              {addMode ? '✕ Cancel' : '+ Add Vehicle'}
            </button>
          </div>

          {addMode && (
            <form className="add-vehicle-form" onSubmit={handleAddVehicle}>
              <div className="form-row">
                <select className="auth-input" value={form.make} onChange={e => setForm({ ...form, make: e.target.value, model: '' })} required>
                  <option value="">Select Make</option>
                  {EV_MAKES.map(m => <option key={m} value={m}>{m}</option>)}
                </select>
                <select className="auth-input" value={form.model} onChange={e => setForm({ ...form, model: e.target.value })} required>
                  <option value="">Select Model</option>
                  {availableModels.map(m => <option key={m} value={m}>{m}</option>)}
                </select>
                <input className="auth-input" type="number" placeholder="Year" value={form.year} onChange={e => setForm({ ...form, year: e.target.value })} required min="2000" max="2035" />
              </div>
              <div className="form-row">
                <input className="auth-input" placeholder="VIN (optional)" value={form.vin} onChange={e => setForm({ ...form, vin: e.target.value })} />
                <input className="auth-input" placeholder="Nickname (optional)" value={form.nickname} onChange={e => setForm({ ...form, nickname: e.target.value })} />
                <select className="auth-input" value={form.color} onChange={e => setForm({ ...form, color: e.target.value })}>
                  <option value="">Select Color</option>
                  {COLORS.map(c => <option key={c} value={c}>{c}</option>)}
                </select>
              </div>
              <button className="btn-primary" type="submit" style={{ maxWidth: '180px' }}>Add Vehicle</button>
            </form>
          )}

          {loading ? <p className="muted-text">Loading...</p> : vehicles.length === 0 ? (
            <div style={{ textAlign: 'center', padding: '2rem' }}>
              <div style={{ fontSize: '3rem', marginBottom: '0.5rem' }}>🚗</div>
              <p className="muted-text">No vehicles added yet.</p>
              <button className="btn-ghost-sm" style={{ marginTop: '0.75rem' }} onClick={() => setAddMode(true)}>+ Add Your First EV</button>
            </div>
          ) : (
            <div className="vehicles-enhanced-grid">
              {vehicles.map(v => (
                <VehicleCard key={v.id} v={v} onDelete={handleDeleteVehicle} onUpdate={handleUpdateVehicle} />
              ))}
            </div>
          )}
        </div>
      )}

      {/* ── SAVED DIAGNOSES TAB ── */}
      {activeTab === 'saved' && (
        <div className="glass-card" style={{ marginTop: '1rem' }}>
          <h3 className="section-title">🔖 Saved Diagnoses</h3>
          {loading ? <p className="muted-text">Loading...</p> : saved.length === 0 ? (
            <div style={{ textAlign: 'center', padding: '2rem' }}>
              <div style={{ fontSize: '3rem', marginBottom: '0.5rem' }}>🔖</div>
              <p className="muted-text">No saved diagnoses yet.</p>
              <p className="muted-text" style={{ fontSize: '0.82rem', marginTop: '0.5rem' }}>After running a diagnosis, click the <strong>🔖 Save</strong> button in the results.</p>
            </div>
          ) : (
            <div className="saved-list">
              {saved.map(s => (
                <div key={s.id} className={`saved-item ${expandedSaved === s.id ? 'saved-expanded' : ''}`}>
                  <div className="saved-item-main" onClick={() => setExpandedSaved(expandedSaved === s.id ? null : s.id)}>
                    <div className="saved-item-left">
                      <span className="dtc-code-sm" style={{ marginRight: '8px' }}>{s.predicted_code || 'N/A'}</span>
                      <span style={{ fontWeight: 600, color: 'var(--txt)', fontSize: '0.9rem' }}>{s.predicted_issue || 'Unknown Issue'}</span>
                    </div>
                    <div className="saved-item-right">
                      {s.confidence && (
                        <span style={{ fontSize: '0.78rem', color: getSeverityColor(s.confidence), fontWeight: 700 }}>
                          {Math.round(s.confidence * 100)}%
                        </span>
                      )}
                      <span style={{ fontSize: '0.75rem', color: 'var(--muted)', marginLeft: '8px' }}>{fmtDate(s.saved_at)}</span>
                      <span style={{ marginLeft: '8px', color: 'var(--muted)', fontSize: '0.8rem' }}>{expandedSaved === s.id ? '▲' : '▼'}</span>
                    </div>
                  </div>

                  {expandedSaved === s.id && (
                    <div className="saved-item-details">
                      <div style={{ background: 'rgba(255,255,255,0.03)', borderRadius: '8px', padding: '0.75rem', marginBottom: '0.75rem' }}>
                        <div style={{ fontSize: '0.72rem', color: 'var(--muted)', textTransform: 'uppercase', letterSpacing: '0.5px', marginBottom: '4px' }}>Symptom</div>
                        <div style={{ color: 'var(--txt2)', fontSize: '0.88rem' }}>{s.symptom_text || '—'}</div>
                      </div>

                      <div style={{ marginBottom: '0.75rem' }}>
                        <div style={{ fontSize: '0.72rem', color: 'var(--muted)', textTransform: 'uppercase', letterSpacing: '0.5px', marginBottom: '4px' }}>Your Note</div>
                        <textarea
                          className="feedback-comment"
                          placeholder="Add or update your note about this diagnosis..."
                          defaultValue={s.notes || ''}
                          onChange={e => setEditNote(e.target.value)}
                          onFocus={() => setEditNote(s.notes || '')}
                          rows={2}
                        />
                      </div>

                      <div style={{ display: 'flex', gap: '0.5rem', flexWrap: 'wrap' }}>
                        <button className="btn-ghost-sm" onClick={() => handleUpdateNote(s.id)}>💾 Update Note</button>
                        <button className="btn-ghost-sm" onClick={() => {
                          window.location.href = `/?q=${encodeURIComponent(s.symptom_text || '')}`
                        }}>🔍 Re-Diagnose</button>
                        <button className="delete-btn" onClick={() => handleDeleteSaved(s.id)}>✕ Remove</button>
                      </div>
                    </div>
                  )}
                </div>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  )
}
