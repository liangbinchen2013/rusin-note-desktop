import { useEffect, useMemo, useState } from 'react'
import { Search } from 'lucide-react'

export default function CommandPalette({ commands, onClose }) {
  const [query, setQuery] = useState('')
  const filtered = useMemo(
    () => commands.filter((cmd) => !query || cmd.label.toLowerCase().includes(query.toLowerCase())),
    [commands, query],
  )

  useEffect(() => {
    const onKey = (e) => {
      if (e.key === 'Escape') onClose()
      if (e.key === 'Enter' && filtered[0]) {
        onClose()
        filtered[0].run()
      }
    }
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [filtered, onClose])

  return (
    <div className="palette-backdrop" onMouseDown={onClose}>
      <div className="palette" onMouseDown={(e) => e.stopPropagation()}>
        <div className="palette-input"><Search size={17} /><input autoFocus value={query} onChange={(e) => setQuery(e.target.value)} placeholder="输入命令或笔记标题…" /></div>
        <div className="palette-list">
          {filtered.map((cmd, i) => (
            <button key={cmd.label} className={i === 0 ? 'active' : ''} onClick={() => { onClose(); cmd.run() }}>
              <span>{cmd.label}</span><small>{cmd.hint || ''}</small>
            </button>
          ))}
          {filtered.length === 0 && <div className="empty-hint">没有匹配项</div>}
        </div>
      </div>
    </div>
  )
}
