import { useMemo, useState } from 'react'
import {
  ChevronDown, ChevronRight, FileText, Folder, FolderOpen, Plus, Trash2,
  RefreshCw, Cloud, HardDriveDownload, Download,
} from 'lucide-react'

function buildTree(notes) {
  const root = { folders: {}, files: [] }
  for (const note of notes) {
    const parts = (note.folder || '').split('/').map((p) => p.trim()).filter(Boolean)
    let node = root
    for (const part of parts) {
      if (!node.folders[part]) node.folders[part] = { folders: {}, files: [] }
      node = node.folders[part]
    }
    node.files.push(note)
  }
  return root
}

function TreeNode({ node, path, expanded, toggle, activeId, onOpen, onNew, onDelete, icon = 'file', depth = 0 }) {
  const folderNames = Object.keys(node.folders).sort((a, b) => a.localeCompare(b, 'zh'))
  const files = [...node.files].sort((a, b) => (b.mtime || 0) - (a.mtime || 0))
  const FileIcon = icon === 'cloud' ? Cloud : icon === 'cache' ? HardDriveDownload : FileText

  return (
    <div>
      {folderNames.map((name) => {
        const folderPath = path ? `${path}/${name}` : name
        const isOpen = expanded.has(folderPath)
        return (
          <div key={folderPath}>
            <div className="tree-row folder-row" style={{ paddingLeft: 10 + depth * 14 }} onClick={() => toggle(folderPath)}>
              {isOpen ? <ChevronDown size={14} /> : <ChevronRight size={14} />}
              {isOpen ? <FolderOpen size={15} className="folder-icon" /> : <Folder size={15} className="folder-icon" />}
              <span className="tree-label">{name}</span>
              {onNew && (
                <button className="tree-action" title="在此文件夹新建笔记" onClick={(e) => { e.stopPropagation(); onNew(folderPath) }}>
                  <Plus size={13} />
                </button>
              )}
            </div>
            {isOpen && (
              <TreeNode
                node={node.folders[name]}
                path={folderPath}
                expanded={expanded}
                toggle={toggle}
                activeId={activeId}
                onOpen={onOpen}
                onNew={onNew}
                onDelete={onDelete}
                icon={icon}
                depth={depth + 1}
              />
            )}
          </div>
        )
      })}
      {files.map((note) => (
        <div
          key={note.id}
          className={`tree-row file-row ${activeId === note.id ? 'active' : ''}`}
          style={{ paddingLeft: 10 + depth * 14 }}
          onClick={() => onOpen(note.id)}
          title={`${note.title || note.id}${note.file ? ' · ' + note.file : ''}`}
        >
          <FileIcon size={15} className={icon === 'file' ? 'file-icon' : 'cloud-icon'} />
          <span className="tree-label">{note.title || note.id}</span>
          {onDelete && (
            <button className="tree-action danger" title={icon === 'cache' ? '移除本地缓存副本' : '删除笔记'} onClick={(e) => {
              e.stopPropagation()
              if (window.confirm(`${icon === 'cache' ? '移除本地缓存副本' : '删除笔记'}「${note.title || note.id}」？`)) onDelete(note.id)
            }}>
              <Trash2 size={13} />
            </button>
          )}
        </div>
      ))}
    </div>
  )
}

function makeToggle(setter) {
  return (path) => setter((prev) => {
    const next = new Set(prev)
    if (next.has(path)) next.delete(path)
    else next.add(path)
    return next
  })
}

export default function Explorer({
  notes, activeId, onOpen, onNew, onRefresh, onDelete,
  remoteNotes = [], remoteInfo, activeRemoteId,
  onOpenRemote, onNewRemote, onDeleteRemote, onRefreshRemote,
  cacheNotes = [], activeCacheId, onOpenCache, onPullCache, onDeleteCache,
}) {
  const tree = useMemo(() => buildTree(notes), [notes])
  const remoteTree = useMemo(() => buildTree(remoteNotes), [remoteNotes])
  const cacheTree = useMemo(() => buildTree(cacheNotes), [cacheNotes])
  const [expandedLocal, setExpandedLocal] = useState(() => new Set())
  const [expandedRemote, setExpandedRemote] = useState(() => new Set())
  const [expandedCache, setExpandedCache] = useState(() => new Set())
  const toggleLocal = makeToggle(setExpandedLocal)
  const toggleRemote = makeToggle(setExpandedRemote)
  const toggleCache = makeToggle(setExpandedCache)

  return (
    <div className="side-panel">
      <div className="side-header">
        <span>资源管理器</span>
        <div className="side-header-actions">
          <button title="新建本地笔记" onClick={() => onNew('')}><Plus size={15} /></button>
          <button title="刷新列表" onClick={() => { onRefresh(); onRefreshRemote?.() }}><RefreshCw size={14} /></button>
        </div>
      </div>
      <div className="tree-scroll">
        <div className="tree-section-title">本地工作区</div>
        <TreeNode
          node={tree} path="" expanded={expandedLocal} toggle={toggleLocal}
          activeId={activeId} onOpen={onOpen} onNew={onNew} onDelete={onDelete}
        />
        {notes.length === 0 && <div className="empty-hint">还没有笔记。点击上方 + 新建一篇。</div>}

        <div className="tree-section-title cache">
          <span>本地缓存 · 云端副本</span>
          <button className="section-action" title="从云端拉取到本地缓存" onClick={onPullCache}><Download size={13} /></button>
        </div>
        <TreeNode
          node={cacheTree} path="" expanded={expandedCache} toggle={toggleCache}
          activeId={activeCacheId} onOpen={onOpenCache} onDelete={onDeleteCache} icon="cache"
        />
        {cacheNotes.length === 0 && <div className="empty-hint">暂无本地缓存。点上方 ↓ 从云端拉取，打开更快，可一键编辑回传。</div>}

        {remoteInfo?.configured && (
          <>
            <div className="tree-section-title cloud">云端工作区 · {remoteInfo.user}</div>
            <TreeNode
              node={remoteTree} path="" expanded={expandedRemote} toggle={toggleRemote}
              activeId={activeRemoteId} onOpen={onOpenRemote} onNew={onNewRemote}
              onDelete={onDeleteRemote} icon="cloud"
            />
            {remoteNotes.length === 0 && <div className="empty-hint">云端工作区暂无笔记</div>}
          </>
        )}
      </div>
    </div>
  )
}
