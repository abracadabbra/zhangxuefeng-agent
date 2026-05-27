import { useState, Component, type ReactNode } from 'react'
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

// 工具名称中文化映射
const TOOL_NAME_MAP: Record<string, string> = {
  search_admission: '搜索录取分数线',
  calculate_match: '分数匹配推荐',
  search_employment: '就业数据查询',
  compare_schools: '院校对比',
  search_policy: '政策查询',
}

function getToolDisplayName(name: string): string {
  return TOOL_NAME_MAP[name] || name
}

interface SourcePanelProps {
  sources: ToolCall[]
}

export default function SourcePanel({ sources }: SourcePanelProps) {
  const [selectedSource, setSelectedSource] = useState<ToolCall | null>(null)

  if (sources.length === 0) {
    return (
      <div className="w-80 border-2 border-ink bg-paper flex flex-col">
        <div className="border-b-2 border-ink px-4 py-3 bg-paper-dark/50">
          <h3 className="font-serif font-bold text-ink">参考文献</h3>
        </div>
        <div className="flex-1 p-4">
          <p className="text-sm text-ink-light font-serif italic">暂无数据来源</p>
        </div>
      </div>
    )
  }

  return (
    <ErrorBoundary>
      <div className="w-80 border-2 border-ink bg-paper flex flex-col">
        <div className="border-b-2 border-ink px-4 py-3 bg-paper-dark/50">
          <div className="flex items-center justify-between">
            <h3 className="font-serif font-bold text-ink">参考文献</h3>
            <span className="text-xs font-mono text-ink-light">{sources.length} 条</span>
          </div>
        </div>
        <div className="flex-1 overflow-y-auto p-4 space-y-3">
          {sources.map((source, idx) => (
            <SourceCard
              key={source.id}
              source={source}
              index={idx + 1}
              onClick={() => setSelectedSource(source)}
            />
          ))}
        </div>
      </div>

      {selectedSource && (
        <SourceModal
          source={selectedSource}
          onClose={() => setSelectedSource(null)}
        />
      )}
    </ErrorBoundary>
  )
}

interface SourceCardProps {
  source: ToolCall
  index: number
  onClick: () => void
}

function SourceCard({ source, index, onClick }: SourceCardProps) {
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

  let preview = '等待结果...'
  if (source.result) {
    try {
      const data = JSON.parse(source.result)
      if (data.status === 'not_found') preview = data.message || '未找到数据'
      else if (data.status === 'not_implemented') preview = '待实现'
      else if (data.status === 'error') preview = data.message || '查询出错'
      else preview = '查询成功，点击查看'
    } catch {
      preview = '点击查看详细'
    }
  }

  return (
    <button
      type="button"
      className="w-full text-left border border-rule p-3 hover:border-ink hover:bg-paper-dark transition-colors cursor-pointer group"
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
        </div>
      </div>
    </button>
  )
}

