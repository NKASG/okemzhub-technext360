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

  /* Short-lived GET cache. Screens often ask for the same list (products,
     stock batches, ...) several times in a row; each trip to the server costs
     time, so identical GETs within GET_TTL_MS share one request. Any write
     clears the cache, so your own changes always show immediately. */
  const GET_TTL_MS = 10000;
  const getCache = new Map(); // path -> { at, promise }

  function cachedGet(path) {
    const hit = getCache.get(path);
    if (hit && Date.now() - hit.at < GET_TTL_MS) return hit.promise;
    const promise = request('GET', path).catch((err) => {
      getCache.delete(path); // never keep failures
      throw err;
    });
    getCache.set(path, { at: Date.now(), promise });
    return promise;
  }

  function write(method, path, body) {
    getCache.clear();
    return request(method, path, body).finally(() => getCache.clear());
  }

  return {
    TOKEN_KEY,
    login,
    clearCache: () => getCache.clear(),
    get:    (p)    => cachedGet(p),
    post:   (p, b) => write('POST',   p, b),
    put:    (p, b) => write('PUT',    p, b),
    patch:  (p, b) => write('PATCH',  p, b),
    delete: (p)    => write('DELETE', p),
  };
})();
