import { useState, useEffect } from 'react'
import { NavLink, useNavigate } from 'react-router-dom'
import { getUser, clearAuth } from '../api'

export default function Navbar({ theme, onThemeToggle, onAuthClick }) {
  const [user, setUser] = useState(getUser())
  const navigate = useNavigate()

  useEffect(() => {
    const sync = () => setUser(getUser())
    window.addEventListener('auth-change', sync)
    return () => window.removeEventListener('auth-change', sync)
  }, [])

  const handleLogout = () => {
    clearAuth()
    setUser(null)
    window.dispatchEvent(new Event('auth-change'))
    navigate('/')
  }

  return (
    <nav className="navbar">
      <NavLink to="/" className="nav-logo">⚡ evTROUBLESHOOTER</NavLink>
      <div className="nav-links">
        <NavLink to="/" end className={({ isActive }) => isActive ? 'nav-link active' : 'nav-link'}>Diagnose</NavLink>
        <NavLink to="/dashboard" className={({ isActive }) => isActive ? 'nav-link active' : 'nav-link'}>Dashboard</NavLink>
        <NavLink to="/garage" className={({ isActive }) => isActive ? 'nav-link active' : 'nav-link'}>My Garage</NavLink>
      </div>
      <div className="nav-actions">
        <button className="theme-toggle" onClick={onThemeToggle} title="Toggle theme">
          {theme === 'dark' ? '☀️' : '🌙'}
        </button>
        {user ? (
          <div className="nav-user">
            <span className="user-greeting">Hi, {user.full_name?.split(' ')[0] || user.email.split('@')[0]}</span>
            <button className="btn-ghost" onClick={handleLogout}>Logout</button>
          </div>
        ) : (
          <button className="btn-ghost" onClick={onAuthClick}>Login / Register</button>
        )}
      </div>
    </nav>
  )
}
