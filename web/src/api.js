async function request(path, options = {}) {
  const response = await fetch(`/api/ide${path}`, {
    ...options,
    headers: {
      'Content-Type': 'application/json',
      ...(options.headers || {}),
    },
  })
  let data = null
  try {
    data = await response.json()
  } catch {
    data = null
  }
  if (!response.ok) {
    throw new Error(data?.error || `请求失败：HTTP ${response.status}`)
  }
  return data
}

export const api = {
  bootstrap: () => request('/bootstrap'),
  listNotes: () => request('/notes'),
  getNote: (id) => request(`/notes/${encodeURIComponent(id)}`),
  createNote: (folder = '') => request('/notes', { method: 'POST', body: JSON.stringify({ folder }) }),
  saveNote: (id, payload) => request(`/notes/${encodeURIComponent(id)}`, {
    method: 'PUT', body: JSON.stringify(payload),
  }),
  deleteNote: (id) => request(`/notes/${encodeURIComponent(id)}`, { method: 'DELETE' }),
  search: (q) => request(`/search?q=${encodeURIComponent(q)}`),
  syncStatus: (check = false) => request(`/sync/status${check ? '?check=1' : ''}`),
  saveSyncSettings: (payload) => request('/sync/settings', {
    method: 'PUT', body: JSON.stringify(payload),
  }),
  runSync: (action) => request(`/sync/${action}`, { method: 'POST' }),
}
