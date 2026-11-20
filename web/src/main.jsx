import React from 'react'
import { createRoot } from 'react-dom/client'
import * as monaco from 'monaco-editor'
import { loader } from '@monaco-editor/react'
import EditorWorker from 'monaco-editor/esm/vs/editor/editor.worker?worker'

import 'katex/dist/katex.min.css'
import 'highlight.js/styles/github-dark.css'
import './styles.css'
import App from './App.jsx'

// 使用本地打包的 Monaco，离线可用，不走 CDN
self.MonacoEnvironment = {
  getWorker() {
    return new EditorWorker()
  },
}
loader.config({ monaco })

createRoot(document.getElementById('root')).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>,
)
