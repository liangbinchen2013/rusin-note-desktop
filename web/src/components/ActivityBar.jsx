import { Files, Search, Cloud, Settings, Sun, Moon, Monitor, Command } from 'lucide-react'

const items = [
  { id: 'explorer', label: '资源管理器', icon: Files },
  { id: 'search', label: '搜索', icon: Search },
  { id: 'sync', label: '云端同步', icon: Cloud },
  { id: 'settings', label: '设置', icon: Settings },
]

const themeLabels = { dark: '暗色', light: '亮色', system: '跟随系统' }

export default function ActivityBar({ view, onView, themeMode, onCycleTheme, onPalette }) {
  const ThemeIcon = themeMode === 'dark' ? Moon : themeMode === 'light' ? Sun : Monitor
  return (
    <div className="activity-bar">
      <img className="activity-logo-img" src="/logo-mark.png" alt="如形本地笔记" title="如形本地笔记" />
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
      <button className="activity-icon" title={`主题：${themeLabels[themeMode]}（点击切换）`} aria-label="切换主题" onClick={onCycleTheme}>
        <ThemeIcon size={20} strokeWidth={1.8} />
      </button>
    </div>
  )
}
