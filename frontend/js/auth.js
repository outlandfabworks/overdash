/**
 * auth.js — shared auth token helper.
 *
 * The backend injects the token into the served index.html as:
 *   <meta name="pidash-token" content="<token>">
 *
 * All mutating API calls (PUT, POST) must include:
 *   Authorization: Bearer <token>
 *
 * Usage:
 *   import { authHeaders, authFetch } from './auth.js';
 *   await authFetch('/api/reset_trip', { method: 'POST' });
 */

export const API_TOKEN = document.querySelector('meta[name="pidash-token"]')
  ?.getAttribute('content') ?? '';

/** Returns headers object with Authorization set. */
export function authHeaders(extra = {}) {
  return { 'Authorization': `Bearer ${API_TOKEN}`, ...extra };
}

/** Drop-in replacement for fetch() that automatically adds the auth header. */
export function authFetch(url, options = {}) {
  return fetch(url, {
    ...options,
    headers: {
      ...authHeaders(options.headers ?? {}),
      ...(options.body ? { 'Content-Type': 'application/json' } : {}),
    },
  });
}
