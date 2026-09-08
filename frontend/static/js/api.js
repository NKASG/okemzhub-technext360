/* Thin fetch wrapper — all API calls go through here. */
const API = (() => {
  const TOKEN_KEY = 'okemzhub_token';

  async function request(method, path, body = null) {
    const token = localStorage.getItem(TOKEN_KEY);
    const headers = {};
    if (body !== null) headers['Content-Type'] = 'application/json';
    if (token)         headers['Authorization'] = `Bearer ${token}`;

    const opts = { method, headers };
    if (body !== null) opts.body = JSON.stringify(body);

    const res = await fetch(path, opts);

    if (res.status === 401) {
      localStorage.removeItem(TOKEN_KEY);
      location.reload();
      throw new Error('Session expired');
    }
    if (res.status === 204) return null;
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err.detail || `HTTP ${res.status}`);
    }
    return res.json();
  }

  async function login(username, password) {
    const body = new URLSearchParams({ username, password });
    const res = await fetch('/auth/token', {
      method: 'POST',
      headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
      body,
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err.detail || 'Login failed');
    }
    return res.json();
  }

  return {
    TOKEN_KEY,
    login,
    get:    (p)    => request('GET',    p),
    post:   (p, b) => request('POST',   p, b),
    put:    (p, b) => request('PUT',    p, b),
    patch:  (p, b) => request('PATCH',  p, b),
    delete: (p)    => request('DELETE', p),
  };
})();
