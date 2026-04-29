import React, { useEffect, useState, useCallback } from 'react';
import { MapContainer, TileLayer, Marker, Popup, useMap } from 'react-leaflet';
import 'leaflet/dist/leaflet.css';
import { apiFetch } from '../api';

// Fix for default marker icons in React-Leaflet
import L from 'leaflet';
import icon from 'leaflet/dist/images/marker-icon.png';
import iconShadow from 'leaflet/dist/images/marker-shadow.png';

let DefaultIcon = L.icon({
  iconUrl: icon,
  shadowUrl: iconShadow,
  iconSize: [25, 41],
  iconAnchor: [12, 41],
  popupAnchor: [1, -34],
});
L.Marker.prototype.options.icon = DefaultIcon;

// Blue pulsing dot for user location
const UserIcon = L.divIcon({
  html: `<div style="
    width:16px;height:16px;
    background:#3b82f6;
    border:3px solid white;
    border-radius:50%;
    box-shadow:0 0 0 4px rgba(59,130,246,0.25);
    animation:pulse 2s infinite;
  "></div>`,
  iconSize: [22, 22],
  iconAnchor: [11, 11],
  className: '',
});

// Numbered marker for service centers
function makeNumberIcon(n, color = '#22d3ee') {
  return L.divIcon({
    html: `<div style="
      width:28px;height:28px;
      background:${color};
      color:#000;
      border-radius:50%;
      display:flex;align-items:center;justify-content:center;
      font-weight:900;font-size:12px;
      border:2px solid white;
      box-shadow:0 2px 6px rgba(0,0,0,0.4);
    ">${n}</div>`,
    iconSize: [28, 28],
    iconAnchor: [14, 14],
    popupAnchor: [0, -14],
    className: '',
  });
}

// Recenter map
function ChangeView({ center, zoom }) {
  const map = useMap();
  map.setView(center, zoom);
  return null;
}

// Star rating
function Stars({ rating }) {
  const full = Math.floor(rating);
  const half = rating - full >= 0.5;
  return (
    <span style={{ color: '#f59e0b', letterSpacing: '1px', fontSize: '0.82rem' }}>
      {'★'.repeat(full)}{half ? '½' : ''}{'☆'.repeat(5 - full - (half ? 1 : 0))}
      <span style={{ color: '#94a3b8', fontSize: '0.75rem', marginLeft: '4px' }}>{rating.toFixed(1)}</span>
    </span>
  );
}

// Haversine distance in km
function haversineKm(lat1, lng1, lat2, lng2) {
  const R = 6371;
  const dLat = ((lat2 - lat1) * Math.PI) / 180;
  const dLng = ((lng2 - lng1) * Math.PI) / 180;
  const a =
    Math.sin(dLat / 2) ** 2 +
    Math.cos((lat1 * Math.PI) / 180) * Math.cos((lat2 * Math.PI) / 180) * Math.sin(dLng / 2) ** 2;
  return (R * 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1 - a))).toFixed(1);
}

// Build WhatsApp URL with a pre-filled message
function whatsappUrl(waNumber, centerName) {
  if (!waNumber) return null;
  const text = encodeURIComponent(
    `Hello, I found your EV service center on evTROUBLESHOOTER. I need help with my electric vehicle. Could you please provide details about your services and availability?`
  );
  return `https://wa.me/${waNumber}?text=${text}`;
}

const SEVERITY_COLORS = ['#22d3ee', '#3b82f6', '#a855f7', '#10b981', '#f59e0b', '#ef4444', '#f97316', '#8b5cf6', '#ec4899', '#06b6d4'];

