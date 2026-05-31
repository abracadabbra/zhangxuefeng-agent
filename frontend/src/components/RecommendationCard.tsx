import { useState } from 'react'

// ── Data Types ──────────────────────────────────────────────

interface SchoolRecommendation {
  school_name: string
  reason: string
  admission_probability: number
  match_score: number
}

interface MajorRecommendation {
  major_name: string
  category: string
  reason: string
  employment_rate: number
  avg_salary: number
}

type RecommendationProps =
  | { type: 'school'; data: SchoolRecommendation }
  | { type: 'major'; data: MajorRecommendation }

// ── Helpers ─────────────────────────────────────────────────

function probabilityLabel(p: number): string {
  if (p >= 0.8) return '稳妥'
  if (p >= 0.5) return '适中'
  if (p >= 0.3) return '冲刺'
  return '搏一搏'
}

function scoreBarWidth(score: number): string {
  const clamped = Math.max(0, Math.min(1, score))
  return `${Math.round(clamped * 100)}%`
}

// ── Component ───────────────────────────────────────────────

export default function RecommendationCard(props: RecommendationProps) {
  const [expanded, setExpanded] = useState(false)

  if (props.type === 'school') {
    return <SchoolCard data={props.data} expanded={expanded} onToggle={() => setExpanded((v) => !v)} />
  }
  return <MajorCard data={props.data} expanded={expanded} onToggle={() => setExpanded((v) => !v)} />
}

// ── School Card ─────────────────────────────────────────────

interface SchoolCardProps {
  data: SchoolRecommendation
  expanded: boolean
  onToggle: () => void
}

function SchoolCard({ data, expanded, onToggle }: SchoolCardProps) {
  const prob = data.admission_probability
  const probLabel = probabilityLabel(prob)
  const probPercent = Math.round(prob * 100)

  return (
    <article
      className="border-2 border-ink bg-paper transition-all duration-300 hover:shadow-warm-lg cursor-pointer"
      onClick={onToggle}
      role="button"
      tabIndex={0}
      onKeyDown={(e) => {
        if (e.key === 'Enter' || e.key === ' ') {
          e.preventDefault()
          onToggle()
        }
      }}
    >
      {/* Header */}
      <div className="px-5 py-4 border-b border-rule">
        <div className="flex items-start justify-between gap-3">
          <div className="min-w-0 flex-1">
            <h3 className="text-lg font-bold text-ink font-serif tracking-wide truncate">
              {data.school_name}
            </h3>
          </div>
          <span
            className={`stamp text-xs flex-shrink-0 ${
              prob >= 0.8
                ? 'bg-ink text-gold'
                : prob >= 0.5
                  ? 'bg-gold text-ink'
                  : 'bg-paper-dark text-ink border border-ink'
            }`}
          >
            {probLabel}
          </span>
        </div>
      </div>

      {/* Metrics */}
      <div className="px-5 py-4 space-y-3">
        {/* Match Score */}
        <div>
          <div className="flex items-center justify-between text-xs font-mono text-ink-light mb-1">
            <span>匹配度</span>
            <span>{Math.round(data.match_score * 100)}%</span>
          </div>
          <div className="h-2 bg-paper-dark border border-rule">
            <div
              className="h-full bg-ink transition-all duration-500"
              style={{ width: scoreBarWidth(data.match_score) }}
            />
          </div>
        </div>

        {/* Admission Probability */}
        <div>
          <div className="flex items-center justify-between text-xs font-mono text-ink-light mb-1">
            <span>录取概率</span>
            <span>{probPercent}%</span>
          </div>
          <div className="h-2 bg-paper-dark border border-rule">
            <div
              className="h-full bg-gold transition-all duration-500"
              style={{ width: scoreBarWidth(prob) }}
            />
          </div>
        </div>
      </div>

      {/* Expandable Reason */}
      <div className={`overflow-hidden transition-all duration-300 ${expanded ? 'max-h-96' : 'max-h-0'}`}>
        <div className="px-5 py-4 border-t border-rule">
          <div className="flex items-center gap-2 mb-2">
            <span className="w-5 h-5 bg-ink text-gold flex items-center justify-center font-mono text-[10px]">
              "
            </span>
            <span className="text-xs font-mono text-ink-light">推荐理由</span>
          </div>
          <p className="text-sm font-serif text-ink leading-relaxed">
            {data.reason}
          </p>
        </div>
      </div>

      {/* Expand Toggle */}
      <div className="px-5 py-2 border-t border-rule flex items-center justify-center gap-1 text-xs font-mono text-ink-light">
        <span>{expanded ? '收起' : '展开详情'}</span>
        <svg
          className={`w-3 h-3 transition-transform duration-300 ${expanded ? 'rotate-180' : ''}`}
          fill="none"
          viewBox="0 0 24 24"
          stroke="currentColor"
          strokeWidth={2}
        >
          <path strokeLinecap="round" strokeLinejoin="round" d="M19 9l-7 7-7-7" />
        </svg>
      </div>
    </article>
  )
}

