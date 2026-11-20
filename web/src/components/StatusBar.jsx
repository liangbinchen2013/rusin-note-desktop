import { GitBranch, Check, AlertCircle } from 'lucide-react'

export default function StatusBar({ user, active, draft, dirty, syncConfigured, message }) {
  const words = (draft.content || '').trim().split(/\s+/).filter(Boolean).length
  return (
    <div className="status-bar">
      <div className="status-left">
        <span className="status-item"><GitBranch size={13} /> 本地工作区</span>
        <span className="status-item">{user}</span>
        <span className="status-item">{syncConfigured ? <><Check size={13} /> 云端已配置</> : <><AlertCircle size={13} /> 未配置云端</>}</span>
      </div>
      <div className="status-right">
        {message && <span className="status-item toast">{message}</span>}
        {active && <span className="status-item">{draft.folder ? `${draft.folder} / ` : ''}{draft.title || active}</span>}
        {active && <span className="status-item">{words} 词</span>}
        {active && <span className="status-item">{dirty ? '未保存' : '已保存'}</span>}
        <span className="status-item">UTF-8 · Markdown</span>
      </div>
    </div>
  )
}
