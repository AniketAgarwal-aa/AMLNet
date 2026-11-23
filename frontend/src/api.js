const PROD_API_URL = 'https://amlnet-api.onrender.com/api';
const isLocalhost = typeof window !== 'undefined' && (window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1');
const BASE = import.meta.env.VITE_API_BASE_URL || (import.meta.env.DEV || isLocalhost ? 'http://localhost:8000/api' : PROD_API_URL);

export function getSessionToken() {
  return localStorage.getItem('amlnet_session_token') || '';
}

export function setSessionToken(token) {
  if (token) {
    localStorage.setItem('amlnet_session_token', token);
  } else {
    localStorage.removeItem('amlnet_session_token');
  }
}

export function getAdminKey() {
  return sessionStorage.getItem('amlnet_admin_key') || '';
}

export function setAdminKey(key) {
  if (key) {
    sessionStorage.setItem('amlnet_admin_key', key);
  } else {
    sessionStorage.removeItem('amlnet_admin_key');
  }
}

export async function api(path, opts = {}) {
  const timeoutMs = opts.timeoutMs || 30000;
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), timeoutMs);

  const headers = {
    'Content-Type': 'application/json',
    ...(opts.headers || {})
  };

  const sessionToken = getSessionToken();
  if (sessionToken && !headers['X-Session-Token']) {
    headers['X-Session-Token'] = sessionToken;
  }

  const adminKey = getAdminKey();
  if (adminKey && !headers['X-Admin-Key']) {
    headers['X-Admin-Key'] = adminKey;
  }

  const url = path.startsWith('http') ? path : `${BASE}${path.startsWith('/') ? '' : '/'}${path}`;

  try {
    const response = await fetch(url, {
      ...opts,
      signal: controller.signal,
      headers
    });

    clearTimeout(timer);

    if (!response.ok) {
      const errorBody = await response.json().catch(() => ({ detail: response.statusText }));
      throw new Error(errorBody.detail || errorBody.message || `HTTP ${response.status}: ${response.statusText}`);
    }

    const contentType = response.headers.get('content-type') || '';
    if (contentType.includes('application/json')) {
      return await response.json();
    } else if (contentType.includes('text/csv') || contentType.includes('text/plain')) {
      return await response.text();
    }
    return await response.blob();
  } catch (err) {
    clearTimeout(timer);
    if (err.name === 'AbortError') {
      throw new Error(`Request to ${path} timed out after ${timeoutMs / 1000}s. The service may be waking up.`);
    }
    throw err;
  }
}