// ── Popup content (light theme for Leaflet) ────────────────────────────────
function CenterPopup({ sc, rank, userLoc }) {
  const distKm = userLoc ? haversineKm(userLoc[0], userLoc[1], sc.lat, sc.lng) : null;
  const waUrl = whatsappUrl(sc.whatsapp, sc.name);

  return (
    <div style={{ minWidth: '220px', fontFamily: 'inherit' }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: '6px', marginBottom: '4px' }}>
        <span style={{
          background: SEVERITY_COLORS[(rank - 1) % SEVERITY_COLORS.length],
          color: '#000', borderRadius: '50%', width: '20px', height: '20px',
          display: 'inline-flex', alignItems: 'center', justifyContent: 'center',
          fontWeight: 900, fontSize: '11px', flexShrink: 0,
        }}>#{rank}</span>
        <strong style={{ color: '#0f172a', fontSize: '0.9rem', lineHeight: 1.2 }}>{sc.name}</strong>
      </div>

      <Stars rating={sc.rating} />
      {distKm && <span style={{ color: '#64748b', fontSize: '0.75rem', marginLeft: '6px' }}>• {distKm} km away</span>}

      <p style={{ margin: '6px 0 2px', fontSize: '0.8rem', color: '#475569' }}>📍 {sc.address}</p>
      <p style={{ margin: '2px 0', fontSize: '0.8rem', color: '#475569' }}>🕐 {sc.hours}</p>
      <p style={{ margin: '2px 0 6px', fontSize: '0.8rem', color: '#475569' }}>📞 <a href={`tel:${sc.phone}`} style={{ color: '#3b82f6' }}>{sc.phone}</a></p>

      <div style={{ display: 'flex', gap: '3px', flexWrap: 'wrap', marginBottom: '10px' }}>
        {sc.brands.map(b => (
          <span key={b} style={{
            background: '#e2e8f0', color: '#334155',
            padding: '1px 6px', borderRadius: '3px', fontSize: '0.65rem', fontWeight: 700,
          }}>{b}</span>
        ))}
      </div>

      <div style={{ display: 'flex', gap: '6px' }}>
        <button
          onClick={() => window.open(sc.maps_url || `https://www.google.com/maps/dir/?api=1&destination=${sc.lat},${sc.lng}`, '_blank')}
          style={{
            flex: 1, background: '#3b82f6', color: 'white', border: 'none',
            padding: '6px 10px', borderRadius: '6px', cursor: 'pointer',
            fontSize: '0.78rem', fontWeight: 600,
          }}
        >🗺️ Directions</button>

        {waUrl && (
          <button
            onClick={() => window.open(waUrl, '_blank')}
            style={{
              flex: 1, background: '#25D366', color: 'white', border: 'none',
              padding: '6px 10px', borderRadius: '6px', cursor: 'pointer',
              fontSize: '0.78rem', fontWeight: 600,
            }}
          >💬 WhatsApp</button>
        )}
      </div>
    </div>
  );
}

