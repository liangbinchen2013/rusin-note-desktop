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
  createNote: (folder = '', title = '') => request('/notes', { method: 'POST', body: JSON.stringify({ folder, title }) }),
  saveNote: (id, payload) => request(`/notes/${encodeURIComponent(id)}`, {
    method: 'PUT', body: JSON.stringify(payload),
  }),
  saveAsNote: (payload) => request('/notes/save-as', { method: 'POST', body: JSON.stringify(payload) }),
  deleteNote: (id) => request(`/notes/${encodeURIComponent(id)}`, { method: 'DELETE' }),
  workspacePaths: () => request('/workspace/paths'),
  saveWorkspacePaths: (payload) => request('/workspace/paths', { method: 'PUT', body: JSON.stringify(payload) }),
  pickFolder: (initial = '') => request('/workspace/pick-folder', { method: 'POST', body: JSON.stringify({ initial }) }),
  localFiles: () => request('/workspace/local/files'),
  localSyncAll: () => request('/workspace/local/sync-all', { method: 'POST' }),
  cloudFiles: () => request('/workspace/cloud/files'),
  cloudPull: () => request('/workspace/cloud/pull', { method: 'POST' }),
  cloudFileRead: (id) => request(`/workspace/cloud/files/${encodeURIComponent(id)}`),
  cloudFileSave: (id, payload) => request(`/workspace/cloud/files/${encodeURIComponent(id)}`, {
    method: 'PUT', body: JSON.stringify(payload),
  }),
  cloudFileDelete: (id) => request(`/workspace/cloud/files/${encodeURIComponent(id)}`, { method: 'DELETE' }),
  search: (q) => request(`/search?q=${encodeURIComponent(q)}`),
  remoteStatus: () => request('/remote/status'),
  remoteNotes: () => request('/remote/notes'),
  getRemoteNote: (id) => request(`/remote/notes/${encodeURIComponent(id)}`),
  createRemoteNote: (folder = '') => request('/remote/notes', { method: 'POST', body: JSON.stringify({ folder }) }),
  saveRemoteNote: (id, payload) => request(`/remote/notes/${encodeURIComponent(id)}`, {
    method: 'PUT', body: JSON.stringify(payload),
  }),
  deleteRemoteNote: (id) => request(`/remote/notes/${encodeURIComponent(id)}`, { method: 'DELETE' }),
  syncStatus: (check = false) => request(`/sync/status${check ? '?check=1' : ''}`),
  saveSyncSettings: (payload) => request('/sync/settings', {
    method: 'PUT', body: JSON.stringify(payload),
  }),
  runSync: (action) => request(`/sync/${action}`, { method: 'POST' }),
}
