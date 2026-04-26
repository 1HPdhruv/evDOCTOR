// Shared API base URL — reads from .env VITE_API_URL
export const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000/api'

// Auth helpers
export function getToken() { return localStorage.getItem('ev_token') }
export function getUser() {
  try { return JSON.parse(localStorage.getItem('ev_user') || 'null') } catch { return null }
}
export function setAuth(token, user) {
  localStorage.setItem('ev_token', token)
  localStorage.setItem('ev_user', JSON.stringify(user))
}
export function clearAuth() {
  localStorage.removeItem('ev_token')
  localStorage.removeItem('ev_user')
}

// Authenticated fetch helper
export async function apiFetch(path, options = {}) {
  const token = getToken()
  const headers = { 'Content-Type': 'application/json', ...(options.headers || {}) }
  if (token) headers['Authorization'] = `Bearer ${token}`
  return fetch(`${API_BASE_URL}${path}`, { ...options, headers })
}
