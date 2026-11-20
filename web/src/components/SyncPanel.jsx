import { useEffect, useState } from 'react'
import { Cloud, RefreshCw, Save, Download, Upload, CloudDownload, CloudUpload, PlugZap } from 'lucide-react'
import { api } from '../api.js'

const actions = [
  { id: 'test', label: '测试连接', icon: PlugZap },
  { id: 'pull_benben', label: '拉取犇犇', icon: Download },
  { id: 'pull_notes', label: '拉取云端笔记', icon: CloudDownload },
  { id: 'push_notes', label: '推送本地笔记', icon: CloudUpload },
  { id: 'push_benben', label: '推送本地犇犇', icon: Upload },
  { id: 'sync_all', label: '全部同步', icon: RefreshCw, primary: true },
]

export default function SyncPanel({ onToast, onNotesChanged, onSettingsSaved }) {
  const [status, setStatus] = useState(null)
  const [form, setForm] = useState({})
  const [cookie, setCookie] = useState('')
  const [busy, setBusy] = useState('')
  const [report, setReport] = useState(null)

  const load = async (check = false) => {
    try {
      const data = await api.syncStatus(check)
      setStatus(data)
      setForm(data.settings || {})
    } catch (err) {
      onToast?.(err.message, 'error')
    }
  }

  useEffect(() => { load(false) }, [])

  const update = (key, value) => setForm((prev) => ({ ...prev, [key]: value }))

  const save = async () => {
    setBusy('save')
    try {
      await api.saveSyncSettings({ ...form, session_cookie: cookie })
      onToast?.('同步设置已保存', 'ok')
      setCookie('')
      await load(true)
      onSettingsSaved?.()
    } catch (err) {
      onToast?.(err.message, 'error')
    } finally {
      setBusy('')
    }
  }

  const run = async (action) => {
    setBusy(action)
    setReport(null)
    try {
      const result = await api.runSync(action)
      setReport({ action, ...result })
      onToast?.(`完成：成功 ${result.ok} / 跳过 ${result.skipped} / 失败 ${result.failed}`, result.failed ? 'error' : 'ok')
      if (action !== 'test') {
        onNotesChanged?.()
        await load(false)
      }
    } catch (err) {
      onToast?.(err.message, 'error')
    } finally {
      setBusy('')
    }
  }

  return (
    <div className="center-panel sync-panel">
      <div className="panel-title"><Cloud size={18} /> 云端同步</div>
      <div className={`connection ${status?.connection?.ok ? 'ok' : ''}`}>
        {status?.connection?.message || '正在读取状态…'}
      </div>

      <div className="sync-grid">
        <label>云端地址<input value={form.remote_url || ''} onChange={(e) => update('remote_url', e.target.value)} placeholder="https://note.example.com" /></label>
        <label>云端用户名<input value={form.remote_user || ''} onChange={(e) => update('remote_user', e.target.value)} placeholder="远端账号" /></label>
        <label>本地用户名<input value={form.local_user || ''} onChange={(e) => update('local_user', e.target.value)} placeholder="留空自动选择" /></label>
        <label>登录 Cookie<input type="password" value={cookie} onChange={(e) => setCookie(e.target.value)} placeholder={form.cookie_configured ? '已保存，留空沿用' : 'rusin_session 的值'} /></label>
        <label>犇犇拉取页数<input type="number" min="1" max="20" value={form.pull_pages ?? 1} onChange={(e) => update('pull_pages', Number(e.target.value))} /></label>
        <label>请求间隔（秒）<input value={form.request_delay ?? 0.3} onChange={(e) => update('request_delay', e.target.value)} /></label>
        <label className="check"><input type="checkbox" checked={!!form.overwrite_remote} onChange={(e) => update('overwrite_remote', e.target.checked)} /> 允许覆盖云端同名笔记</label>
        <label className="check"><input type="checkbox" checked={!!form.overwrite_local} onChange={(e) => update('overwrite_local', e.target.checked)} /> 更新本地云端镜像</label>
      </div>

      <div className="sync-buttons">
        <button className="primary small" onClick={save} disabled={!!busy}><Save size={14} /> {busy === 'save' ? '保存中…' : '保存设置'}</button>
        {actions.map(({ id, label, icon: Icon, primary }) => (
          <button key={id} className={`${primary ? 'primary' : ''} small`} onClick={() => run(id)} disabled={!!busy}>
            <Icon size={14} /> {busy === id ? '执行中…' : label}
          </button>
        ))}
      </div>

      {report && (
        <div className="report">
          <b>{report.action}</b> · 成功 {report.ok} / 跳过 {report.skipped} / 失败 {report.failed}
          {report.details?.length > 0 && <ul>{report.details.slice(0, 20).map((line, i) => <li key={i}>{line}</li>)}</ul>}
        </div>
      )}

      <div className="run-history">
        <h3>最近记录</h3>
        {(status?.runs || []).length === 0 && <div className="empty-hint">还没有同步记录</div>}
        {status?.runs?.map((run, i) => (
          <div className="run-row" key={i}>
            <span>{run.time}</span><b>{run.action}</b>
            <span>成功 {run.report.ok} / 跳过 {run.report.skipped} / 失败 {run.report.failed}</span>
          </div>
        ))}
      </div>
      <p className="hint-text">Cookie 从浏览器登录云端站点后的开发者工具中复制；保存在本地并已加密，请妥善保管 data/ 目录。</p>
    </div>
  )
}
