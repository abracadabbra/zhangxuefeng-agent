import { useState, Component, type ReactNode } from 'react'
import { useTranslation } from 'react-i18next'
import type { ToolCall } from '../types'

// 错误边界组件
class ErrorBoundary extends Component<{ children: ReactNode }, { hasError: boolean }> {
  state = { hasError: false }

  static getDerivedStateFromError() {
    return { hasError: true }
  }

  render() {
    if (this.state.hasError) {
      return (
        <div className="p-4 text-sm text-red">
          渲染出错，请刷新页面重试
        </div>
      )
    }
    return this.props.children
  }
}

interface SourcePanelProps {
  sources: ToolCall[]
  onClose?: () => void
}

export default function SourcePanel({ sources, onClose }: SourcePanelProps) {
  const { t } = useTranslation()
  const [selectedSource, setSelectedSource] = useState<ToolCall | null>(null)

  const getToolDisplayName = (name: string): string => {
    const key = `sourcePanel.toolNames.${name}` as const
    const translated = t(key)
    return translated === key ? name : translated
  }

  if (sources.length === 0) {
    return (
      <div className="w-full lg:w-80 border-2 border-ink dark:border-night-border bg-paper dark:bg-night-card flex flex-col h-full">
        <div className="border-b-2 border-ink dark:border-night-border px-4 py-3 bg-paper-dark/50 dark:bg-night/50">
          <div className="flex items-center justify-between">
            <h3 className="font-serif font-bold text-ink dark:text-paper">{t('sourcePanel.title')}</h3>
            {onClose && (
              <button type="button" onClick={onClose} className="lg:hidden text-ink-light dark:text-night-muted hover:text-ink dark:hover:text-paper text-lg px-1">
                &times;
              </button>
            )}
          </div>
        </div>
        <div className="flex-1 p-4">
          <p className="text-sm text-ink-light dark:text-night-muted font-serif italic">{t('sourcePanel.noData')}</p>
        </div>
      </div>
    )
  }

  return (
    <ErrorBoundary>
      <div className="w-full lg:w-80 border-2 border-ink dark:border-night-border bg-paper dark:bg-night-card flex flex-col h-full">
        <div className="border-b-2 border-ink dark:border-night-border px-4 py-3 bg-paper-dark/50 dark:bg-night/50">
          <div className="flex items-center justify-between">
            <h3 className="font-serif font-bold text-ink dark:text-paper">{t('sourcePanel.title')}</h3>
            <div className="flex items-center gap-2">
              <span className="text-xs font-mono text-ink-light dark:text-night-muted">{t('sourcePanel.count', { count: sources.length })}</span>
              {onClose && (
                <button type="button" onClick={onClose} className="lg:hidden text-ink-light dark:text-night-muted hover:text-ink dark:hover:text-paper text-lg px-1 leading-none">
                  &times;
                </button>
              )}
            </div>
          </div>
        </div>
        <div className="flex-1 overflow-y-auto p-4 space-y-3">
          {sources.map((source, idx) => (
            <SourceCard
              key={source.id}
              source={source}
              index={idx + 1}
              onClick={() => setSelectedSource(source)}
              getToolDisplayName={getToolDisplayName}
            />
          ))}
        </div>
      </div>

      {selectedSource && (
        <SourceModal
          source={selectedSource}
          onClose={() => setSelectedSource(null)}
          getToolDisplayName={getToolDisplayName}
        />
      )}
    </ErrorBoundary>
  )
}

interface SourceCardProps {
  source: ToolCall
  index: number
  onClick: () => void
  getToolDisplayName: (name: string) => string
}

