const BASE = import.meta.env.VITE_API_BASE_URL || (import.meta.env.DEV ? 'http://localhost:8000/api' : '/api');

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
  const response = await fetch(url, {
    ...opts,
    headers
  });

  if (!response.ok) {
    const errorBody = await response.json().catch(() => ({ detail: response.statusText }));
    throw new Error(errorBody.detail || errorBody.message || response.statusText);
  }

  // Check if response is JSON or blob/text
  const contentType = response.headers.get('content-type') || '';
  if (contentType.includes('application/json')) {
    return response.json();
  } else if (contentType.includes('text/csv') || contentType.includes('text/plain')) {
    return response.text();
  }
  return response.blob();
}
