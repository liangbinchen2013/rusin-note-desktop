import { useEffect, useState } from 'react'
import { Search } from 'lucide-react'
import { api } from '../api.js'

export default function SearchPanel({ onOpen }) {
  const [query, setQuery] = useState('')
  const [items, setItems] = useState([])
  const [error, setError] = useState('')

  useEffect(() => {
    let active = true
    const timer = setTimeout(async () => {
      try {
        const data = await api.search(query)
        if (active) {
          setItems(data.items || [])
          setError('')
        }
      } catch (err) {
        if (active) setError(err.message)
      }
    }, 200)
    return () => { active = false; clearTimeout(timer) }
  }, [query])

  return (
    <div className="side-panel">
      <div className="side-header"><span>搜索笔记</span></div>
      <div className="search-box">
        <Search size={15} />
        <input autoFocus value={query} onChange={(e) => setQuery(e.target.value)} placeholder="标题、标签或正文…" />
      </div>
      {error && <div className="empty-hint error">{error}</div>}
      <div className="tree-scroll">
        {items.map((note) => (
          <button key={note.id} className="search-result" onClick={() => onOpen(note.id)}>
            <span className="search-title">{note.title || note.id}</span>
            <span className="search-meta">{note.folder || '根目录'} · {note.id}</span>
            {note.snippet && <span className="search-snippet">{note.snippet}</span>}
          </button>
        ))}
        {!error && items.length === 0 && <div className="empty-hint">输入关键词开始搜索</div>}
      </div>
    </div>
  )
}
