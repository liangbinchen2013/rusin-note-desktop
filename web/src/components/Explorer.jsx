import { useMemo, useState } from 'react'
import { ChevronDown, ChevronRight, FileText, Folder, FolderOpen, Plus, Trash2, RefreshCw } from 'lucide-react'

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

function TreeNode({ node, path, expanded, toggle, activeId, onOpen, onNew, onDelete, depth = 0 }) {
  const folderNames = Object.keys(node.folders).sort((a, b) => a.localeCompare(b, 'zh'))
  const files = [...node.files].sort((a, b) => b.mtime - a.mtime)

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
              <button className="tree-action" title="在此文件夹新建笔记" onClick={(e) => { e.stopPropagation(); onNew(folderPath) }}>
                <Plus size={13} />
              </button>
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
          title={`${note.title} · ${note.id}`}
        >
          <FileText size={15} className="file-icon" />
          <span className="tree-label">{note.title || note.id}</span>
          <button className="tree-action danger" title="删除笔记" onClick={(e) => {
            e.stopPropagation()
            if (window.confirm(`删除笔记「${note.title || note.id}」？`)) onDelete(note.id)
          }}>
            <Trash2 size={13} />
          </button>
        </div>
      ))}
    </div>
  )
}

export default function Explorer({ notes, activeId, onOpen, onNew, onRefresh, onDelete }) {
  const tree = useMemo(() => buildTree(notes), [notes])
  const [expanded, setExpanded] = useState(() => new Set())

  const toggle = (path) => {
    setExpanded((prev) => {
      const next = new Set(prev)
      if (next.has(path)) next.delete(path)
      else next.add(path)
      return next
    })
  }

  return (
    <div className="side-panel">
      <div className="side-header">
        <span>资源管理器</span>
        <div className="side-header-actions">
          <button title="新建笔记" onClick={() => onNew('')}><Plus size={15} /></button>
          <button title="刷新列表" onClick={onRefresh}><RefreshCw size={14} /></button>
        </div>
      </div>
      <div className="tree-scroll">
        <TreeNode
          node={tree}
          path=""
          expanded={expanded}
          toggle={toggle}
          activeId={activeId}
          onOpen={onOpen}
          onNew={onNew}
          onDelete={onDelete}
        />
        {notes.length === 0 && <div className="empty-hint">还没有笔记。点击上方 + 新建一篇。</div>}
      </div>
    </div>
  )
}
