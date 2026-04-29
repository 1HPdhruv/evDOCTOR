import { useState, useEffect } from 'react'
import { NavLink, useNavigate } from 'react-router-dom'
import { getUser, clearAuth } from '../api'
import { useTranslation } from 'react-i18next'

export default function Navbar({ theme, onThemeToggle, onAuthClick }) {
  const [user, setUser] = useState(getUser())
  const navigate = useNavigate()
  const { t, i18n } = useTranslation()

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

  const changeLanguage = (lng) => {
    i18n.changeLanguage(lng)
  }

  return (
    <nav className="navbar">
      <NavLink to="/" className="nav-logo">⚡ {t('appTitle', 'evTROUBLESHOOTER')}</NavLink>
      <div className="nav-links">
        <NavLink to="/" end className={({ isActive }) => isActive ? 'nav-link active' : 'nav-link'}>{t('home', 'Diagnose')}</NavLink>
        <NavLink to="/dashboard" className={({ isActive }) => isActive ? 'nav-link active' : 'nav-link'}>{t('dashboard', 'Dashboard')}</NavLink>
        <NavLink to="/garage" className={({ isActive }) => isActive ? 'nav-link active' : 'nav-link'}>{t('garage', 'My Garage')}</NavLink>
      </div>
      <div className="nav-actions">
        <select 
          className="lang-select" 
          value={i18n.resolvedLanguage || 'en'} 
          onChange={(e) => changeLanguage(e.target.value)}
        >
          <option value="en">English</option>
          <option value="hi">हिंदी (HI)</option>
          <option value="bn">বাংলা (BN)</option>
          <option value="ta">தமிழ் (TA)</option>
          <option value="te">తెలుగు (TE)</option>
          <option value="ml">മലയാളം (ML)</option>
          <option value="kn">ಕನ್ನಡ (KN)</option>
          <option value="mr">मराठी (MR)</option>
        </select>
        
        <button className="theme-toggle" onClick={onThemeToggle} title="Toggle theme">
          {theme === 'dark' ? '☀️' : '🌙'}
        </button>
        {user ? (
          <div className="nav-user">
            <span className="user-greeting">Hi, {user.full_name?.split(' ')[0] || user.email.split('@')[0]}</span>
            <button className="btn-ghost" onClick={handleLogout}>Logout</button>
          </div>
        ) : (
          <button className="btn-ghost" onClick={onAuthClick}>{t('login', 'Login / Register')}</button>
        )}
      </div>
    </nav>
  )
}
