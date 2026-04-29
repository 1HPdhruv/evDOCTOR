import { useEffect, useState, useRef } from 'react'
import { Routes, Route } from 'react-router-dom'
import Navbar from './components/Navbar'
import AuthModal from './components/AuthModal'
import Dashboard from './pages/Dashboard'
import Garage from './pages/Garage'
import ShareView from './pages/ShareView'
import ServiceMap from './components/ServiceMap'
import Chatbot from './components/Chatbot'
import { API_BASE_URL, apiFetch, getToken } from './api'
import jsPDF from 'jspdf'
import { useTranslation } from 'react-i18next'
import './App.css'

export default function App() {
  const { t } = useTranslation()
  // ── Theme ──
  const [theme, setTheme] = useState(() => localStorage.getItem('ev_theme') || 'dark')
  useEffect(() => {
    document.body.setAttribute('data-theme', theme)
    localStorage.setItem('ev_theme', theme)
  }, [theme])

  // ── Auth modal ──
  const [showAuth, setShowAuth] = useState(false)

  // ── Diagnosis state ──
  const [symptom, setSymptom] = useState(() => {
    // Support ?q= URL param from Garage "Diagnose" button
    const params = new URLSearchParams(window.location.search)
    return params.get('q') || ''
  })
  const [loading, setLoading] = useState(false)
  const [results, setResults] = useState(null)
  const [error, setError] = useState(null)
  const [searchId, setSearchId] = useState(null)
  const [expertBreakdown, setExpertBreakdown] = useState(null)
  const [showExpert, setShowExpert] = useState(false)

  // ── Feedback ──
  const [feedbackHelpful, setFeedbackHelpful] = useState(null)
  const [feedbackComment, setFeedbackComment] = useState('')
  const [feedbackSubmitted, setFeedbackSubmitted] = useState(false)
  const [feedbackLoading, setFeedbackLoading] = useState(false)

  // ── History ──
  const [history, setHistory] = useState([])
  const [historyCollapsed, setHistoryCollapsed] = useState(false)

  // ── Autocomplete ──
  const [suggestions, setSuggestions] = useState([])
  const [showSuggestions, setShowSuggestions] = useState(false)
  const acTimer = useRef(null)

  // ── Voice ──
  const [listening, setListening] = useState(false)
  const voiceTriggered = useRef(false)

  // ── Share ──
  const [shareSlug, setShareSlug] = useState(null)
  const [shareCopied, setShareCopied] = useState(false)

  useEffect(() => { fetchHistory() }, [])

  // Auto-diagnose after voice input updates the symptom state
  useEffect(() => {
    if (voiceTriggered.current && symptom.trim()) {
      voiceTriggered.current = false
      handleDiagnose(symptom)
    }
  }, [symptom])

  const fetchHistory = async () => {
    try {
      const res = await fetch(`${API_BASE_URL}/history?limit=10`)
      if (res.ok) setHistory(await res.json())
    } catch { /* ignore */ }
  }

  const handleDeleteHistory = async (id) => {
    try {
      const res = await apiFetch(`/history/${id}`, { method: 'DELETE' })
      if (res.ok) {
        setHistory(prev => prev.filter(h => h.id !== id))
      }
    } catch { /* ignore */ }
  }

  // ── Autocomplete handler ──
  const handleSymptomChange = (val) => {
    setSymptom(val)
    clearTimeout(acTimer.current)
    if (val.length < 2) { setSuggestions([]); setShowSuggestions(false); return }
    acTimer.current = setTimeout(async () => {
      try {
        const res = await fetch(`${API_BASE_URL}/autocomplete?q=${encodeURIComponent(val)}&limit=6`)
        if (res.ok) {
          const data = await res.json()
          setSuggestions(data)
          setShowSuggestions(data.length > 0)
        }
      } catch { /* ignore */ }
    }, 250)
  }

  const handleVoice = () => {
    if (!('webkitSpeechRecognition' in window || 'SpeechRecognition' in window)) {
      alert('Voice input not supported in this browser. Try Chrome.')
      return
    }
    const SR = window.SpeechRecognition || window.webkitSpeechRecognition
    const rec = new SR()
    rec.lang = 'en-US'; rec.interimResults = false
    setListening(true)
    rec.onresult = (e) => {
      const transcript = e.results[0][0].transcript;
      voiceTriggered.current = true;
      setListening(false);
      setSymptom(transcript);
    }
    rec.onerror = () => setListening(false)
    rec.onend = () => setListening(false)
    rec.start()
  }

  // ── Diagnose ──
  const handleDiagnose = async (overrideText = null) => {
    const textToDiagnose = typeof overrideText === 'string' ? overrideText : symptom;
    if (!textToDiagnose.trim()) { setError('Please enter your EV symptoms.'); return }
    setLoading(true); setError(null); setResults(null); setShareSlug(null)
    setFeedbackSubmitted(false); setFeedbackHelpful(null); setFeedbackComment('')
    setExpertBreakdown(null); setShowExpert(false)
    setShowSuggestions(false)
    try {
      const res = await apiFetch('/diagnose', {
        method: 'POST', body: JSON.stringify({ symptom_text: textToDiagnose }),
      })
      const data = await res.json()
      if (!data.success) setError(data.message || 'Diagnosis failed.')
      else {
        setResults(data.results)
        setSearchId(data.search_id || null)
        setExpertBreakdown(data.expert_breakdown || null)
        fetchHistory()
      }
    } catch { setError('Network error. Is the backend running?') }
    finally { setLoading(false) }
  }

  // ── Feedback ──
  const handleFeedback = async () => {
    if (feedbackHelpful === null || !results?.length) return
    setFeedbackLoading(true)
    try {
      const res = await apiFetch('/feedback', {
        method: 'POST',
        body: JSON.stringify({ symptom_text: symptom, predicted_issue: results[0].issue, was_helpful: feedbackHelpful, comment: feedbackComment || null }),
      })
      if (res.ok) setFeedbackSubmitted(true)
    } catch { /* ignore */ }
    finally { setFeedbackLoading(false) }
  }

  // ── Share ──
  const handleShare = async () => {
    if (!searchId) return
    try {
      const res = await apiFetch('/share', { method: 'POST', body: JSON.stringify({ search_id: searchId }) })
      const data = await res.json()
      const url = `${window.location.origin}/share/${data.slug}`
      setShareSlug(url)
      await navigator.clipboard.writeText(url)
      setShareCopied(true)
      setTimeout(() => setShareCopied(false), 3000)
    } catch { /* ignore */ }
  }

  // ── Bookmark / Save Diagnosis ──
  const [bookmarkSaved, setBookmarkSaved] = useState(false)
  const [bookmarkLoading, setBookmarkLoading] = useState(false)
  const [showBookmarkModal, setShowBookmarkModal] = useState(false)
  const [bookmarkNote, setBookmarkNote] = useState('')

  const handleSaveDiagnosis = async () => {
    if (!searchId) return
    setBookmarkLoading(true)
    try {
      const res = await apiFetch('/saved', {
        method: 'POST',
        body: JSON.stringify({ search_id: searchId, notes: bookmarkNote || null })
      })
      if (res.ok) {
        setBookmarkSaved(true)
        setShowBookmarkModal(false)
        setBookmarkNote('')
        setTimeout(() => setBookmarkSaved(false), 3000)
      }
    } catch { /* ignore */ }
    finally { setBookmarkLoading(false) }
  }

  // ── PDF Download ──
  const handlePDF = () => {
    if (!results?.length) return
    const doc = new jsPDF()
    doc.setFontSize(18); doc.setTextColor(34, 211, 238)
    doc.text('evTROUBLESHOOTER Diagnosis Report', 15, 20)
    doc.setFontSize(10); doc.setTextColor(100, 100, 100)
    doc.text(`Generated: ${new Date().toLocaleString()}`, 15, 28)
    doc.setFontSize(11); doc.setTextColor(0)
    doc.text(`Symptom: ${symptom}`, 15, 40)
    let y = 52
    results.forEach((r, i) => {
      if (y > 250) { doc.addPage(); y = 20 }
      doc.setFontSize(13); doc.setTextColor(59, 130, 246)
      doc.text(`${i + 1}. ${r.code} — ${r.issue}`, 15, y); y += 8
      doc.setFontSize(10); doc.setTextColor(80)
      doc.text(`Severity: ${r.severity} | Category: ${r.category} | Confidence: ${Math.round(r.confidence * 100)}%`, 15, y); y += 7
      doc.setTextColor(0)
      doc.text(`Fix: ${r.fix}`, 15, y, { maxWidth: 180 }); y += 10
      if (r.steps?.length) {
        doc.text('Steps:', 15, y); y += 6
        r.steps.forEach((s, si) => { doc.text(`  ${si + 1}. ${s}`, 15, y, { maxWidth: 175 }); y += 6 })
      }
      y += 6
    })
    doc.save(`evTROUBLESHOOTER_${results[0].code}_${Date.now()}.pdf`)
  }

  // ── Helpers ──
  const getConfClass = (c) => c >= 0.6 ? 'conf-high' : c >= 0.3 ? 'conf-medium' : 'conf-low'
  const fmtDate = (d) => new Date(d).toLocaleDateString('en-IN', { day: '2-digit', month: 'short', year: 'numeric', hour: '2-digit', minute: '2-digit' })

  return (
    <>
      <Navbar theme={theme} onThemeToggle={() => setTheme(t => t === 'dark' ? 'light' : 'dark')} onAuthClick={() => setShowAuth(true)} />
      {showAuth && <AuthModal onClose={() => setShowAuth(false)} />}

      <Routes>
        <Route path="/dashboard" element={<Dashboard />} />
        <Route path="/garage" element={<Garage onAuthClick={() => setShowAuth(true)} />} />
        <Route path="/share/:slug" element={<ShareView />} />
        <Route path="/" element={
          <div className="container">
            {/* Hero */}
            <div className="hero-container">
              <div className="hero-badge">AI-Powered Diagnostics</div>
              <h1 className="hero-title">{t('appTitle', 'evTROUBLESHOOTER')}</h1>
              <p className="hero-subtitle">{t('heroSubtitle', 'Describe your EV symptoms — get an instant AI diagnosis with step-by-step troubleshooting')}</p>
            </div>

            {/* Input */}
            <div className="glass-card" style={{ position: 'relative' }}>
              <p className="tip-text"><strong>Tip:</strong> Describe sounds, warnings, error lights, performance changes.</p>
              <div className="input-row">
                <textarea className="textarea-field" value={symptom}
                  onChange={(e) => handleSymptomChange(e.target.value)}
                  placeholder={t('placeholder', 'e.g. battery not charging, range dropped, motor making noise...')}
                  onKeyDown={(e) => { if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); handleDiagnose() } }}
                  onBlur={() => setTimeout(() => setShowSuggestions(false), 150)} />
                <button className={`voice-btn ${listening ? 'listening' : ''}`} onClick={handleVoice} title="Voice input">
                  {listening ? '🔴' : '🎤'}
                </button>
              </div>
              {showSuggestions && suggestions.length > 0 && (
                <ul className="autocomplete-list">
                  {suggestions.map((s, i) => (
                    <li key={i} className="autocomplete-item" onMouseDown={() => { setSymptom(s); setShowSuggestions(false) }}>{s}</li>
                  ))}
                </ul>
              )}
              <div className="btn-wrapper">
                <button className="btn-primary" onClick={handleDiagnose} disabled={loading}>
                  {loading ? <><span className="scanner-ring"></span> {t('scanning', 'Scanning...')}</> : `⚡ ${t('diagnoseBtn', 'Diagnose Now')}`}
                </button>
              </div>
            </div>

            {error && <div className="error-message"><span className="error-icon">!</span> {error}</div>}

            {/* Results */}
            {results?.length > 0 && (
              <div className="results-container">
                <div className="results-header">
                  <h2 className="section-title">Diagnosis Results</h2>
                  <div className="results-actions">
                    {expertBreakdown && (
                      <button className="btn-ghost-sm" onClick={() => setShowExpert(x => !x)}>
                        {showExpert ? 'Hide' : 'Show'} Expert Mode
                      </button>
                    )}
                    <button className="btn-ghost-sm" onClick={handlePDF}>⬇ PDF</button>
                    {searchId && <button className="btn-ghost-sm" onClick={handleShare}>{shareCopied ? '✓ Copied!' : '🔗 Share'}</button>}
                    {searchId && (
                      <button
                        className={`btn-ghost-sm ${bookmarkSaved ? 'bookmark-saved' : ''}`}
                        onClick={() => setShowBookmarkModal(true)}
                        disabled={bookmarkSaved}
                      >
                        {bookmarkSaved ? '🔖 Saved!' : '🔖 Save'}
                      </button>
                    )}
                  </div>
                </div>
                {shareSlug && <div className="share-banner">Shareable link: <code>{shareSlug}</code></div>}

                {/* Bookmark Modal */}
                {showBookmarkModal && (
                  <div className="modal-overlay" onClick={() => setShowBookmarkModal(false)}>
                    <div className="modal-card" onClick={e => e.stopPropagation()}>
                      <button className="modal-close" onClick={() => setShowBookmarkModal(false)}>×</button>
                      <h3 className="modal-title">🔖 Save Diagnosis</h3>
                      <p style={{ color: 'var(--txt2)', fontSize: '0.9rem', marginBottom: '1rem' }}>
                        Save this diagnosis to <strong>My Garage → Saved Diagnoses</strong> for future reference.
                      </p>
                      <textarea
                        className="feedback-comment"
                        placeholder="Add a note (optional) — e.g. 'Happened after rain', 'Fixed by dealer'"
                        value={bookmarkNote}
                        onChange={e => setBookmarkNote(e.target.value)}
                        rows={3}
                        style={{ marginBottom: '1rem' }}
                      />
                      <button
                        className="btn-primary"
                        style={{ maxWidth: '100%' }}
                        onClick={handleSaveDiagnosis}
                        disabled={bookmarkLoading}
                      >
                        {bookmarkLoading ? 'Saving...' : '🔖 Save to My Garage'}
                      </button>
                    </div>
                  </div>
                )}


                {/* Expert Mode Panel */}
                {showExpert && expertBreakdown && (
                  <div className="expert-panel glass-card">
                    <h4 className="expert-title">Expert Mode — Per-Model Confidence (Top Prediction)</h4>
                    <div className="expert-bars">
                      {[['Logistic Regression', expertBreakdown.lr, 'var(--accent-cyan)'],
                      ['SGD Classifier', expertBreakdown.sgd, 'var(--accent-purple)'],
                      ['Naive Bayes', expertBreakdown.nb, 'var(--accent-amber)']].map(([name, val, color]) => (
                        <div key={name} className="expert-row">
                          <span className="expert-label">{name}</span>
                          <div className="expert-bar-bg">
                            <div className="expert-bar-fill" style={{ width: `${Math.round(val * 100)}%`, background: color }}></div>
                          </div>
                          <span className="expert-pct">{Math.round(val * 100)}%</span>
                        </div>
                      ))}
                    </div>
                  </div>
                )}

                {results.map((r, i) => {
                  const pct = Math.round(r.confidence * 100), sev = r.severity.toLowerCase(), rank = i + 1
                  return (
                    <div key={i} className={`result-card severity-${sev}`} style={{ animationDelay: `${i * 0.12}s` }}>
                      <div className={`rank-badge rank-${rank}-badge`}>{rank}</div>
                      <div className="result-meta">
                        <span className="dtc-code">{r.code}</span>
                        <span className={`severity-badge ${sev}`}>{r.severity}</span>
                        <span className="category-pill">{r.category}</span>
                      </div>
                      <h3 className={`result-title ${rank === 1 ? 'primary' : ''}`}>{r.issue}</h3>
                      <div className="confidence-row">
                        <span className="confidence-label">Confidence: {pct}%</span>
                        <div className="confidence-bar-container">
                          <div className={`confidence-bar-fill ${getConfClass(r.confidence)}`} style={{ width: `${pct}%` }}></div>
                        </div>
                      </div>
                      <div className="fix-box"><div className="fix-label">Suggested Fix</div><div className="fix-text">{r.fix}</div></div>
                      {r.steps?.length > 0 && (
                        <div className="steps-section">
                          <h4 className="steps-heading">Troubleshooting Steps</h4>
                          <div className="steps-list">
                            {r.steps.map((s, si) => <div className="step-item" key={si}><div className="step-number">{si + 1}</div><div className="step-text">{s}</div></div>)}
                          </div>
                        </div>
                      )}
                    </div>
                  )
                })}

                {/* Map Integration */}
                <ServiceMap />

                {/* Feedback */}
                <div className="glass-card feedback-card">
                  <h3 className="feedback-title">Was this diagnosis helpful?</h3>
                  {feedbackSubmitted ? (
                    <div className="feedback-success">✓ Thank you for your feedback!</div>
                  ) : (<>
                    <div className="feedback-buttons">
                      <button className={`feedback-btn ${feedbackHelpful === true ? 'active-yes' : ''}`} onClick={() => setFeedbackHelpful(true)}>👍 Yes</button>
                      <button className={`feedback-btn ${feedbackHelpful === false ? 'active-no' : ''}`} onClick={() => setFeedbackHelpful(false)}>👎 No</button>
                    </div>
                    <textarea className="feedback-comment" placeholder="Comments (optional)..." value={feedbackComment} onChange={(e) => setFeedbackComment(e.target.value)} rows={2} />
                    <button className="btn-secondary" onClick={handleFeedback} disabled={feedbackHelpful === null || feedbackLoading}>
                      {feedbackLoading ? 'Submitting...' : 'Submit Feedback'}
                    </button>
                  </>)}
                </div>
              </div>
            )}

            {/* Recent Searches */}
            <div className="glass-card history-card">
              <div className="history-header">
                <h3 className="section-title">{t('recentSearches', 'Recent Searches')}</h3>
                <button 
                  className="collapse-btn" 
                  onClick={() => setHistoryCollapsed(!historyCollapsed)}
                  title={historyCollapsed ? "Expand" : "Collapse"}
                >
                  {historyCollapsed ? "▼" : "▲"}
                </button>
              </div>
              
              {!historyCollapsed && (
                history.length === 0 ? <p className="muted-text">{t('noSearches', 'No searches yet. Run a diagnosis to see history here.')}</p> : (
                  <div className="history-table-wrapper">
                    <table className="history-table">
                      <thead><tr><th>{t('symptom', 'Symptom')}</th><th>{t('issue', 'Issue')}</th><th>{t('code', 'Code')}</th><th>{t('confidence', 'Confidence')}</th><th>{t('date', 'Date')}</th><th></th></tr></thead>
                      <tbody>
                        {history.map((h) => (
                          <tr key={h.id}>
                            <td className="symptom-cell">{h.symptom_text?.substring(0, 45)}{h.symptom_text?.length > 45 ? '...' : ''}</td>
                            <td>{h.predicted_issue || '—'}</td>
                            <td><span className="dtc-code-sm">{h.predicted_code || '—'}</span></td>
                            <td>{h.confidence ? `${Math.round(h.confidence * 100)}%` : '—'}</td>
                            <td className="date-cell">{fmtDate(h.searched_at)}</td>
                            <td className="action-cell">
                              <button 
                                className="delete-history-btn" 
                                onClick={() => handleDeleteHistory(h.id)}
                                title="Remove search"
                              >
                                ×
                              </button>
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                )
              )}
            </div>

            <footer className="footer">
              <strong>evTROUBLESHOOTER</strong> — AI-Powered EV Fault Diagnosis<br />
              React + FastAPI + Ensemble ML + JWT Auth + PWA &bull; 127+ Fault Codes<br /><br />
              Made by <a href="https://github.com/1HPdhruv" target="_blank" rel="noreferrer">Dhruv</a>
            </footer>
          </div>
        } />
      </Routes>
      <Chatbot />
    </>
  )
}
