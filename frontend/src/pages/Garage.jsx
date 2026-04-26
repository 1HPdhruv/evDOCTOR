import { useEffect, useState } from 'react'
import { apiFetch, getUser } from '../api'

export default function Garage({ onAuthClick }) {
  const user = getUser()
  const [vehicles, setVehicles] = useState([])
  const [saved, setSaved] = useState([])
  const [loading, setLoading] = useState(true)
  const [form, setForm] = useState({ make: '', model: '', year: new Date().getFullYear(), vin: '', nickname: '' })
  const [addMode, setAddMode] = useState(false)

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
      if (res.ok) { setAddMode(false); setForm({ make: '', model: '', year: new Date().getFullYear(), vin: '', nickname: '' }); loadAll() }
    } catch { /* ignore */ }
  }

  const handleDeleteVehicle = async (id) => {
    await apiFetch(`/vehicles/${id}`, { method: 'DELETE' })
    loadAll()
  }

  const handleDeleteSaved = async (id) => {
    await apiFetch(`/saved/${id}`, { method: 'DELETE' })
    loadAll()
  }

  if (!user) return (
    <div className="container">
      <div className="hero-container">
        <h1 className="hero-title" style={{ fontSize: '2rem' }}>My Garage</h1>
        <p className="hero-subtitle">Login to manage your vehicles and saved diagnoses</p>
        <button className="btn-primary" style={{ maxWidth: '200px', margin: '1rem auto' }} onClick={onAuthClick}>Login / Register</button>
      </div>
    </div>
  )

  return (
    <div className="container">
      <div className="hero-container" style={{ paddingBottom: '1rem' }}>
        <div className="hero-badge">My Garage</div>
        <h1 className="hero-title" style={{ fontSize: '2.5rem' }}>Vehicles & Saves</h1>
        <p className="hero-subtitle">Manage your EVs and bookmark important diagnoses</p>
      </div>

      {/* Vehicles */}
      <div className="glass-card">
        <div className="section-header">
          <h3 className="section-title">🚗 My Vehicles</h3>
          <button className="btn-ghost-sm" onClick={() => setAddMode(!addMode)}>{addMode ? 'Cancel' : '+ Add Vehicle'}</button>
        </div>

        {addMode && (
          <form className="add-vehicle-form" onSubmit={handleAddVehicle}>
            <div className="form-row">
              <input className="auth-input" placeholder="Make (e.g. Tesla)" value={form.make} onChange={e => setForm({ ...form, make: e.target.value })} required />
              <input className="auth-input" placeholder="Model (e.g. Model 3)" value={form.model} onChange={e => setForm({ ...form, model: e.target.value })} required />
              <input className="auth-input" type="number" placeholder="Year" value={form.year} onChange={e => setForm({ ...form, year: e.target.value })} required />
            </div>
            <div className="form-row">
              <input className="auth-input" placeholder="VIN (optional)" value={form.vin} onChange={e => setForm({ ...form, vin: e.target.value })} />
              <input className="auth-input" placeholder="Nickname (optional)" value={form.nickname} onChange={e => setForm({ ...form, nickname: e.target.value })} />
            </div>
            <button className="btn-primary" type="submit" style={{ maxWidth: '180px' }}>Save Vehicle</button>
          </form>
        )}

        {loading ? <p className="muted-text">Loading...</p> : vehicles.length === 0 ? (
          <p className="muted-text">No vehicles added yet. Click "+ Add Vehicle" above.</p>
        ) : (
          <div className="vehicles-grid">
            {vehicles.map(v => (
              <div key={v.id} className="vehicle-card">
                <div className="vehicle-year">{v.year}</div>
                <div className="vehicle-name">{v.make} {v.model}</div>
                {v.nickname && <div className="vehicle-nick">"{v.nickname}"</div>}
                {v.vin && <div className="vehicle-vin">VIN: {v.vin}</div>}
                <button className="delete-btn" onClick={() => handleDeleteVehicle(v.id)}>✕ Remove</button>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Saved Diagnoses */}
      <div className="glass-card">
        <h3 className="section-title">🔖 Saved Diagnoses</h3>
        {loading ? <p className="muted-text">Loading...</p> : saved.length === 0 ? (
          <p className="muted-text">No saved diagnoses yet. After diagnosing, you can save results from the home page.</p>
        ) : (
          <div className="history-table-wrapper">
            <table className="history-table">
              <thead><tr><th>Symptom</th><th>Issue</th><th>Code</th><th>Confidence</th><th>Notes</th><th></th></tr></thead>
              <tbody>
                {saved.map(s => (
                  <tr key={s.id}>
                    <td className="symptom-cell">{s.symptom_text?.substring(0, 40)}{s.symptom_text?.length > 40 ? '...' : ''}</td>
                    <td>{s.predicted_issue || '—'}</td>
                    <td><span className="dtc-code-sm">{s.predicted_code || '—'}</span></td>
                    <td>{s.confidence ? `${Math.round(s.confidence * 100)}%` : '—'}</td>
                    <td className="muted-text">{s.notes || '—'}</td>
                    <td><button className="delete-btn-sm" onClick={() => handleDeleteSaved(s.id)}>✕</button></td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  )
}