function SourceCard({ source, index, onClick, getToolDisplayName }: SourceCardProps) {
  const { t } = useTranslation()
  let status: 'success' | 'not_found' | 'not_implemented' | 'error' | 'pending' = 'pending'
  if (source.result) {
    try {
      const data = JSON.parse(source.result)
      if (data.status === 'not_found') status = 'not_found'
      else if (data.status === 'not_implemented') status = 'not_implemented'
      else if (data.status === 'error') status = 'error'
      else status = 'success'
    } catch {
      status = 'success'
    }
  }

  let preview = t('sourcePanel.waiting')
  if (source.result) {
    try {
      const data = JSON.parse(source.result)
      if (data.status === 'not_found') preview = data.message || t('sourcePanel.notFound')
      else if (data.status === 'not_implemented') preview = t('sourcePanel.notImplemented')
      else if (data.status === 'error') preview = data.message || t('sourcePanel.queryError')
      else preview = t('sourcePanel.querySuccess')
    } catch {
      preview = t('sourcePanel.clickDetail')
    }
  }

  return (
    <button
      type="button"
      className="w-full text-left border border-rule dark:border-night-border p-3
                 hover:border-ink dark:hover:border-gold hover:bg-paper-dark dark:hover:bg-night-border/30
                 transition-colors cursor-pointer group"
      onClick={(e) => { e.stopPropagation(); onClick() }}
    >
      <div className="flex items-start gap-2">
        {/* 编号 */}
        <span className="w-6 h-6 bg-ink dark:bg-gold text-gold dark:text-ink flex items-center justify-center font-mono text-xs flex-shrink-0">
          {index}
        </span>
        <div className="flex-1 min-w-0">
          <div className="flex items-center justify-between gap-2">
            <span className="text-sm font-mono text-ink dark:text-paper truncate">{getToolDisplayName(source.name)}</span>
            <FreshnessBadge status={status} />
          </div>
          <p className="text-xs text-ink-light dark:text-night-muted font-serif mt-1 truncate">{preview}</p>
        </div>
      </div>
    </button>
  )
}

function FreshnessBadge({ status }: { status: 'success' | 'not_found' | 'not_implemented' | 'error' | 'pending' }) {
  const { t } = useTranslation()
  const config = {
    success: { label: t('sourcePanel.status.success'), className: 'border-green-600 text-green-600' },
    not_found: { label: t('sourcePanel.status.notFound'), className: 'border-orange-500 text-orange-500' },
    not_implemented: { label: t('sourcePanel.status.notImplemented'), className: 'border-ink-light dark:border-night-muted text-ink-light dark:text-night-muted' },
    error: { label: t('sourcePanel.status.error'), className: 'border-red text-red' },
    pending: { label: t('sourcePanel.status.pending'), className: 'border-ink-light dark:border-night-muted text-ink-light dark:text-night-muted' },
  }
  const { label, className } = config[status]
  return (
    <span className={`inline-flex items-center px-2 py-0.5 border text-[10px] font-mono font-bold ${className}`}>
      {label}
    </span>
  )
}

interface SourceModalProps {
  source: ToolCall
  onClose: () => void
  getToolDisplayName: (name: string) => string
}

function SourceModal({ source, onClose, getToolDisplayName }: SourceModalProps) {
  const { t } = useTranslation()
  return (
    <div
      className="fixed inset-0 bg-ink/50 dark:bg-black/60 flex items-center justify-center z-50 p-4"
      onClick={(e) => { if (e.target === e.currentTarget) onClose() }}
    >
      <div className="bg-paper dark:bg-night-card border-2 border-ink dark:border-night-border max-w-lg w-full max-h-[80vh] flex flex-col">
        <div className="flex items-center justify-between px-4 py-3 border-b-2 border-ink dark:border-night-border bg-paper-dark/50 dark:bg-night/50">
          <h3 className="text-base font-bold font-serif text-ink dark:text-paper">{getToolDisplayName(source.name)}</h3>
          <button type="button" onClick={onClose} className="text-ink-light dark:text-night-muted hover:text-ink dark:hover:text-paper text-xl leading-none px-2">
            &times;
          </button>
        </div>
        <div className="flex-1 overflow-y-auto p-4">
          <ErrorBoundary>
            <SourceDetail result={source.result} />
          </ErrorBoundary>
        </div>
        <div className="px-4 py-3 border-t-2 border-ink dark:border-night-border">
          <button type="button" onClick={onClose} className="w-full px-4 py-2 bg-ink dark:bg-gold text-paper dark:text-ink font-serif font-bold hover:bg-ink-light dark:hover:bg-gold/80 transition-colors text-sm">
            {t('sourcePanel.detail.close')}
          </button>
        </div>
      </div>
    </div>
  )
}

