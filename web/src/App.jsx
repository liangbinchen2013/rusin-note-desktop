import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import { api } from './api.js'
import ActivityBar from './components/ActivityBar.jsx'
import Explorer from './components/Explorer.jsx'
import SearchPanel from './components/SearchPanel.jsx'
import EditorPane from './components/EditorPane.jsx'
import SyncPanel from './components/SyncPanel.jsx'
import SettingsPanel from './components/SettingsPanel.jsx'
import StatusBar from './components/StatusBar.jsx'
import CommandPalette from './components/CommandPalette.jsx'

function titleFrom(content, fallback) {
  const line = (content || '').split('\n').map((l) => l.trim()).find((l) => l && !l.startsWith('```'))
  return (line ? line.replace(/^#+\s*/, '').slice(0, 60) : '') || fallback || ''
}

export default function App() {
  const [boot, setBoot] = useState(null)
  const [notes, setNotes] = useState([])
  const [tabs, setTabs] = useState([])
  const [activeId, setActiveId] = useState(null)
  const [draft, setDraft] = useState({ id: '', title: '', content: '', tags: [], folder: '', mtime: 0 })
  const [dirty, setDirty] = useState(false)
  const [view, setView] = useState('explorer')
  const [theme, setTheme] = useState(() => localStorage.getItem('rusin-theme') || 'dark')
  const [preview, setPreview] = useState('split')
  const [paletteOpen, setPaletteOpen] = useState(false)
  const [message, setMessage] = useState('')
  const saveRef = useRef(null)
  const messageTimer = useRef(null)

  const showMessage = useCallback((text) => {
    setMessage(text)
    clearTimeout(messageTimer.current)
    messageTimer.current = setTimeout(() => setMessage(''), 2600)
  }, [])

  const refreshNotes = useCallback(async () => {
    try {
      const data = await api.bootstrap()
      setBoot(data)
      setNotes(data.notes || [])
    } catch (err) {
      showMessage(err.message)
    }
  }, [showMessage])

  const openNote = useCallback(async (id) => {
    try {
      const data = await api.getNote(id)
      setDraft({
        id: data.id,
        title: titleFrom(data.content, id),
        content: data.content || '',
        tags: data.tags || [],
        folder: data.folder || '',
        mtime: data.mtime || 0,
      })
      setActiveId(id)
      setTabs((prev) => (prev.includes(id) ? prev : [...prev, id]))
      setDirty(false)
      setView('explorer')
    } catch (err) {
      showMessage(err.message)
    }
  }, [showMessage])

  const createNote = useCallback(async (folder = '') => {
    try {
      const data = await api.createNote(folder)
      await refreshNotes()
      await openNote(data.id)
      showMessage(`已创建笔记 ${data.id}`)
    } catch (err) {
      showMessage(err.message)
    }
  }, [refreshNotes, openNote, showMessage])

  const save = useCallback(async () => {
    if (!activeId || !dirty) return
    try {
      const result = await api.saveNote(activeId, {
        content: draft.content,
        tags: draft.tags,
        folder: draft.folder,
      })
      const title = titleFrom(draft.content, activeId)
      setDraft((prev) => ({ ...prev, title, mtime: result.mtime || prev.mtime }))
      setNotes((prev) => prev.map((n) => (
        n.id === activeId ? { ...n, title, tags: draft.tags, folder: draft.folder, mtime: result.mtime || n.mtime } : n
      )))
      setDirty(false)
      showMessage('已保存')
    } catch (err) {
      showMessage(err.message)
    }
  }, [activeId, dirty, draft, showMessage])
  saveRef.current = save

  const deleteCurrent = useCallback(async () => {
    if (!activeId || !window.confirm(`删除笔记「${draft.title || activeId}」？`)) return
    try {
      await api.deleteNote(activeId)
      const remaining = tabs.filter((id) => id !== activeId)
      setTabs(remaining)
      if (remaining.length) await openNote(remaining[remaining.length - 1])
      else {
        setActiveId(null)
        setDraft({ id: '', title: '', content: '', tags: [], folder: '', mtime: 0 })
        setDirty(false)
      }
      await refreshNotes()
      showMessage('笔记已删除')
    } catch (err) {
      showMessage(err.message)
    }
  }, [activeId, draft.title, tabs, openNote, refreshNotes, showMessage])

  const closeTab = useCallback((id) => {
    const remaining = tabs.filter((tab) => tab !== id)
    setTabs(remaining)
    if (id === activeId) {
      if (remaining.length) openNote(remaining[remaining.length - 1])
      else { setActiveId(null); setDirty(false) }
    }
  }, [tabs, activeId, openNote])

  useEffect(() => { refreshNotes() }, [refreshNotes])

  useEffect(() => {
    document.documentElement.dataset.theme = theme
    localStorage.setItem('rusin-theme', theme)
  }, [theme])

  useEffect(() => {
    if (!dirty) return undefined
    const timer = setTimeout(() => saveRef.current?.(), 1500)
    return () => clearTimeout(timer)
  }, [dirty, draft.content, draft.tags, draft.folder])

  const paletteCommands = useMemo(() => {
    const actions = [
      { label: '新建笔记', hint: '在当前工作区创建', run: () => createNote('') },
      { label: '保存当前笔记', hint: 'Ctrl+S', run: () => saveRef.current?.() },
      { label: '删除当前笔记', hint: '需要确认', run: () => deleteCurrent() },
      { label: '全部同步', hint: '拉取并推送', run: async () => { setView('sync'); await api.runSync('sync_all'); refreshNotes(); showMessage('全部同步完成') } },
      { label: '打开云端同步面板', run: () => setView('sync') },
      { label: '切换主题', run: () => setTheme((t) => (t === 'dark' ? 'light' : 'dark')) },
      { label: '切换预览', run: () => setPreview((p) => (p === 'off' ? 'split' : 'off')) },
    ]
    const noteCommands = notes.map((note) => ({
      label: `打开：${note.title || note.id}`,
      hint: note.folder || note.id,
      run: () => openNote(note.id),
    }))
    return [...actions, ...noteCommands]
  }, [notes, createNote, deleteCurrent, openNote, refreshNotes, showMessage])

  useEffect(() => {
    const onKey = (event) => {
      const mod = event.ctrlKey || event.metaKey
      if (!mod) return
      const key = event.key.toLowerCase()
      if (key === 's') {
        event.preventDefault()
        saveRef.current?.()
      } else if (key === 'p') {
        event.preventDefault()
        setPaletteOpen(true)
      }
    }
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [])

  const showWide = view === 'sync' || view === 'settings'

  return (
    <div className="app-shell">
      <ActivityBar
        view={view}
        onView={setView}
        theme={theme}
        onToggleTheme={() => setTheme((t) => (t === 'dark' ? 'light' : 'dark'))}
        onPalette={() => setPaletteOpen(true)}
      />
      {!showWide && (
        <aside className="side-bar">
          {view === 'explorer' ? (
            <Explorer
              notes={notes}
              activeId={activeId}
              onOpen={openNote}
              onNew={createNote}
              onRefresh={refreshNotes}
              onDelete={async (id) => { await api.deleteNote(id); await refreshNotes(); if (id === activeId) closeTab(id) }}
            />
          ) : (
            <SearchPanel onOpen={openNote} />
          )}
        </aside>
      )}
      <main className={`main-area ${showWide ? 'wide' : ''}`}>
        {view === 'sync' ? (
          <SyncPanel onToast={showMessage} onNotesChanged={refreshNotes} />
        ) : view === 'settings' ? (
          <SettingsPanel
            theme={theme}
            onToggleTheme={() => setTheme((t) => (t === 'dark' ? 'light' : 'dark'))}
            user={boot?.user}
            stats={boot?.stats}
            siteName={boot?.siteName}
          />
        ) : (
          <EditorPane
            tabs={tabs}
            activeId={activeId}
            draft={draft}
            dirty={dirty}
            theme={theme}
            preview={preview}
            onPreviewChange={setPreview}
            onChange={(content) => { setDraft((prev) => ({ ...prev, content })); setDirty(true) }}
            onFieldChange={(key, value) => {
              const next = key === 'tags'
                ? value.split(',').map((t) => t.trim()).filter(Boolean)
                : value
              setDraft((prev) => ({ ...prev, [key]: next }))
              setDirty(true)
            }}
            onSave={save}
            onCloseTab={closeTab}
            onOpen={openNote}
          />
        )}
      </main>
      <StatusBar
        user={boot?.user || '…'}
        active={activeId}
        draft={draft}
        dirty={dirty}
        syncConfigured={!!boot?.syncConfigured}
        message={message}
      />
      {paletteOpen && <CommandPalette commands={paletteCommands} onClose={() => setPaletteOpen(false)} />}
    </div>
  )
}
