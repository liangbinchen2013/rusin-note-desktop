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

const REMOTE_PREFIX = 'cloud:'
const CACHE_PREFIX = 'cache:'
const sourceOf = (key) => (
  typeof key !== 'string' ? 'local'
    : key.startsWith(CACHE_PREFIX) ? 'cache'
      : key.startsWith(REMOTE_PREFIX) ? 'remote' : 'local'
)
const rawId = (key) => {
  if (typeof key !== 'string') return key
  if (key.startsWith(CACHE_PREFIX)) return key.slice(CACHE_PREFIX.length)
  if (key.startsWith(REMOTE_PREFIX)) return key.slice(REMOTE_PREFIX.length)
  return key
}
const keyFor = (id, source) => (
  source === 'cache' ? CACHE_PREFIX + id : source === 'remote' ? REMOTE_PREFIX + id : id
)

const EMPTY_DRAFT = { id: '', title: '', content: '', tags: [], folder: '', mtime: 0 }

function titleFrom(content, fallback) {
  const line = (content || '').split('\n').map((l) => l.trim()).find((l) => l && !l.startsWith('```'))
  return (line ? line.replace(/^#+\s*/, '').slice(0, 60) : '') || fallback || ''
}

export default function App() {
  const [boot, setBoot] = useState(null)
  const [notes, setNotes] = useState([])
  const [remoteInfo, setRemoteInfo] = useState(null)
  const [remoteNotes, setRemoteNotes] = useState([])
  const [cacheNotes, setCacheNotes] = useState([])
  const [workspacePaths, setWorkspacePaths] = useState(null)
  const [tabs, setTabs] = useState([])
  const [activeId, setActiveId] = useState(null)
  const [draft, setDraft] = useState(EMPTY_DRAFT)
  const [dirty, setDirty] = useState(false)
  const [view, setView] = useState('explorer')
  const [themeMode, setThemeMode] = useState(() => localStorage.getItem('rusin-theme-mode') || 'dark')
  const [systemDark, setSystemDark] = useState(() => (
    typeof window.matchMedia === 'function' && window.matchMedia('(prefers-color-scheme: dark)').matches
  ))
  const theme = themeMode === 'system' ? (systemDark ? 'dark' : 'light') : themeMode
  const [preview, setPreview] = useState('split')
  const [scrollSync, setScrollSync] = useState(true)
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

  const refreshRemote = useCallback(async () => {
    try {
      const info = await api.remoteStatus()
      setRemoteInfo(info)
      if (info.configured) {
        const data = await api.remoteNotes()
        setRemoteNotes(data.notes || [])
      } else {
        setRemoteNotes([])
      }
    } catch (err) {
      showMessage(err.message)
    }
  }, [showMessage])

  const refreshCache = useCallback(async () => {
    try {
      const data = await api.cloudFiles()
      setCacheNotes(data.files || [])
    } catch (err) {
      showMessage(err.message)
    }
  }, [showMessage])

  const refreshWorkspace = useCallback(async () => {
    try {
      setWorkspacePaths(await api.workspacePaths())
    } catch (err) {
      showMessage(err.message)
    }
  }, [showMessage])

  const refreshAll = useCallback(async () => {
    await refreshNotes()
    await refreshRemote()
    await refreshCache()
  }, [refreshNotes, refreshRemote, refreshCache])

  const openNote = useCallback(async (id, source = 'local') => {
    const key = keyFor(id, source)
    try {
      const data = source === 'remote' ? await api.getRemoteNote(id)
        : source === 'cache' ? await api.cloudFileRead(id)
          : await api.getNote(id)
      setDraft({
        id,
        title: data.title || titleFrom(data.content, id),
        content: data.content || '',
        tags: data.tags || [],
        folder: data.folder || '',
        mtime: data.mtime || 0,
      })
      setActiveId(key)
      setTabs((prev) => (prev.includes(key) ? prev : [...prev, key]))
      setDirty(false)
      setView('explorer')
    } catch (err) {
      showMessage(err.message)
    }
  }, [showMessage])

  const openByKey = useCallback((key) => {
    return openNote(rawId(key), sourceOf(key))
  }, [openNote])

  const createNote = useCallback(async (folder = '', source = 'local') => {
    try {
      const data = source === 'remote'
        ? await api.createRemoteNote(folder)
        : await api.createNote(folder)
      await refreshAll()
      await openNote(data.id, source)
      showMessage(`已${source === 'remote' ? '在云端' : ''}创建笔记 ${data.id}`)
    } catch (err) {
      showMessage(err.message)
    }
  }, [refreshAll, openNote, showMessage])

  const saveAs = useCallback(async () => {
    const name = window.prompt('另存为名称', draft.title || titleFrom(draft.content, ''))
    if (!name || !name.trim()) return
    try {
      const data = await api.saveAsNote({
        title: name.trim(),
        content: draft.content,
        tags: draft.tags,
        folder: draft.folder,
      })
      await refreshAll()
      await openNote(data.id, 'local')
      showMessage(`已另存为「${name.trim()}」`)
    } catch (err) {
      showMessage(err.message)
    }
  }, [draft, refreshAll, openNote, showMessage])

  const save = useCallback(async () => {
    if (!activeId || !dirty) return
    const source = sourceOf(activeId)
    const payload = {
      content: draft.content,
      tags: draft.tags,
      folder: draft.folder,
      title: draft.title || titleFrom(draft.content, rawId(activeId)),
    }
    try {
      if (source === 'remote') {
        await api.saveRemoteNote(rawId(activeId), payload)
      } else if (source === 'cache') {
        const result = await api.cloudFileSave(rawId(activeId), payload)
        await refreshCache()
        showMessage(result.pushed ? '已保存到本地缓存并推送云端' : `已保存到本地缓存${result.pushError ? '（云端推送失败：' + result.pushError + '）' : ''}`)
      } else {
        const result = await api.saveNote(activeId, payload)
        setDraft((prev) => ({ ...prev, mtime: result.mtime || prev.mtime }))
        showMessage('已保存')
      }
      if (source !== 'cache') {
        const title = payload.title
        setDraft((prev) => ({ ...prev, title }))
        const update = (note) => (
          note.id === rawId(activeId)
            ? { ...note, title, tags: draft.tags, folder: draft.folder }
            : note
        )
        if (source === 'remote') setRemoteNotes((prev) => prev.map(update))
        else setNotes((prev) => prev.map(update))
      }
      setDirty(false)
    } catch (err) {
      showMessage(err.message)
    }
  }, [activeId, dirty, draft, refreshCache, showMessage])
  saveRef.current = save

  const deleteCurrent = useCallback(async () => {
    if (!activeId || !window.confirm(`删除「${draft.title || rawId(activeId)}」？`)) return
    const source = sourceOf(activeId)
    try {
      if (source === 'remote') await api.deleteRemoteNote(rawId(activeId))
      else if (source === 'cache') await api.cloudFileDelete(rawId(activeId))
      else await api.deleteNote(activeId)
      const remaining = tabs.filter((key) => key !== activeId)
      setTabs(remaining)
      if (remaining.length) await openByKey(remaining[remaining.length - 1])
      else {
        setActiveId(null)
        setDraft(EMPTY_DRAFT)
        setDirty(false)
      }
      await refreshAll()
      showMessage(source === 'cache' ? '已移除本地缓存副本' : source === 'remote' ? '云端笔记已删除' : '笔记已删除')
    } catch (err) {
      showMessage(err.message)
    }
  }, [activeId, draft.title, tabs, openByKey, refreshAll, showMessage])

  const closeTab = useCallback((key) => {
    const remaining = tabs.filter((tab) => tab !== key)
    setTabs(remaining)
    if (key === activeId) {
      if (remaining.length) openByKey(remaining[remaining.length - 1])
      else { setActiveId(null); setDirty(false) }
    }
  }, [tabs, activeId, openByKey])

  const pullCloudCache = useCallback(async () => {
    try {
      setView('sync')
      const result = await api.cloudPull()
      showMessage(`缓存完成：成功 ${result.ok} / 失败 ${result.failed || 0}`)
      await refreshCache()
      await refreshWorkspace()
    } catch (err) {
      showMessage(err.message)
    }
  }, [refreshCache, refreshWorkspace, showMessage])

  useEffect(() => { refreshAll(); refreshWorkspace() }, [refreshAll, refreshWorkspace])

  useEffect(() => {
    if (typeof window.matchMedia !== 'function') return undefined
    const media = window.matchMedia('(prefers-color-scheme: dark)')
    const handler = (event) => setSystemDark(event.matches)
    media.addEventListener?.('change', handler)
    return () => media.removeEventListener?.('change', handler)
  }, [])

  useEffect(() => {
    document.documentElement.dataset.theme = theme
    localStorage.setItem('rusin-theme-mode', themeMode)
  }, [theme, themeMode])

  const cycleTheme = useCallback(() => {
    setThemeMode((mode) => (mode === 'dark' ? 'light' : mode === 'light' ? 'system' : 'dark'))
  }, [])

  useEffect(() => {
    if (!dirty) return undefined
    const timer = setTimeout(() => saveRef.current?.(), 1500)
    return () => clearTimeout(timer)
  }, [dirty, draft.content, draft.tags, draft.folder, draft.title])

  const paletteCommands = useMemo(() => {
    const actions = [
      { label: '新建本地笔记', run: () => createNote('', 'local') },
      { label: '新建云端笔记', hint: '需先配置云端', run: () => createNote('', 'remote') },
      { label: '保存当前笔记', hint: 'Ctrl+S', run: () => saveRef.current?.() },
      { label: '另存为（自定义名称）', run: saveAs },
      { label: '删除当前笔记', hint: '需要确认', run: () => deleteCurrent() },
      { label: '拉取云端到本地缓存', hint: '网盘式离线副本', run: pullCloudCache },
      { label: '全部同步', hint: '拉取并推送', run: async () => { setView('sync'); await api.runSync('sync_all'); refreshAll(); showMessage('全部同步完成') } },
      { label: '打开云端同步面板', run: () => setView('sync') },
      { label: '切换主题（暗色 / 亮色 / 跟随系统）', run: cycleTheme },
      { label: '切换预览', run: () => setPreview((p) => (p === 'off' ? 'split' : 'off')) },
      { label: '切换滚动同步', run: () => setScrollSync((v) => !v) },
    ]
    const localCommands = notes.map((note) => ({
      label: `打开：${note.title || note.id}`,
      hint: `本地 · ${note.folder || note.id}`,
      run: () => openNote(note.id, 'local'),
    }))
    const cloudCommands = remoteNotes.map((note) => ({
      label: `打开云端：${note.title || note.id}`,
      hint: `云端 · ${note.folder || note.id}`,
      run: () => openNote(note.id, 'remote'),
    }))
    const cacheCommands = cacheNotes.map((note) => ({
      label: `编辑缓存：${note.title || note.id}`,
      hint: `本地缓存 · ${note.folder || note.file}`,
      run: () => openNote(note.id, 'cache'),
    }))
    return [...actions, ...localCommands, ...cacheCommands, ...cloudCommands]
  }, [notes, remoteNotes, cacheNotes, createNote, deleteCurrent, openNote, refreshAll, showMessage, cycleTheme, saveAs, pullCloudCache])

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
  const activeSource = sourceOf(activeId)

  return (
    <div className="app-shell">
      <ActivityBar
        view={view}
        onView={setView}
        themeMode={themeMode}
        onCycleTheme={cycleTheme}
        onPalette={() => setPaletteOpen(true)}
      />
      {!showWide && (
        <aside className="side-bar">
          {view === 'explorer' ? (
            <Explorer
              notes={notes}
              activeId={activeSource === 'local' ? activeId : null}
              onOpen={(id) => openNote(id, 'local')}
              onNew={(folder) => createNote(folder, 'local')}
              onRefresh={refreshNotes}
              onDelete={async (id) => {
                await api.deleteNote(id)
                await refreshNotes()
                if (id === activeId) closeTab(id)
              }}
              remoteNotes={remoteNotes}
              remoteInfo={remoteInfo}
              activeRemoteId={activeSource === 'remote' ? rawId(activeId) : null}
              onOpenRemote={(id) => openNote(id, 'remote')}
              onNewRemote={(folder) => createNote(folder, 'remote')}
              onDeleteRemote={async (id) => {
                await api.deleteRemoteNote(id)
                await refreshRemote()
                if (keyFor(id, 'remote') === activeId) closeTab(keyFor(id, 'remote'))
              }}
              onRefreshRemote={refreshRemote}
              cacheNotes={cacheNotes}
              activeCacheId={activeSource === 'cache' ? rawId(activeId) : null}
              onOpenCache={(id) => openNote(id, 'cache')}
              onPullCache={pullCloudCache}
              onDeleteCache={async (id) => {
                await api.cloudFileDelete(id)
                await refreshCache()
                if (keyFor(id, 'cache') === activeId) closeTab(keyFor(id, 'cache'))
              }}
            />
          ) : (
            <SearchPanel onOpen={(id) => openNote(id, 'local')} />
          )}
        </aside>
      )}
      <main className={`main-area ${showWide ? 'wide' : ''}`}>
        {view === 'sync' ? (
          <SyncPanel
            onToast={showMessage}
            onNotesChanged={refreshAll}
            onSettingsSaved={refreshRemote}
          />
        ) : view === 'settings' ? (
          <SettingsPanel
            themeMode={themeMode}
            onThemeMode={setThemeMode}
            user={boot?.user}
            stats={boot?.stats}
            siteName={boot?.siteName}
            dataDir={workspacePaths}
            onToast={showMessage}
            onPathsSaved={async () => { await refreshWorkspace(); await refreshCache() }}
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
            scrollSync={scrollSync}
            onScrollSyncChange={setScrollSync}
            remote={activeSource === 'remote'}
            cached={activeSource === 'cache'}
            onSaveAs={saveAs}
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
            onOpen={openByKey}
          />
        )}
      </main>
      <StatusBar
        user={boot?.user || '…'}
        active={activeId ? rawId(activeId) : null}
        draft={draft}
        dirty={dirty}
        syncConfigured={!!boot?.syncConfigured}
        message={message}
      />
      {paletteOpen && <CommandPalette commands={paletteCommands} onClose={() => setPaletteOpen(false)} />}
    </div>
  )
}