function SourceDetail({ result }: { result?: string }) {
  const { t } = useTranslation()

  if (!result) {
    return <p className="text-sm text-ink-light dark:text-night-muted font-serif italic">{t('sourcePanel.waiting')}</p>
  }

  try {
    const data = JSON.parse(result)

    if (data.status === 'not_implemented') {
      return (
        <div className="text-sm text-ink-light dark:text-night-muted">
          <p className="font-bold font-serif mb-1">{t('sourcePanel.detail.statusNotImplemented')}</p>
          <p className="font-serif">{t('sourcePanel.detail.notImplementedDesc')}</p>
        </div>
      )
    }

    if (data.status === 'not_found') {
      return (
        <div className="text-sm">
          <p className="font-bold font-serif mb-1 text-red">{t('sourcePanel.detail.statusNotFound')}</p>
          <p className="font-serif text-ink dark:text-paper">{String(data.message || t('sourcePanel.detail.noMatchData'))}</p>
          {data.suggestions && <p className="mt-2 text-ink-light dark:text-night-muted font-serif">Suggestions: {String(data.suggestions)}</p>}
        </div>
      )
    }

    if (data.status === 'error') {
      return (
        <div className="text-sm">
          <p className="font-bold font-serif mb-1 text-red">{t('sourcePanel.detail.statusError')}</p>
          <p className="font-serif text-ink dark:text-paper">{String(data.message || t('sourcePanel.detail.queryFailed'))}</p>
        </div>
      )
    }

    // 结构化数据表格显示
    if (data.results && Array.isArray(data.results)) {
      return (
        <div className="space-y-4">
          {data.query && (
            <div className="flex gap-2 text-sm">
              <span className="font-mono text-ink-light dark:text-night-muted">{t('sourcePanel.detail.queryLabel')}</span>
              <span className="font-serif text-ink dark:text-paper">{String(data.query)}</span>
            </div>
          )}
          {data.source && (
            <div className="flex gap-2 text-sm">
              <span className="font-mono text-ink-light dark:text-night-muted">{t('sourcePanel.detail.sourceLabel')}</span>
              <span className="font-serif text-ink dark:text-paper">{String(data.source)}</span>
            </div>
          )}
          <div className="border border-ink dark:border-night-border">
            <div className="bg-ink dark:bg-gold text-paper dark:text-ink px-3 py-2 font-mono text-xs font-bold">
              {t('sourcePanel.detail.resultTitle', { count: data.results.length })}
            </div>
            <div className="divide-y divide-rule dark:divide-night-border">
              {data.results.slice(0, 10).map((item: Record<string, unknown>, idx: number) => (
                <div key={idx} className="px-3 py-2 text-sm">
                  {Object.entries(item).map(([key, value]) => (
                    <div key={key} className="flex gap-2 py-0.5">
                      <span className="font-mono text-ink-light dark:text-night-muted text-xs min-w-[80px]">{key}:</span>
                      <span className="font-serif text-ink dark:text-paper text-xs">{String(value)}</span>
                    </div>
                  ))}
                </div>
              ))}
            </div>
            {data.results.length > 10 && (
              <div className="px-3 py-2 text-xs text-ink-light dark:text-night-muted font-mono border-t border-rule dark:border-night-border">
                {t('sourcePanel.detail.moreResults', { count: data.results.length - 10 })}
              </div>
            )}
          </div>
        </div>
      )
    }

    // 限制 JSON 显示大小，防止大对象导致浏览器崩溃
    const jsonStr = JSON.stringify(data, null, 2)
    const displayStr = jsonStr.length > 5000 ? jsonStr.slice(0, 5000) + `\n... (${t('sourcePanel.detail.dataTruncated')})` : jsonStr

    return (
      <div className="space-y-3 text-sm">
        <div className="rule-single pt-3">
          <p className="font-mono text-ink-light dark:text-night-muted mb-2 text-xs">{t('sourcePanel.detail.fullData')}</p>
          <pre className="bg-paper-dark dark:bg-night border border-rule dark:border-night-border p-3 overflow-x-auto whitespace-pre-wrap break-words font-mono text-xs leading-relaxed max-h-80 overflow-y-auto text-ink dark:text-paper">
            {displayStr}
          </pre>
        </div>
      </div>
    )
  } catch {
    const displayResult = result.length > 2000 ? result.slice(0, 2000) + `... (${t('sourcePanel.detail.resultTruncated')})` : result
    return (
      <div className="text-sm">
        <p className="font-mono text-ink-light dark:text-night-muted mb-2 text-xs">{t('sourcePanel.detail.detailContent')}</p>
        <div className="bg-paper-dark dark:bg-night border border-rule dark:border-night-border p-3 whitespace-pre-wrap break-words max-h-80 overflow-y-auto font-serif text-xs text-ink dark:text-paper">
          {displayResult}
        </div>
      </div>
    )
  }
}