function FreshnessBadge({ status }: { status: 'success' | 'not_found' | 'not_implemented' | 'error' | 'pending' }) {
  const config = {
    success: { label: '正常', className: 'border-green-600 text-green-600' },
    not_found: { label: '未找到', className: 'border-orange-500 text-orange-500' },
    not_implemented: { label: '待实现', className: 'border-ink-light text-ink-light' },
    error: { label: '错误', className: 'border-red text-red' },
    pending: { label: '等待中', className: 'border-ink-light text-ink-light' },
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
}

function SourceModal({ source, onClose }: SourceModalProps) {
  return (
    <div
      className="fixed inset-0 bg-ink/50 flex items-center justify-center z-50 p-4"
      onClick={(e) => { if (e.target === e.currentTarget) onClose() }}
    >
      <div className="bg-paper border-2 border-ink max-w-lg w-full max-h-[80vh] flex flex-col">
        <div className="flex items-center justify-between px-4 py-3 border-b-2 border-ink bg-paper-dark/50">
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
            关闭
          </button>
        </div>
      </div>
    </div>
  )
}

function SourceDetail({ result }: { result?: string }) {
  if (!result) {
    return <p className="text-sm text-ink-light font-serif italic">等待结果...</p>
  }

  try {
    const data = JSON.parse(result)

    if (data.status === 'not_implemented') {
      return (
        <div className="text-sm text-ink-light">
          <p className="font-bold font-serif mb-1">状态：待实现</p>
          <p className="font-serif">此功能尚未完成</p>
        </div>
      )
    }

    if (data.status === 'not_found') {
      return (
        <div className="text-sm">
          <p className="font-bold font-serif mb-1 text-red">状态：未找到</p>
          <p className="font-serif text-ink">{String(data.message || '未找到匹配数据')}</p>
          {data.suggestions && <p className="mt-2 text-ink-light font-serif">建议：{String(data.suggestions)}</p>}
        </div>
      )
    }

    if (data.status === 'error') {
      return (
        <div className="text-sm">
          <p className="font-bold font-serif mb-1 text-red">状态：错误</p>
          <p className="font-serif text-ink">{String(data.message || '查询失败')}</p>
        </div>
      )
    }

    // 结构化数据表格显示
    if (data.results && Array.isArray(data.results)) {
      return (
        <div className="space-y-4">
          {data.query && (
            <div className="flex gap-2 text-sm">
              <span className="font-mono text-ink-light">查询：</span>
              <span className="font-serif text-ink">{String(data.query)}</span>
            </div>
          )}
          {data.source && (
            <div className="flex gap-2 text-sm">
              <span className="font-mono text-ink-light">数据源：</span>
              <span className="font-serif text-ink">{String(data.source)}</span>
            </div>
          )}
          <div className="border border-ink">
            <div className="bg-ink text-paper px-3 py-2 font-mono text-xs font-bold">
              查询结果 · {data.results.length} 条
            </div>
            <div className="divide-y divide-rule">
              {data.results.slice(0, 10).map((item: Record<string, unknown>, idx: number) => (
                <div key={idx} className="px-3 py-2 text-sm">
                  {Object.entries(item).map(([key, value]) => (
                    <div key={key} className="flex gap-2 py-0.5">
                      <span className="font-mono text-ink-light text-xs min-w-[80px]">{key}:</span>
                      <span className="font-serif text-ink text-xs">{String(value)}</span>
                    </div>
                  ))}
                </div>
              ))}
            </div>
            {data.results.length > 10 && (
              <div className="px-3 py-2 text-xs text-ink-light font-mono border-t border-rule">
                ... 还有 {data.results.length - 10} 条结果
              </div>
            )}
          </div>
        </div>
      )
    }

    // 限制 JSON 显示大小，防止大对象导致浏览器崩溃
    const jsonStr = JSON.stringify(data, null, 2)
    const displayStr = jsonStr.length > 5000 ? jsonStr.slice(0, 5000) + '\n... (数据过大已截断)' : jsonStr

    return (
      <div className="space-y-3 text-sm">
        <div className="rule-single pt-3">
          <p className="font-mono text-ink-light mb-2 text-xs">完整数据：</p>
          <pre className="bg-paper-dark border border-rule p-3 overflow-x-auto whitespace-pre-wrap break-words font-mono text-xs leading-relaxed max-h-80 overflow-y-auto">
            {displayStr}
          </pre>
        </div>
      </div>
    )
  } catch {
    const displayResult = result.length > 2000 ? result.slice(0, 2000) + '... (已截断)' : result
    return (
      <div className="text-sm">
        <p className="font-mono text-ink-light mb-2 text-xs">详细内容：</p>
        <div className="bg-paper-dark border border-rule p-3 whitespace-pre-wrap break-words max-h-80 overflow-y-auto font-serif text-xs">
          {displayResult}
        </div>
      </div>
    )
  }
}
