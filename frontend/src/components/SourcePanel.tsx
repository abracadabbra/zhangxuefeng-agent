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
      <div className="w-full lg:w-80 border-2 border-ink bg-paper flex flex-col h-full">
        <div className="border-b-2 border-ink px-4 py-3 bg-paper-dark/50/50">
          <div className="flex items-center justify-between">
            <h3 className="font-serif font-bold text-ink">{t('sourcePanel.title')}</h3>
            {onClose && (
              <button type="button" onClick={onClose} className="lg:hidden text-ink-light hover:text-ink text-lg px-1">
                &times;
              </button>
            )}
          </div>
        </div>
        <div className="flex-1 p-4">
          <p className="text-sm text-ink-light font-serif italic">{t('sourcePanel.noData')}</p>
        </div>
      </div>
    )
  }

  return (
    <ErrorBoundary>
      <div className="w-full lg:w-80 border-2 border-ink bg-paper flex flex-col h-full">
        <div className="border-b-2 border-ink px-4 py-3 bg-paper-dark/50/50">
          <div className="flex items-center justify-between">
            <h3 className="font-serif font-bold text-ink">{t('sourcePanel.title')}</h3>
            <div className="flex items-center gap-2">
              <span className="text-xs font-mono text-ink-light">{t('sourcePanel.count', { count: sources.length })}</span>
              {onClose && (
                <button type="button" onClick={onClose} className="lg:hidden text-ink-light hover:text-ink text-lg px-1 leading-none">
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

type Confidence = 'high' | 'medium' | 'low'

interface SourceMetadata {
  confidence?: Confidence
  sourceType?: string
  source?: string
}

interface StructuredResults {
  items: Record<string, unknown>[]
}

function isConfidence(value: unknown): value is Confidence {
  return value === 'high' || value === 'medium' || value === 'low'
}

function confidenceLabel(confidence: Confidence) {
  const labels = {
    high: '高可信',
    medium: '中可信',
    low: '低可信',
  }
  return labels[confidence]
}

function confidenceClass(confidence: Confidence) {
  const classes = {
    high: 'border-green-600 text-green-600',
    medium: 'border-gold text-ink',
    low: 'border-orange-500 text-orange-500',
  }
  return classes[confidence]
}

function sourceTypeLabel(sourceType: string) {
  const labels: Record<string, string> = {
    vector_index: '向量索引',
    database: '结构化库',
    policy: '政策库',
  }
  return labels[sourceType] || sourceType
}

function extractSourceMetadata(data: unknown): SourceMetadata {
  if (!data || typeof data !== 'object') return {}
  const record = data as Record<string, unknown>
  const results = record.results
  const firstResult = Array.isArray(results) && results[0] && typeof results[0] === 'object'
    ? results[0] as Record<string, unknown>
    : {}
  const confidence = isConfidence(firstResult.confidence)
    ? firstResult.confidence
    : isConfidence(record.confidence)
      ? record.confidence
      : undefined
  const sourceType = typeof firstResult.source_type === 'string'
    ? firstResult.source_type
    : typeof record.source_type === 'string'
      ? record.source_type
      : undefined
  const source = typeof firstResult.source === 'string'
    ? firstResult.source
    : typeof record.source === 'string'
      ? record.source
      : undefined

  return { confidence, sourceType, source }
}

function extractStructuredResults(data: Record<string, unknown>): StructuredResults | null {
  const resultKeys = ['results', 'scores', 'schools', 'matched_schools']
  for (const key of resultKeys) {
    const value = data[key]
    if (Array.isArray(value)) {
      return {
        items: value.filter(
          (item): item is Record<string, unknown> => Boolean(item) && typeof item === 'object',
        ),
      }
    }
  }
  return null
}

function formatDetailValue(value: unknown): string {
  if (value === null || value === undefined) return ''
  if (typeof value === 'string' || typeof value === 'number' || typeof value === 'boolean') return String(value)
  return JSON.stringify(value)
}

function SourceCard({ source, index, onClick, getToolDisplayName }: SourceCardProps) {
  const { t } = useTranslation()
  let status: 'success' | 'not_found' | 'not_implemented' | 'error' | 'pending' = 'pending'
  let metadata: SourceMetadata = {}
  if (source.result) {
    try {
      const data = JSON.parse(source.result)
      if (data.status === 'not_found') status = 'not_found'
      else if (data.status === 'not_implemented') status = 'not_implemented'
      else if (data.status === 'error') status = 'error'
      else status = 'success'
      metadata = extractSourceMetadata(data)
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
      className="w-full text-left border border-rule p-3
                 hover:border-ink hover:bg-paper-dark
                 transition-colors cursor-pointer group"
      onClick={(e) => { e.stopPropagation(); onClick() }}
    >
      <div className="flex items-start gap-2">
        {/* 编号 */}
        <span className="w-6 h-6 bg-ink text-gold flex items-center justify-center font-mono text-xs flex-shrink-0">
          {index}
        </span>
        <div className="flex-1 min-w-0">
          <div className="flex items-center justify-between gap-2">
            <span className="text-sm font-mono text-ink truncate">{getToolDisplayName(source.name)}</span>
            <FreshnessBadge status={status} />
          </div>
          <p className="text-xs text-ink-light font-serif mt-1 truncate">{preview}</p>
          <SourceMetadataBadges metadata={metadata} className="mt-2 flex flex-wrap gap-1.5" />
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
    not_implemented: { label: t('sourcePanel.status.notImplemented'), className: 'border-ink-light text-ink-light' },
    error: { label: t('sourcePanel.status.error'), className: 'border-red text-red' },
    pending: { label: t('sourcePanel.status.pending'), className: 'border-ink-light text-ink-light' },
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
      className="fixed inset-0 bg-ink/50 flex items-center justify-center z-50 p-4"
      onClick={(e) => { if (e.target === e.currentTarget) onClose() }}
    >
      <div className="bg-paper border-2 border-ink max-w-lg w-full max-h-[80vh] flex flex-col">
        <div className="flex items-center justify-between px-4 py-3 border-b-2 border-ink bg-paper-dark/50/50">
          <h3 className="text-base font-bold font-serif text-ink">{getToolDisplayName(source.name)}</h3>
          <button type="button" onClick={onClose} className="text-ink-light hover:text-ink text-xl leading-none px-2">
            &times;
          </button>
        </div>
        <div className="flex-1 overflow-y-auto p-4">
          <ErrorBoundary>
            <SourceDetail result={source.result} />
          </ErrorBoundary>
        </div>
        <div className="px-4 py-3 border-t-2 border-ink">
          <button type="button" onClick={onClose} className="w-full px-4 py-2 bg-ink text-paper font-serif font-bold hover:bg-ink-light transition-colors text-sm">
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
    return <p className="text-sm text-ink-light font-serif italic">{t('sourcePanel.waiting')}</p>
  }

  try {
    const data = JSON.parse(result)
    const metadata = extractSourceMetadata(data)
    const structuredResults = extractStructuredResults(data)

    if (data.status === 'not_implemented') {
      return (
        <div className="text-sm text-ink-light">
          <p className="font-bold font-serif mb-1">{t('sourcePanel.detail.statusNotImplemented')}</p>
          <p className="font-serif">{t('sourcePanel.detail.notImplementedDesc')}</p>
        </div>
      )
    }

    if (data.status === 'not_found') {
      return (
        <div className="text-sm">
          <p className="font-bold font-serif mb-1 text-red">{t('sourcePanel.detail.statusNotFound')}</p>
          <p className="font-serif text-ink">{String(data.message || t('sourcePanel.detail.noMatchData'))}</p>
          {data.suggestions && <p className="mt-2 text-ink-light font-serif">Suggestions: {String(data.suggestions)}</p>}
        </div>
      )
    }

    if (data.status === 'error') {
      return (
        <div className="text-sm">
          <p className="font-bold font-serif mb-1 text-red">{t('sourcePanel.detail.statusError')}</p>
          <p className="font-serif text-ink">{String(data.message || t('sourcePanel.detail.queryFailed'))}</p>
        </div>
      )
    }

    // 结构化数据表格显示
    if (structuredResults) {
      return (
        <div className="space-y-4">
          <SourceMetadataBadges metadata={metadata} includeSource className="flex flex-wrap gap-1.5" />
          {data.query && (
            <div className="flex gap-2 text-sm">
              <span className="font-mono text-ink-light">{t('sourcePanel.detail.queryLabel')}</span>
              <span className="font-serif text-ink">{formatDetailValue(data.query)}</span>
            </div>
          )}
          {data.source && (
            <div className="flex gap-2 text-sm">
              <span className="font-mono text-ink-light">{t('sourcePanel.detail.sourceLabel')}</span>
              <span className="font-serif text-ink">{formatDetailValue(data.source)}</span>
            </div>
          )}
          <div className="border border-ink">
            <div className="bg-ink text-paper px-3 py-2 font-mono text-xs font-bold">
              {t('sourcePanel.detail.resultTitle', { count: structuredResults.items.length })}
            </div>
            <div className="divide-y divide-rule">
              {structuredResults.items.slice(0, 10).map((item: Record<string, unknown>, idx: number) => (
                <div key={idx} className="px-3 py-2 text-sm">
                  <SourceResultBadges item={item} />
                  {Object.entries(item).map(([key, value]) => (
                    <div key={key} className="flex gap-2 py-0.5">
                      <span className="font-mono text-ink-light text-xs min-w-[80px]">{key}:</span>
                      <span className="font-serif text-ink text-xs">{formatDetailValue(value)}</span>
                    </div>
                  ))}
                </div>
              ))}
            </div>
            {structuredResults.items.length > 10 && (
              <div className="px-3 py-2 text-xs text-ink-light font-mono border-t border-rule">
                {t('sourcePanel.detail.moreResults', { count: structuredResults.items.length - 10 })}
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
          <p className="font-mono text-ink-light mb-2 text-xs">{t('sourcePanel.detail.fullData')}</p>
          <pre className="bg-paper-dark border border-rule p-3 overflow-x-auto whitespace-pre-wrap break-words font-mono text-xs leading-relaxed max-h-80 overflow-y-auto text-ink">
            {displayStr}
          </pre>
        </div>
      </div>
    )
  } catch {
    const displayResult = result.length > 2000 ? result.slice(0, 2000) + `... (${t('sourcePanel.detail.resultTruncated')})` : result
    return (
      <div className="text-sm">
        <p className="font-mono text-ink-light mb-2 text-xs">{t('sourcePanel.detail.detailContent')}</p>
        <div className="bg-paper-dark border border-rule p-3 whitespace-pre-wrap break-words max-h-80 overflow-y-auto font-serif text-xs text-ink">
          {displayResult}
        </div>
      </div>
    )
  }
}

function SourceResultBadges({ item }: { item: Record<string, unknown> }) {
  const metadata = extractSourceMetadata({ results: [item] })
  return <SourceMetadataBadges metadata={metadata} includeSource className="mb-2 flex flex-wrap gap-1.5" />
}

function SourceMetadataBadges({
  metadata,
  includeSource = false,
  className,
}: {
  metadata: SourceMetadata
  includeSource?: boolean
  className: string
}) {
  if (!metadata.confidence && !metadata.sourceType && (!includeSource || !metadata.source)) return null

  return (
    <div className={className}>
      {metadata.confidence && (
        <span className={`inline-flex border px-1.5 py-0.5 text-[10px] font-mono font-bold ${confidenceClass(metadata.confidence)}`}>
          {confidenceLabel(metadata.confidence)}
        </span>
      )}
      {metadata.sourceType && (
        <span className="inline-flex border border-ink/30 px-1.5 py-0.5 text-[10px] font-mono text-ink-light">
          {sourceTypeLabel(metadata.sourceType)}
        </span>
      )}
      {includeSource && metadata.source && (
        <span className="inline-flex max-w-full border border-ink/30 px-1.5 py-0.5 text-[10px] font-mono text-ink-light">
          {metadata.source}
        </span>
      )}
    </div>
  )
}
