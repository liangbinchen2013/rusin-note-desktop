import Editor from '@monaco-editor/react'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import rehypeKatex from 'rehype-katex'
import rehypeHighlight from 'rehype-highlight'
import { X, Eye, Columns2, Save, FileCode2 } from 'lucide-react'

export default function EditorPane({
  tabs, activeId, draft, dirty, theme, preview, onPreviewChange,
  onChange, onFieldChange, onSave, onCloseTab, onOpen,
}) {
  if (!activeId) {
    return (
      <div className="center-panel empty-editor">
        <FileCode2 size={56} strokeWidth={1} />
        <h2>如形本地笔记</h2>
        <p>从左侧资源管理器选择一篇笔记，或按 <kbd>Ctrl</kbd> + <kbd>P</kbd> 快速打开。</p>
      </div>
    )
  }

  return (
    <div className="center-panel editor-container">
      <div className="tab-bar">
        {tabs.map((id) => (
          <div key={id} className={`tab ${id === activeId ? 'active' : ''}`} onClick={() => onOpen(id)}>
            <span className="tab-title">{draft.id === id && draft.title ? draft.title : id}</span>
            {dirty && <span className="dirty-dot" />}
            <button className="tab-close" onClick={(e) => { e.stopPropagation(); onCloseTab(id) }} aria-label="关闭标签">
              <X size={13} />
            </button>
          </div>
        ))}
      </div>

      <div className="editor-toolbar">
        <div className="toolbar-fields">
          <input className="folder-input" value={draft.folder || ''} onChange={(e) => onFieldChange('folder', e.target.value)} placeholder="文件夹（用 / 分层）" />
          <input className="tags-input" value={(draft.tags || []).join(', ')} onChange={(e) => onFieldChange('tags', e.target.value)} placeholder="标签，逗号分隔" />
        </div>
        <div className="toolbar-actions">
          <button className="small" onClick={() => onPreviewChange(preview === 'off' ? 'split' : 'off')} title="切换预览">
            {preview === 'off' ? <Eye size={14} /> : <Columns2 size={14} />} {preview === 'off' ? '预览' : '关闭预览'}
          </button>
          <button className="primary small" onClick={onSave}><Save size={14} /> 保存{dirty ? ' •' : ''}</button>
        </div>
      </div>

      <div className={`editor-body ${preview !== 'off' ? 'with-preview' : ''}`}>
        <div className="monaco-wrap">
          <Editor
            path={`${activeId}.md`}
            language="markdown"
            theme={theme === 'dark' ? 'vs-dark' : 'light'}
            value={draft.content || ''}
            onChange={(value) => onChange(value ?? '')}
            options={{
              fontSize: 14,
              lineHeight: 22,
              fontFamily: 'JetBrains Mono, Cascadia Code, Consolas, monospace',
              minimap: { enabled: true },
              wordWrap: 'on',
              automaticLayout: true,
              scrollBeyondLastLine: false,
              smoothScrolling: true,
              cursorBlinking: 'smooth',
              padding: { top: 12, bottom: 12 },
              renderLineHighlight: 'all',
            }}
          />
        </div>
        {preview !== 'off' && (
          <div className="preview-pane">
            <div className="preview-header">预览</div>
            <div className="markdown-body">
              <ReactMarkdown remarkPlugins={[remarkGfm]} rehypePlugins={[rehypeKatex, rehypeHighlight]}>
                {draft.content || ''}
              </ReactMarkdown>
            </div>
          </div>
        )}
      </div>
    </div>
  )
}
