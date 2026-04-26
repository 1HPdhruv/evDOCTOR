import { useEffect, useState } from 'react'
import { useParams, Link } from 'react-router-dom'
import { API_BASE_URL } from '../api'

export default function ShareView() {
  const { slug } = useParams()
  const [data, setData] = useState(null)
  const [loading, setLoading] = useState(true)
  const [notFound, setNotFound] = useState(false)

  useEffect(() => {
    fetch(`${API_BASE_URL}/share/${slug}`)
      .then(r => { if (!r.ok) throw new Error(); return r.json() })
      .then(setData)
      .catch(() => setNotFound(true))
      .finally(() => setLoading(false))
  }, [slug])

  if (loading) return <div className="page-center"><div className="loader"></div></div>
  if (notFound) return (
    <div className="page-center">
      <h2 style={{ color: 'var(--accent-red)' }}>Shared diagnosis not found</h2>
      <p className="muted-text" style={{ marginTop: '0.5rem' }}>This link may have expired or been removed.</p>
      <Link to="/" className="btn-primary" style={{ display: 'inline-block', marginTop: '1.5rem', maxWidth: '200px', textDecoration: 'none' }}>Go to Home</Link>
    </div>
  )

  return (
    <div className="container">
      <div className="hero-container">
        <div className="hero-badge">Shared Diagnosis</div>
        <h1 className="hero-title" style={{ fontSize: '2rem' }}>evTROUBLESHOOTER</h1>
      </div>
      <div className="glass-card">
        <p className="tip-text">This diagnosis was shared via evTROUBLESHOOTER</p>
        <div className="share-symptom-box">
          <strong style={{ color: 'var(--text-muted)', fontSize: '0.8rem', textTransform: 'uppercase', letterSpacing: '1px' }}>Symptom</strong>
          <p style={{ marginTop: '0.4rem', color: 'var(--text-primary)' }}>{data.symptom_text}</p>
        </div>
        <div style={{ marginTop: '1.2rem' }}>
          <div className="result-meta" style={{ marginBottom: '0.5rem' }}>
            {data.predicted_code && <span className="dtc-code">{data.predicted_code}</span>}
          </div>
          <h3 className="result-title primary">{data.predicted_issue || 'Unknown Fault'}</h3>
          {data.confidence && (
            <div className="confidence-row" style={{ marginTop: '0.8rem' }}>
              <span className="confidence-label">Confidence: {Math.round(data.confidence * 100)}%</span>
              <div className="confidence-bar-container">
                <div className="confidence-bar-fill conf-high" style={{ width: `${Math.round(data.confidence * 100)}%` }}></div>
              </div>
            </div>
          )}
        </div>
        <div style={{ marginTop: '1.5rem', paddingTop: '1rem', borderTop: '1px solid var(--border-glass)', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <span className="muted-text" style={{ fontSize: '0.8rem' }}>Shared on {new Date(data.searched_at).toLocaleDateString()}</span>
          <Link to="/" className="btn-primary" style={{ display: 'inline-block', maxWidth: '200px', textDecoration: 'none', textAlign: 'center' }}>Try evTROUBLESHOOTER</Link>
        </div>
      </div>
    </div>
  )
}
