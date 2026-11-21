import { useRef } from 'react'
import Editor from '@monaco-editor/react'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import remarkMath from 'remark-math'
import rehypeKatex from 'rehype-katex'
import rehypeHighlight from 'rehype-highlight'
import { X, Eye, Columns2, Save, FileCode2, Link2, Cloud, HardDriveDownload, Copy } from 'lucide-react'

export default function EditorPane({
  tabs, activeId, draft, dirty, theme, preview, onPreviewChange,
  onChange, onFieldChange, onSave, onCloseTab, onOpen,
  scrollSync, onScrollSyncChange, remote, cached, onSaveAs,
}) {
  const editorRef = useRef(null)
  const previewRef = useRef(null)
  const syncing = useRef(false)

  const syncToPreview = (event) => {
    if (!scrollSync || !event.scrollTopChanged || syncing.current) return
    const el = previewRef.current
    if (!el) return
    const maxEditor = Math.max(1, (event.scrollHeight || 0) - (event.viewportHeight || 0))
    const maxPreview = Math.max(0, el.scrollHeight - el.clientHeight)
    syncing.current = true
    el.scrollTop = (event.scrollTop / maxEditor) * maxPreview
    requestAnimationFrame(() => { syncing.current = false })
  }

  const syncToEditor = () => {
    if (!scrollSync || syncing.current || !editorRef.current || !previewRef.current) return
    const el = previewRef.current
    const maxPreview = Math.max(1, el.scrollHeight - el.clientHeight)
    if (!editorRef.current.getModel()) return
    const contentHeight = editorRef.current.getContentHeight?.() || editorRef.current.getModel().getLineCount() * 22
    const maxEditor = Math.max(0, contentHeight - editorRef.current.getLayoutInfo().height)
    syncing.current = true
    editorRef.current.setScrollTop((el.scrollTop / maxPreview) * maxEditor)
    requestAnimationFrame(() => { syncing.current = false })
  }

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
        {remote && <span className="remote-badge"><Cloud size={13} /> 云端</span>}
        {cached && <span className="cache-badge"><HardDriveDownload size={13} /> 本地缓存</span>}
        <div className="toolbar-fields">
          <input className="name-input" value={draft.title || ''} onChange={(e) => onFieldChange('title', e.target.value)} placeholder="笔记名称" title="笔记名称（另存为可新建副本）" />
          <input className="folder-input" value={draft.folder || ''} onChange={(e) => onFieldChange('folder', e.target.value)} placeholder="文件夹（用 / 分层）" />
          <input className="tags-input" value={(draft.tags || []).join(', ')} onChange={(e) => onFieldChange('tags', e.target.value)} placeholder="标签，逗号分隔" />
        </div>
        <div className="toolbar-actions">
          <button className="small" onClick={onSaveAs} title="按名称另存为新的本地笔记"><Copy size={14} /> 另存为</button>
          <button className={`small ${scrollSync ? 'active' : ''}`} onClick={() => onScrollSyncChange(!scrollSync)} title="编辑器与预览滚动同步">
            <Link2 size={14} /> 同步滚动
          </button>
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
            onMount={(editor) => {
              editorRef.current = editor
              editor.onDidScrollChange(syncToPreview)
            }}
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
          <div className="preview-pane" ref={previewRef} onScroll={syncToEditor}>
            <div className="preview-header">预览</div>
            <div className="markdown-body">
              <ReactMarkdown remarkPlugins={[remarkGfm, remarkMath]} rehypePlugins={[rehypeKatex, rehypeHighlight]}>
                {draft.content || ''}
              </ReactMarkdown>
            </div>
          </div>
        )}
      </div>
    </div>
  )
}
