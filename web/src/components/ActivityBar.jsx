import { Files, Search, Cloud, Settings, Sun, Moon, Command } from 'lucide-react'

const items = [
  { id: 'explorer', label: '资源管理器', icon: Files },
  { id: 'search', label: '搜索', icon: Search },
  { id: 'sync', label: '云端同步', icon: Cloud },
  { id: 'settings', label: '设置', icon: Settings },
]

export default function ActivityBar({ view, onView, theme, onToggleTheme, onPalette }) {
  return (
    <div className="activity-bar">
      <div className="activity-icon activity-logo" title="如形本地笔记">R</div>
      {items.map(({ id, label, icon: Icon }) => (
        <button
          key={id}
          className={`activity-icon ${view === id ? 'active' : ''}`}
          title={label}
          aria-label={label}
          onClick={() => onView(id)}
        >
          <Icon size={22} strokeWidth={1.8} />
        </button>
      ))}
      <div className="activity-spacer" />
      <button className="activity-icon" title="命令面板 (Ctrl+P)" aria-label="命令面板" onClick={onPalette}>
        <Command size={20} strokeWidth={1.8} />
      </button>
      <button className="activity-icon" title="切换主题" aria-label="切换主题" onClick={onToggleTheme}>
        {theme === 'dark' ? <Sun size={20} strokeWidth={1.8} /> : <Moon size={20} strokeWidth={1.8} />}
      </button>
    </div>
  )
}