// ── Major Card ──────────────────────────────────────────────

interface MajorCardProps {
  data: MajorRecommendation
  expanded: boolean
  onToggle: () => void
}

function MajorCard({ data, expanded, onToggle }: MajorCardProps) {
  const empPercent = Math.round(data.employment_rate * 100)

  return (
    <article
      className="border-2 border-ink bg-paper transition-all duration-300 hover:shadow-warm-lg cursor-pointer"
      onClick={onToggle}
      role="button"
      tabIndex={0}
      onKeyDown={(e) => {
        if (e.key === 'Enter' || e.key === ' ') {
          e.preventDefault()
          onToggle()
        }
      }}
    >
      {/* Header */}
      <div className="px-5 py-4 border-b border-rule">
        <div className="flex items-start justify-between gap-3">
          <div className="min-w-0 flex-1">
            <h3 className="text-lg font-bold text-ink font-serif tracking-wide truncate">
              {data.major_name}
            </h3>
            <span className="text-xs font-mono text-ink-light">{data.category}</span>
          </div>
          <span className="stamp text-xs flex-shrink-0 bg-ink text-gold">
            {data.category}
          </span>
        </div>
      </div>

      {/* Metrics */}
      <div className="px-5 py-4">
        <div className="grid grid-cols-2 gap-4">
          {/* Employment Rate */}
          <div>
            <div className="text-xs font-mono text-ink-light mb-1">就业率</div>
            <div className="flex items-baseline gap-1">
              <span className="text-2xl font-bold text-ink font-mono">{empPercent}</span>
              <span className="text-sm text-ink-light font-mono">%</span>
            </div>
          </div>
          {/* Average Salary */}
          <div>
            <div className="text-xs font-mono text-ink-light mb-1">平均薪资</div>
            <div className="flex items-baseline gap-1">
              <span className="text-2xl font-bold text-ink font-mono">{data.avg_salary}</span>
              <span className="text-sm text-ink-light font-mono">元/月</span>
            </div>
          </div>
        </div>
      </div>

      {/* Expandable Reason */}
      <div className={`overflow-hidden transition-all duration-300 ${expanded ? 'max-h-96' : 'max-h-0'}`}>
        <div className="px-5 py-4 border-t border-rule">
          <div className="flex items-center gap-2 mb-2">
            <span className="w-5 h-5 bg-ink text-gold flex items-center justify-center font-mono text-[10px]">
              "
            </span>
            <span className="text-xs font-mono text-ink-light">推荐理由</span>
          </div>
          <p className="text-sm font-serif text-ink leading-relaxed">
            {data.reason}
          </p>
        </div>
      </div>

      {/* Expand Toggle */}
      <div className="px-5 py-2 border-t border-rule flex items-center justify-center gap-1 text-xs font-mono text-ink-light">
        <span>{expanded ? '收起' : '展开详情'}</span>
        <svg
          className={`w-3 h-3 transition-transform duration-300 ${expanded ? 'rotate-180' : ''}`}
          fill="none"
          viewBox="0 0 24 24"
          stroke="currentColor"
          strokeWidth={2}
        >
          <path strokeLinecap="round" strokeLinejoin="round" d="M19 9l-7 7-7-7" />
        </svg>
      </div>
    </article>
  )
}
