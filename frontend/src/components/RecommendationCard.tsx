import { useState } from 'react'

// ── Data Types ──────────────────────────────────────────────

export interface SchoolRecommendation {
  school_name: string
  reason: string
  admission_probability: number
  match_score: number
  strategy?: '冲' | '稳' | '保' | null
  risk_points?: string[]
  alternatives?: string[]
}

export interface MajorRecommendation {
  major_name: string
  category: string
  reason: string
  employment_rate: number
  avg_salary: number
  strategy?: '冲' | '稳' | '保' | null
  risk_points?: string[]
  alternatives?: string[]
}

type RecommendationProps =
  | ({ type: 'school'; data: SchoolRecommendation } & FavoriteProps)
  | ({ type: 'major'; data: MajorRecommendation } & FavoriteProps)

interface FavoriteProps {
  isFavorite?: boolean
  onFavoriteToggle?: () => void
}

// ── Helpers ─────────────────────────────────────────────────

function probabilityLabel(p: number): string {
  if (p >= 0.8) return '稳妥'
  if (p >= 0.5) return '适中'
  if (p >= 0.3) return '冲刺'
  return '搏一搏'
}

function strategyLabel(strategy: string | null | undefined, probability?: number): string {
  if (strategy) return strategy
  if (probability == null) return '稳'
  if (probability >= 0.8) return '保'
  if (probability >= 0.55) return '稳'
  return '冲'
}

function scoreBarWidth(score: number): string {
  const normalized = score > 1 ? score / 10 : score
  const clamped = Math.max(0, Math.min(1, normalized))
  return `${Math.round(clamped * 100)}%`
}

function scorePercent(score: number): number {
  const normalized = score > 1 ? score / 10 : score
  return Math.round(Math.max(0, Math.min(1, normalized)) * 100)
}

function DetailList({ title, items }: { title: string; items?: string[] }) {
  if (!items?.length) return null
  return (
    <div className="mt-3">
      <div className="text-xs font-mono text-ink-light mb-1">{title}</div>
      <ul className="space-y-1">
        {items.map(item => (
          <li key={item} className="text-sm font-serif text-ink leading-relaxed">
            {item}
          </li>
        ))}
      </ul>
    </div>
  )
}

// ── Component ───────────────────────────────────────────────

export default function RecommendationCard(props: RecommendationProps) {
  const [expanded, setExpanded] = useState(false)

  if (props.type === 'school') {
    return (
      <SchoolCard
        data={props.data}
        expanded={expanded}
        isFavorite={props.isFavorite}
        onFavoriteToggle={props.onFavoriteToggle}
        onToggle={() => setExpanded((v) => !v)}
      />
    )
  }
  return (
    <MajorCard
      data={props.data}
      expanded={expanded}
      isFavorite={props.isFavorite}
      onFavoriteToggle={props.onFavoriteToggle}
      onToggle={() => setExpanded((v) => !v)}
    />
  )
}

// ── School Card ─────────────────────────────────────────────

interface SchoolCardProps {
  data: SchoolRecommendation
  expanded: boolean
  isFavorite?: boolean
  onFavoriteToggle?: () => void
  onToggle: () => void
}

function SchoolCard({ data, expanded, isFavorite, onFavoriteToggle, onToggle }: SchoolCardProps) {
  const prob = data.admission_probability
  const probLabel = probabilityLabel(prob)
  const probPercent = Math.round(prob * 100)
  const strategy = strategyLabel(data.strategy, prob)

  return (
    <article
      className="border-2 border-ink bg-paper transition-all duration-300 hover:shadow-warm-lg"
    >
      {/* Header */}
      <div className="px-5 py-4 border-b border-rule">
        <div className="flex items-start justify-between gap-3">
          <div className="min-w-0 flex-1">
            <h3 className="text-lg font-bold text-ink font-serif tracking-wide truncate">
              {data.school_name}
            </h3>
          </div>
          <div className="flex flex-shrink-0 items-center gap-2">
            {onFavoriteToggle && (
              <button
                type="button"
                aria-pressed={isFavorite}
                aria-label={`${isFavorite ? '取消收藏' : '收藏'} ${data.school_name}`}
                className={`border px-2 py-1 text-xs font-serif font-bold transition-colors ${
                  isFavorite
                    ? 'border-ink bg-ink text-gold'
                    : 'border-ink/30 bg-paper text-ink-light hover:border-ink hover:text-ink'
                }`}
                onClick={onFavoriteToggle}
              >
                {isFavorite ? '已收藏' : '收藏'}
              </button>
            )}
            <span
              className={`stamp text-xs ${
                strategy === '保'
                  ? 'bg-ink text-gold'
                  : strategy === '稳'
                    ? 'bg-gold text-ink'
                    : 'bg-paper-dark text-ink border border-ink'
              }`}
            >
              {strategy} · {probLabel}
            </span>
          </div>
        </div>
      </div>

      {/* Metrics */}
      <div className="px-5 py-4 space-y-3">
        {/* Match Score */}
        <div>
          <div className="flex items-center justify-between text-xs font-mono text-ink-light mb-1">
            <span>匹配度</span>
            <span>{scorePercent(data.match_score)}%</span>
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
      <div className={`overflow-hidden transition-all duration-300 ${expanded ? 'max-h-[32rem]' : 'max-h-0'}`}>
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
          <DetailList title="风险点" items={data.risk_points} />
          <DetailList title="替代方案" items={data.alternatives} />
        </div>
      </div>

      {/* Expand Toggle */}
      <button
        type="button"
        className="w-full px-5 py-2 border-t border-rule flex items-center justify-center gap-1 text-xs font-mono text-ink-light hover:text-ink transition-colors"
        onClick={onToggle}
      >
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
      </button>
    </article>
  )
}

// ── Major Card ──────────────────────────────────────────────

interface MajorCardProps {
  data: MajorRecommendation
  expanded: boolean
  isFavorite?: boolean
  onFavoriteToggle?: () => void
  onToggle: () => void
}

function MajorCard({ data, expanded, isFavorite, onFavoriteToggle, onToggle }: MajorCardProps) {
  const empPercent = Math.round(data.employment_rate * 100)
  const strategy = strategyLabel(data.strategy)

  return (
    <article
      className="border-2 border-ink bg-paper transition-all duration-300 hover:shadow-warm-lg"
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
          <div className="flex flex-shrink-0 items-center gap-2">
            {onFavoriteToggle && (
              <button
                type="button"
                aria-pressed={isFavorite}
                aria-label={`${isFavorite ? '取消收藏' : '收藏'} ${data.major_name}`}
                className={`border px-2 py-1 text-xs font-serif font-bold transition-colors ${
                  isFavorite
                    ? 'border-ink bg-ink text-gold'
                    : 'border-ink/30 bg-paper text-ink-light hover:border-ink hover:text-ink'
                }`}
                onClick={onFavoriteToggle}
              >
                {isFavorite ? '已收藏' : '收藏'}
              </button>
            )}
            <span className="stamp text-xs bg-ink text-gold">
              {strategy} · {data.category}
            </span>
          </div>
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
      <div className={`overflow-hidden transition-all duration-300 ${expanded ? 'max-h-[32rem]' : 'max-h-0'}`}>
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
          <DetailList title="风险点" items={data.risk_points} />
          <DetailList title="替代方案" items={data.alternatives} />
        </div>
      </div>

      {/* Expand Toggle */}
      <button
        type="button"
        className="w-full px-5 py-2 border-t border-rule flex items-center justify-center gap-1 text-xs font-mono text-ink-light hover:text-ink transition-colors"
        onClick={onToggle}
      >
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
      </button>
    </article>
  )
}