// ── Main Component ─────────────────────────────────────────────────────────
const ServiceMap = () => {
  const [centers, setCenters] = useState([]);
  const [userLoc, setUserLoc] = useState(null);
  const [loading, setLoading] = useState(true);
  const [locationStatus, setLocationStatus] = useState('detecting');
  const [selectedCenter, setSelectedCenter] = useState(null);
  const [collapsed, setCollapsed] = useState(false);
  const [filter, setFilter] = useState('All');

  // Default: Chennai centre
  const defaultLoc = [13.0827, 80.2707];

  const fetchCenters = useCallback(async (lat, lng) => {
    setLoading(true);
    try {
      let url = '/service-centers';
      if (lat && lng) url += `?lat=${lat}&lng=${lng}`;
      const res = await apiFetch(url);
      if (res.ok) setCenters(await res.json());
    } catch (e) {
      console.error('Failed to fetch service centers', e);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    if (!navigator.geolocation) {
      setLocationStatus('unavailable');
      fetchCenters();
      return;
    }
    navigator.geolocation.getCurrentPosition(
      (pos) => {
        const lat = pos.coords.latitude;
        const lng = pos.coords.longitude;
        setUserLoc([lat, lng]);
        setLocationStatus('found');
        fetchCenters(lat, lng);
      },
      () => {
        setLocationStatus('denied');
        fetchCenters(); // Will return Chennai centers as default
      },
      { timeout: 8000 }
    );
  }, [fetchCenters]);

  const mapCenter = userLoc || defaultLoc;
  const mapZoom = userLoc ? 12 : 11;

  // Brand filter options
  const allBrands = ['All', ...Array.from(new Set(centers.flatMap(c => c.brands))).filter(b => b !== 'All Brands' && b !== 'Multi-brand').sort()];

  const visibleCenters = filter === 'All'
    ? centers
    : centers.filter(c => c.brands.some(b => b.toLowerCase().includes(filter.toLowerCase())));

  return (
    <div className="glass-card map-card" style={{ marginTop: '1.5rem', padding: '1rem' }}>
      {/* Header */}
      <div className="history-header" style={{ marginBottom: '0.8rem' }}>
        <div>
          <h3 className="section-title" style={{ margin: 0, fontSize: '1.1rem' }}>
            📍 Nearby EV Service Centers
          </h3>
          <p style={{ margin: '2px 0 0', fontSize: '0.78rem', color: 'var(--muted)' }}>
            {locationStatus === 'found' && userLoc
              ? `📡 Using your live location • ${centers.length} centers found`
              : locationStatus === 'denied'
              ? '⚠️ Location denied — showing Chennai centers'
              : locationStatus === 'unavailable'
              ? '📍 Showing Chennai centers'
              : '⏳ Detecting your location...'}
          </p>
        </div>
        <button className="collapse-btn" onClick={() => setCollapsed(!collapsed)} title={collapsed ? 'Expand' : 'Collapse'}>
          {collapsed ? '▼' : '▲'}
        </button>
      </div>

      {!collapsed && (
        loading ? (
          <div style={{ padding: '2rem', textAlign: 'center', color: 'var(--txt2)' }}>
            <span className="scanner-ring"></span> Locating service centers...
          </div>
        ) : (
          <>
            {/* Brand Filter Pills */}
            <div className="brand-filter-row">
              {allBrands.slice(0, 10).map(b => (
                <button
                  key={b}
                  className={`brand-pill ${filter === b ? 'brand-pill-active' : ''}`}
                  onClick={() => setFilter(b)}
                >
                  {b}
                </button>
              ))}
            </div>

            {/* Map */}
            <div style={{ height: '380px', width: '100%', borderRadius: '12px', overflow: 'hidden', border: '1px solid var(--border)', marginBottom: '1rem' }}>
              <MapContainer center={mapCenter} zoom={mapZoom} scrollWheelZoom={true} style={{ height: '100%', width: '100%' }}>
                <ChangeView center={mapCenter} zoom={mapZoom} />
                <TileLayer
                  attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>'
                  url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
                />

                {/* User location */}
                {userLoc && (
                  <Marker position={userLoc} icon={UserIcon}>
                    <Popup><strong>📍 Your Location</strong></Popup>
                  </Marker>
                )}

                {/* Service center markers */}
                {visibleCenters.map((sc, idx) => (
                  <Marker
                    key={sc.id}
                    position={[sc.lat, sc.lng]}
                    icon={makeNumberIcon(idx + 1, SEVERITY_COLORS[idx % SEVERITY_COLORS.length])}
                  >
                    <Popup maxWidth={280} autoPan={true}>
                      <CenterPopup sc={sc} rank={idx + 1} userLoc={userLoc} />
                    </Popup>
                  </Marker>
                ))}
              </MapContainer>
            </div>

            {/* List */}
            <div className="sc-list">
              {visibleCenters.map((sc, idx) => {
                const distKm = userLoc ? haversineKm(userLoc[0], userLoc[1], sc.lat, sc.lng) : null;
                const waUrl = whatsappUrl(sc.whatsapp, sc.name);
                const isOpen = selectedCenter === sc.id;

                return (
                  <div
                    key={sc.id}
                    className={`sc-item ${isOpen ? 'sc-selected' : ''}`}
                    onClick={() => setSelectedCenter(isOpen ? null : sc.id)}
                  >
                    <div
                      className="sc-item-rank"
                      style={{ background: SEVERITY_COLORS[idx % SEVERITY_COLORS.length] + '22', color: SEVERITY_COLORS[idx % SEVERITY_COLORS.length], borderColor: SEVERITY_COLORS[idx % SEVERITY_COLORS.length] + '44' }}
                    >
                      {idx + 1}
                    </div>
                    <div className="sc-item-info">
                      <div className="sc-item-name">{sc.name}</div>
                      <div className="sc-item-meta">
                        <Stars rating={sc.rating} />
                        {distKm && <span style={{ color: 'var(--cyan)', fontSize: '0.78rem', marginLeft: '8px', fontWeight: 700 }}>📍 {distKm} km</span>}
                        <span style={{ color: 'var(--muted)', fontSize: '0.75rem', marginLeft: '8px' }}>🕐 {sc.hours}</span>
                      </div>
                      <div className="sc-item-addr">{sc.address}</div>

                      {isOpen && (
                        <div className="sc-item-details" onClick={e => e.stopPropagation()}>
                          <div style={{ marginBottom: '6px', fontSize: '0.85rem' }}>
                            📞 <a href={`tel:${sc.phone}`} style={{ color: 'var(--cyan)', textDecoration: 'none' }}>{sc.phone}</a>
                          </div>
                          <div style={{ display: 'flex', gap: '4px', flexWrap: 'wrap', marginBottom: '10px' }}>
                            {sc.brands.map(b => (
                              <span key={b} className="dtc-code-sm" style={{ background: 'rgba(59,130,246,0.1)', color: 'var(--blue)', border: '1px solid rgba(59,130,246,0.2)' }}>{b}</span>
                            ))}
                          </div>
                          <div style={{ display: 'flex', gap: '6px', flexWrap: 'wrap' }}>
                            <button
                              className="btn-ghost-sm"
                              onClick={() => window.open(sc.maps_url || `https://www.google.com/maps/dir/?api=1&destination=${sc.lat},${sc.lng}`, '_blank')}
                            >
                              🗺️ Google Maps
                            </button>
                            {waUrl && (
                              <button
                                className="wa-btn"
                                onClick={() => window.open(waUrl, '_blank')}
                              >
                                💬 WhatsApp
                              </button>
                            )}
                            <a href={`tel:${sc.phone}`} className="btn-ghost-sm" style={{ textDecoration: 'none' }}>
                              📞 Call
                            </a>
                          </div>
                        </div>
                      )}
                    </div>
                  </div>
                );
              })}
            </div>

            {visibleCenters.length === 0 && (
              <p className="muted-text" style={{ textAlign: 'center', padding: '1rem' }}>
                No service centers found for <strong>{filter}</strong>. Try selecting "All".
              </p>
            )}
          </>
        )
      )}
    </div>
  );
};

export default ServiceMap;
