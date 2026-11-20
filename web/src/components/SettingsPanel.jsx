import { Settings2, Sun, Moon, Database, Keyboard } from 'lucide-react'

export default function SettingsPanel({ theme, onToggleTheme, user, stats, siteName }) {
  return (
    <div className="center-panel settings-panel">
      <div className="panel-title"><Settings2 size={18} /> 设置</div>
      <div className="settings-card">
        <h3>外观</h3>
        <div className="setting-row">
          <span>主题</span>
          <button className="small" onClick={onToggleTheme}>
            {theme === 'dark' ? <><Sun size={14} /> 切换到浅色</> : <><Moon size={14} /> 切换到深色</>}
          </button>
        </div>
      </div>
      <div className="settings-card">
        <h3><Database size={15} /> 本地数据</h3>
        <p>应用名称：{siteName}</p>
        <p>当前用户：{user}</p>
        <p>笔记数量：{stats?.count ?? 0} · 内容大小：{stats?.size ?? 0} 字节</p>
        <p>数据目录：工作区 data/（SQLite 索引 + JSON 文件）</p>
      </div>
      <div className="settings-card">
        <h3><Keyboard size={15} /> 快捷键</h3>
        <p><kbd>Ctrl</kbd> + <kbd>S</kbd> 保存当前笔记</p>
        <p><kbd>Ctrl</kbd> + <kbd>P</kbd> 快速打开笔记 / 命令面板</p>
        <p><kbd>Ctrl</kbd> + <kbd>Shift</kbd> + <kbd>P</kbd> 命令面板</p>
      </div>
    </div>
  )
}
