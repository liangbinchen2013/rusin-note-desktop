import { useEffect, useState } from 'react'
import { Settings2, Sun, Moon, Monitor, Database, Keyboard, FolderOpen, RefreshCw, HardDrive, CloudDownload } from 'lucide-react'
import { api } from '../api.js'

const modes = [
  { id: 'light', label: '亮色', icon: Sun },
  { id: 'dark', label: '暗色', icon: Moon },
  { id: 'system', label: '跟随系统', icon: Monitor },
]

export default function SettingsPanel({
  themeMode, onThemeMode, user, stats, siteName,
  dataDir, onToast, onPathsSaved,
}) {
  const [localDir, setLocalDir] = useState('')
  const [cloudDir, setCloudDir] = useState('')
  const [busy, setBusy] = useState('')

  useEffect(() => {
    setLocalDir(dataDir?.customLocal ? (dataDir?.localDir || '') : '')
    setCloudDir(dataDir?.customCloud ? (dataDir?.cloudDir || '') : '')
  }, [dataDir])

  const pick = async (current, setter) => {
    let result = null
    try {
      if (window.pywebview?.api?.pickFolder) {
        result = await window.pywebview.api.pickFolder(current)
      } else {
        result = await api.pickFolder(current)
      }
    } catch (err) {
      onToast?.(err.message, 'error')
      return
    }
    if (result?.path) setter(result.path)
    else {
      const typed = window.prompt('输入文件夹完整路径（原生窗口不可用时）', current)
      if (typed) setter(typed)
    }
  }

  const savePaths = async () => {
    setBusy('save')
    try {
      await api.saveWorkspacePaths({ local_notes_dir: localDir, cloud_cache_dir: cloudDir })
      onToast?.('目录设置已保存', 'ok')
      await onPathsSaved?.()
    } catch (err) {
      onToast?.(err.message, 'error')
    } finally {
      setBusy('')
    }
  }

  const syncAll = async () => {
    setBusy('sync')
    try {
      const result = await api.localSyncAll()
      onToast?.(`已镜像 ${result.count} 篇本地笔记`, 'ok')
      await onPathsSaved?.()
    } catch (err) {
      onToast?.(err.message, 'error')
    } finally {
      setBusy('')
    }
  }

  return (
    <div className="center-panel settings-panel">
      <div className="panel-title"><Settings2 size={18} /> 设置</div>
      <div className="settings-card">
        <h3>外观</h3>
        <div className="setting-row">
          <span>主题</span>
          <div className="theme-options">
            {modes.map(({ id, label, icon: Icon }) => (
              <button key={id} className={`small ${themeMode === id ? 'active' : ''}`} onClick={() => onThemeMode(id)}>
                <Icon size={14} /> {label}
              </button>
            ))}
          </div>
        </div>
      </div>

      <div className="settings-card">
        <h3><FolderOpen size={15} /> 工作区目录</h3>
        <p>本地笔记镜像与云端缓存都以 .md 文件落到目录，可用其它编辑器直接打开。留空表示使用默认位置。</p>
        <div className="dir-row">
          <label>本地笔记目录</label>
          <input value={localDir} onChange={(e) => setLocalDir(e.target.value)} placeholder={dataDir?.localDir || '默认：data/local_notes'} />
          <button className="small" onClick={() => pick(localDir || dataDir?.localDir || '', setLocalDir)} title="选择文件夹"><FolderOpen size={14} /></button>
        </div>
        <div className="dir-row">
          <label>云端缓存目录</label>
          <input value={cloudDir} onChange={(e) => setCloudDir(e.target.value)} placeholder={dataDir?.cloudDir || '默认：系统临时目录'} />
          <button className="small" onClick={() => pick(cloudDir || dataDir?.cloudDir || '', setCloudDir)} title="选择文件夹"><FolderOpen size={14} /></button>
        </div>
        <div className="dir-actions">
          <button className="small" onClick={savePaths} disabled={!!busy}><RefreshCw size={14} /> {busy === 'save' ? '保存中…' : '保存目录'}</button>
          <button className="small" onClick={syncAll} disabled={!!busy}><HardDrive size={14} /> {busy === 'sync' ? '镜像中…' : '镜像全部本地笔记'}</button>
        </div>
        <p className="dir-stat"><Database size={13} /> 本地镜像 {dataDir?.localCount ?? 0} 个 · 云端缓存 {dataDir?.cloudCount ?? 0} 个</p>
        <p className="dir-stat"><CloudDownload size={13} /> 云端缓存的笔记可一键编辑，保存时回传云端；删除缓存副本不影响云端原文。</p>
      </div>

      <div className="settings-card">
        <h3><Database size={15} /> 本地数据</h3>
        <p>应用名称：{siteName}</p>
        <p>当前用户：{user}</p>
        <p>笔记数量：{stats?.count ?? 0} · 内容大小：{stats?.size ?? 0} 字节</p>
        <p>数据目录：{dataDir?.localDir || '工作区 data/'}（SQLite 索引 + JSON 文件）</p>
      </div>
      <div className="settings-card">
        <h3><Keyboard size={15} /> 快捷键</h3>
        <p><kbd>Ctrl</kbd> + <kbd>S</kbd> 保存当前笔记</p>
        <p><kbd>Ctrl</kbd> + <kbd>P</kbd> 快速打开笔记 / 命令面板</p>
      </div>
    </div>
  )
}
