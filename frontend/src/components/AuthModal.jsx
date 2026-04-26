import { useState } from 'react'
import { API_BASE_URL, setAuth } from '../api'

export default function AuthModal({ onClose }) {
  const [mode, setMode] = useState('login') // 'login' | 'register'
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [fullName, setFullName] = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)

  const handleSubmit = async (e) => {
    e.preventDefault()
    setLoading(true); setError(null)
    try {
      let res, data
      if (mode === 'register') {
        res = await fetch(`${API_BASE_URL}/auth/register`, {
          method: 'POST', headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ email, password, full_name: fullName }),
        })
      } else {
        // OAuth2 form format for login
        const form = new URLSearchParams()
        form.append('username', email); form.append('password', password)
        res = await fetch(`${API_BASE_URL}/auth/login`, { method: 'POST', body: form })
      }
      data = await res.json()
      if (!res.ok) { setError(data.detail || 'Something went wrong'); return }
      setAuth(data.access_token, { email: data.email, full_name: data.full_name, id: data.user_id })
      window.dispatchEvent(new Event('auth-change'))
      onClose()
    } catch (err) {
      setError('Network error. Is the backend running?')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal-card" onClick={e => e.stopPropagation()}>
        <button className="modal-close" onClick={onClose}>✕</button>
        <h2 className="modal-title">{mode === 'login' ? 'Sign In' : 'Create Account'}</h2>
        <form onSubmit={handleSubmit} className="auth-form">
          {mode === 'register' && (
            <input className="auth-input" type="text" placeholder="Full Name" value={fullName}
              onChange={e => setFullName(e.target.value)} />
          )}
          <input className="auth-input" type="email" placeholder="Email" value={email}
            onChange={e => setEmail(e.target.value)} required />
          <input className="auth-input" type="password" placeholder="Password" value={password}
            onChange={e => setPassword(e.target.value)} required />
          {error && <p className="auth-error">{error}</p>}
          <button className="btn-primary" type="submit" disabled={loading}>
            {loading ? 'Please wait...' : (mode === 'login' ? 'Sign In' : 'Create Account')}
          </button>
        </form>
        <p className="auth-switch">
          {mode === 'login' ? "Don't have an account? " : "Already have an account? "}
          <button className="link-btn" onClick={() => { setMode(mode === 'login' ? 'register' : 'login'); setError(null) }}>
            {mode === 'login' ? 'Register' : 'Login'}
          </button>
        </p>
      </div>
    </div>
  )
}
