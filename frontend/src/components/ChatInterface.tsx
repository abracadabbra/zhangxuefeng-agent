import { useState, useRef, useEffect, useCallback, type CSSProperties, type ReactElement } from 'react'
import { useTranslation } from 'react-i18next'
import { List, useListCallbackRef, useDynamicRowHeight, type DynamicRowHeight } from 'react-window'
import MessageBubble from './MessageBubble'
import SourcePanel from './SourcePanel'
import { MessageSkeleton } from './Skeleton'
import RecommendationCard, {
  type MajorRecommendation,
  type SchoolRecommendation,
} from './RecommendationCard'
import { fetchUserProfile, profileSummary, userProfileToChatContext } from '../api/profile'
import { API_BASE } from '../config'
import type { Message, ToolCall, UserProfile } from '../types'

interface ChatInterfaceProps {
  sessionId: string
  userProfile?: UserProfile | null
  scenario?: 'gaokao' | 'kaoyan' | 'career'
}

type RecommendationItem = SchoolRecommendation | MajorRecommendation
type Strategy = '冲' | '稳' | '保'

interface RecommendResponse {
  recommendations?: RecommendationItem[]
  summary?: string
  gradient_summary?: Partial<Record<Strategy, string[]>>
}

interface RecommendationFavoritesResponse {
  favorite_keys?: string[]
}

interface ProfileProgressField {
  key: keyof UserProfile
  label: string
  required: boolean
}

const PROFILE_PROGRESS_FIELDS: ProfileProgressField[] = [
  { key: 'score', label: '分数', required: true },
  { key: 'province', label: '省份', required: true },
  { key: 'subject', label: '科类/选科', required: true },
  { key: 'familyCondition', label: '家庭条件', required: true },
  { key: 'targetCity', label: '目标城市', required: false },
  { key: 'riskTolerance', label: '风险偏好', required: false },
  { key: 'careerGoal', label: '职业方向', required: false },
  { key: 'admissionBatch', label: '省份批次', required: false },
  { key: 'subjectRequirements', label: '选科限制', required: false },
  { key: 'rank', label: '位次', required: false },
  { key: 'budget', label: '家庭预算', required: false },
  { key: 'regionPreference', label: '地域偏好', required: false },
  { key: 'cityTier', label: '城市层级', required: false },
  { key: 'careerPreferenceWeight', label: '职业偏好权重', required: false },
]

/** Row component for virtual list — self-measures height via observeRowElements */
function ChatRow({ index, style, messages, dynamicRowHeight, t }: {
  index: number
  style: CSSProperties
  messages: Message[]
  isLoading: boolean
  dynamicRowHeight: DynamicRowHeight
  t: (key: string, opts?: Record<string, unknown>) => string
}): ReactElement {
  const rowRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    const el = rowRef.current
    if (!el) return
    return dynamicRowHeight.observeRowElements([el])
  }, [dynamicRowHeight])

  // Loading indicator row (appended as the last row when loading)
  if (index === messages.length) {
    return (
      <div ref={rowRef} style={style}>
        <div className="px-3 sm:px-6 py-4">
          <div role="status" aria-label={t('chat.analyzing')} className="flex items-center gap-3">
            <div className="w-8 h-8 bg-ink flex items-center justify-center flex-shrink-0">
              <span className="text-gold font-bold text-sm font-serif">张</span>
            </div>
            <div className="flex items-center gap-2 text-ink-light">
              <div className="flex space-x-1" aria-hidden="true">
                <div className="w-2 h-2 bg-ink-light rounded-full animate-bounce" />
                <div className="w-2 h-2 bg-ink-light rounded-full animate-bounce [animation-delay:0.2s]" />
                <div className="w-2 h-2 bg-ink-light rounded-full animate-bounce [animation-delay:0.4s]" />
              </div>
              <span className="text-sm font-serif">{t('chat.analyzing')}</span>
            </div>
          </div>
        </div>
      </div>
    )
  }

  return (
    <div ref={rowRef} style={style}>
      <div className="px-3 sm:px-6 pt-3 pb-1">
        <MessageBubble message={messages[index]} />
      </div>
    </div>
  )
}

function recommendationName(item: RecommendationItem): string {
  return 'school_name' in item ? item.school_name : item.major_name
}

function recommendationKey(item: RecommendationItem): string {
  return 'school_name' in item ? `school:${item.school_name}` : `major:${item.major_name}`
}

function favoriteStorageKey(sessionId: string): string {
  return `recommendation-favorites:${sessionId}`
}

function parseFavoriteKeys(value: unknown): string[] {
  if (!Array.isArray(value)) return []
  return value.filter((item): item is string => typeof item === 'string')
}

function readFavoriteKeysFromStorage(sessionId: string): string[] {
  try {
    const raw = window.localStorage.getItem(favoriteStorageKey(sessionId))
    return parseFavoriteKeys(raw ? JSON.parse(raw) : [])
  } catch {
    return []
  }
}

function writeFavoriteKeysToStorage(sessionId: string, favoriteKeys: string[]) {
  try {
    window.localStorage.setItem(favoriteStorageKey(sessionId), JSON.stringify(favoriteKeys))
  } catch {
    // 收藏只是本地体验增强，存储不可用时不影响推荐主流程。
  }
}

async function saveFavoriteKeysToServer(sessionId: string, favoriteKeys: string[]) {
  const response = await fetch(`${API_BASE}/api/session/${sessionId}/favorites`, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ favorite_keys: favoriteKeys }),
  })
  if (!response.ok) throw new Error('Favorite sync failed')
}

function recommendationStrategy(item: RecommendationItem): Strategy {
  if (item.strategy === '冲' || item.strategy === '稳' || item.strategy === '保') return item.strategy
  if ('admission_probability' in item) {
    if (item.admission_probability >= 0.8) return '保'
    if (item.admission_probability >= 0.55) return '稳'
  }
  return '冲'
}

function metricLabel(item: RecommendationItem): string {
  if ('admission_probability' in item) {
    return `录取 ${Math.round(item.admission_probability * 100)}%`
  }
  return `就业 ${Math.round(item.employment_rate * 100)}%`
}

function hasProfileValue(value: unknown): boolean {
  return value !== undefined && value !== null && value !== ''
}

function profileProgress(profile: UserProfile | null | undefined) {
  const requiredFields = PROFILE_PROGRESS_FIELDS.filter(field => field.required)
  const completedRequired = requiredFields.filter(field => hasProfileValue(profile?.[field.key]))
  const missingRequired = requiredFields.filter(field => !hasProfileValue(profile?.[field.key]))
  const optionalHints = PROFILE_PROGRESS_FIELDS.filter(
    field => !field.required && !hasProfileValue(profile?.[field.key]),
  )
  const percent = Math.round((completedRequired.length / requiredFields.length) * 100)

  return {
    percent,
    completed: completedRequired.length,
    total: requiredFields.length,
    missingRequired,
    optionalHints,
  }
}

function ProfileProgress({ profile }: { profile: UserProfile | null | undefined }) {
  const progress = profileProgress(profile)
  const missingLabels = progress.missingRequired.map(field => field.label)
  const optionalLabels = progress.optionalHints.slice(0, 2).map(field => field.label)

  return (
    <section
      aria-label="追问进度"
      className="mb-3 border border-ink/30 bg-paper px-3 py-2"
    >
      <div className="flex items-center justify-between gap-3">
        <div>
          <div className="text-xs font-mono text-ink-light">追问进度</div>
          <div className="mt-1 text-sm font-serif font-bold text-ink">
            必要信息 {progress.completed}/{progress.total}
          </div>
        </div>
        <div className="text-lg font-mono font-bold text-ink">{progress.percent}%</div>
      </div>
      <div className="mt-2 h-2 border border-rule bg-paper-dark">
        <div
          className="h-full bg-gold transition-all duration-300"
          style={{ width: `${progress.percent}%` }}
        />
      </div>
      {missingLabels.length > 0 ? (
        <p className="mt-2 text-xs font-serif text-ink-light">
          还差：{missingLabels.join('、')}
        </p>
      ) : (
        <p className="mt-2 text-xs font-serif text-ink-light">
          必要信息已齐，可以生成更完整的推荐。
          {optionalLabels.length > 0 ? ` 可补充：${optionalLabels.join('、')}` : ''}
        </p>
      )}
    </section>
  )
}

function RecommendationOverview({
  recommendations,
  summary,
  gradientSummary,
  favoriteKeys,
  onFavoriteToggle,
}: {
  recommendations: RecommendationItem[]
  summary: string
  gradientSummary: Partial<Record<Strategy, string[]>>
  favoriteKeys: string[]
  onFavoriteToggle: (item: RecommendationItem) => void
}) {
  if (recommendations.length === 0 && !summary) return null

  const favoriteSet = new Set(favoriteKeys)
  const favoriteCount = recommendations.filter(item => favoriteSet.has(recommendationKey(item))).length
  const groups = (['冲', '稳', '保'] as const).map(strategy => ({
    strategy,
    items: recommendations.filter(item => recommendationStrategy(item) === strategy),
    names: gradientSummary[strategy] || [],
  }))

  return (
    <section aria-label="志愿推荐结果" className="border-b-2 border-ink bg-paper-dark/30 px-3 sm:px-6 py-4 space-y-4">
      <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
        <div>
          <span className="stamp text-xs">志愿推荐</span>
          {summary && <p className="mt-2 text-sm font-serif text-ink leading-relaxed">{summary}</p>}
          {recommendations.length > 0 && (
            <p className="mt-2 text-xs font-mono text-ink-light">
              已收藏 {favoriteCount} / {recommendations.length} 项
            </p>
          )}
        </div>
        <div className="grid grid-cols-3 gap-2 sm:min-w-[220px]">
          {groups.map(group => (
            <div key={group.strategy} className="border border-ink/30 bg-paper px-2 py-2 text-center">
              <div className="text-lg font-mono font-bold text-ink">{group.items.length || group.names.length}</div>
              <div className="text-xs font-serif text-ink-light">{group.strategy}</div>
              {group.names.length > 0 && (
                <div className="mt-1 truncate text-[11px] font-serif text-ink-light" title={group.names.join('、')}>
                  {group.names.join('、')}
                </div>
              )}
            </div>
          ))}
        </div>
      </div>

      {recommendations.length > 0 && (
        <div className="overflow-x-auto border border-ink/30 bg-paper">
          <table className="min-w-full text-left text-sm">
            <thead className="font-mono text-xs text-ink-light border-b border-rule">
              <tr>
                <th className="px-3 py-2 font-normal">梯度</th>
                <th className="px-3 py-2 font-normal">推荐项</th>
                <th className="px-3 py-2 font-normal">关键指标</th>
              </tr>
            </thead>
            <tbody className="font-serif text-ink">
              {recommendations.slice(0, 6).map(item => (
                <tr key={recommendationName(item)} className="border-b border-rule last:border-0">
                  <td className="px-3 py-2 font-bold">{recommendationStrategy(item)}</td>
                  <td className="px-3 py-2">{recommendationName(item)}</td>
                  <td className="px-3 py-2">{metricLabel(item)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {recommendations.length > 0 && (
        <div className="grid gap-3 md:grid-cols-2">
          {recommendations.map(item => {
            const key = recommendationKey(item)
            const favoriteProps = {
              isFavorite: favoriteSet.has(key),
              onFavoriteToggle: () => onFavoriteToggle(item),
            }

            return 'school_name' in item
              ? <RecommendationCard key={key} type="school" data={item} {...favoriteProps} />
              : <RecommendationCard key={key} type="major" data={item} {...favoriteProps} />
          })}
        </div>
      )}
    </section>
  )
}

export default function ChatInterface({ sessionId, userProfile, scenario }: ChatInterfaceProps) {
  const { t } = useTranslation()
  const [messages, setMessages] = useState<Message[]>([])
  const [input, setInput] = useState('')
  const [isLoading, setIsLoading] = useState(false)
  const [profileSent, setProfileSent] = useState(false)
  const [resolvedProfile, setResolvedProfile] = useState<UserProfile | null>(userProfile || null)
  const [lastSources, setLastSources] = useState<ToolCall[]>([])
  const [showSources, setShowSources] = useState(false)
  const [isRecommending, setIsRecommending] = useState(false)
  const [recommendations, setRecommendations] = useState<RecommendationItem[]>([])
  const [recommendSummary, setRecommendSummary] = useState('')
  const [gradientSummary, setGradientSummary] = useState<Partial<Record<Strategy, string[]>>>({})
  const [favoriteKeys, setFavoriteKeys] = useState<string[]>([])
  const [favoritesLoaded, setFavoritesLoaded] = useState(false)
  const inputRef = useRef<HTMLTextAreaElement>(null)
  const [listApi, setListApi] = useListCallbackRef()
  const dynamicRowHeight = useDynamicRowHeight({ defaultRowHeight: 120, key: 'chat-messages' })

  // Total rows = messages + optional loading indicator
  const rowCount = messages.length + (isLoading ? 1 : 0)

  const scrollToBottom = useCallback(() => {
    if (rowCount > 0 && listApi) {
      listApi.scrollToRow({ index: rowCount - 1, align: 'end', behavior: 'smooth' })
    }
  }, [rowCount, listApi])

  useEffect(() => {
    scrollToBottom()
  }, [messages, isLoading, scrollToBottom])

  useEffect(() => {
    if (!isLoading) {
      inputRef.current?.focus()
    }
  }, [isLoading])

  useEffect(() => {
    setResolvedProfile(userProfile || null)
  }, [userProfile])

  useEffect(() => {
    let cancelled = false
    setFavoritesLoaded(false)
    setFavoriteKeys(readFavoriteKeysFromStorage(sessionId))

    fetch(`${API_BASE}/api/session/${sessionId}/favorites`)
      .then(r => {
        if (!r.ok) return null
        return r.json()
      })
      .then((data: RecommendationFavoritesResponse | null) => {
        if (cancelled || !data) return
        setFavoriteKeys(parseFavoriteKeys(data.favorite_keys))
      })
      .catch(() => {
        // 后端收藏不可用时继续使用本地缓存。
      })
      .finally(() => {
        if (!cancelled) setFavoritesLoaded(true)
      })

    return () => {
      cancelled = true
    }
  }, [sessionId])

  useEffect(() => {
    if (!favoritesLoaded) return
    writeFavoriteKeysToStorage(sessionId, favoriteKeys)
  }, [favoriteKeys, favoritesLoaded, sessionId])

  // 加载历史消息
  useEffect(() => {
    fetch(`${API_BASE}/api/session/${sessionId}`)
      .then(r => {
        if (!r.ok) return null
        return r.json()
      })
      .then(data => {
        if (data?.messages?.length > 0) {
          const history: Message[] = data.messages
            .filter((m: { role: string }) => m.role === 'user' || m.role === 'assistant')
            .map((m: { role: string; content: string }) => ({
              id: crypto.randomUUID(),
              role: m.role as 'user' | 'assistant',
              content: m.content || '',
              timestamp: new Date(),
            }))
          if (history.length > 0) {
            setMessages(history)
          }
        }
      })
      .catch(() => {})
  }, [sessionId])

  // 加载用户画像（恢复会话时也需要）
  useEffect(() => {
    if (userProfile) return // 已有表单传来的画像，不需要再获取
    fetchUserProfile(sessionId)
      .then(profile => {
        if (profile) {
          setResolvedProfile(profile)
          const ctx = userProfileToChatContext(profile)
          if (ctx) {
            setMessages(prev => {
              if (prev.length > 0) return prev
              return [...prev, {
                id: crypto.randomUUID(),
                role: 'assistant',
                content: `我记住你的信息了：${profileSummary(profile)}。有什么需要咨询的？`,
                timestamp: new Date(),
              }]
            })
          }
        }
      })
      .catch(() => {})
  }, [sessionId, userProfile])

  // 进入聊天时：自动发送 profile 信息（优先用 props，其次从 API 获取）
  useEffect(() => {
    if (profileSent || messages.length > 0) return

    const sendInitMessage = (profile: UserProfile | null) => {
      const ctx = userProfileToChatContext(profile)

      if (!ctx) {
        return
      }

      const scenarioLabel = scenario === 'kaoyan' ? '考研' : scenario === 'career' ? '职业规划' : '高考志愿填报'
      const initMessage = `我(${profileSummary(profile!)})来咨询${scenarioLabel}。请直接根据这些信息回答我的问题。`

      const userMessage: Message = {
        id: crypto.randomUUID(),
        role: 'user',
        content: initMessage,
        timestamp: new Date(),
      }
      setMessages([userMessage])
      setIsLoading(true)
      setProfileSent(true)

      fetch(`${API_BASE}/api/chat`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          session_id: sessionId,
          message: initMessage,
          user_context: ctx,
          stream: false,
        }),
      })
        .then(r => r.json())
        .then(data => {
          setIsLoading(false)
          if (data.reply) {
            setMessages(prev => [...prev, {
              id: crypto.randomUUID(),
              role: 'assistant',
              content: data.reply,
              timestamp: new Date(),
            }])
          }
        })
        .catch(() => {
          setIsLoading(false)
        })
    }

    if (userProfile) {
      sendInitMessage(userProfile)
    } else {
      fetchUserProfile(sessionId).then(profile => {
        if (profile) {
          setResolvedProfile(profile)
        }
        sendInitMessage(profile)
      })
        .catch(() => {})
    }
  }, [userProfile, profileSent, messages.length, sessionId, scenario])

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!input.trim() || isLoading) return

    const userMessage: Message = {
      id: crypto.randomUUID(),
      role: 'user',
      content: input.trim(),
      timestamp: new Date(),
    }

    setMessages(prev => [...prev, userMessage])
    setInput('')
    setIsLoading(true)

    try {
      const body: Record<string, unknown> = {
        session_id: sessionId,
        message: userMessage.content,
        stream: true,
      }
      if (userProfile && !profileSent) {
        body.user_context = userProfileToChatContext(userProfile)
        setProfileSent(true)
      }

      const response = await fetch(`${API_BASE}/api/chat`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body),
      })

      if (!response.ok) throw new Error('Request failed')

      const contentType = response.headers.get('content-type') || ''

      if (contentType.includes('text/event-stream')) {
        const reader = response.body?.getReader()
        if (!reader) throw new Error('Cannot read response stream')

        const decoder = new TextDecoder()
        const assistantMessage: Message = {
          id: crypto.randomUUID(),
          role: 'assistant',
          content: '',
          timestamp: new Date(),
          toolCalls: [],
        }

        setMessages(prev => [...prev, assistantMessage])

        while (true) {
          const { done, value } = await reader.read()
          if (done) break

          const chunk = decoder.decode(value)
          const lines = chunk.split('\n')

          for (const line of lines) {
            if (line.startsWith('data: ')) {
              try {
                const data = JSON.parse(line.slice(6))

                if (data.type === 'text') {
                  assistantMessage.content += data.content
                  setMessages(prev => {
                    const updated = [...prev]
                    const lastMsg = updated[updated.length - 1]
                    if (lastMsg.role === 'assistant') {
                      lastMsg.content = assistantMessage.content
                    }
                    return updated
                  })
                } else if (data.type === 'tool_call') {
                  const toolCall: ToolCall = {
                    id: crypto.randomUUID(),
                    name: data.name,
                    arguments: data.arguments,
                  }
                  assistantMessage.toolCalls?.push(toolCall)
                  setLastSources(prev => [...prev, toolCall])
                  setMessages(prev => {
                    const updated = [...prev]
                    const lastMsg = updated[updated.length - 1]
                    if (lastMsg.role === 'assistant' && lastMsg.toolCalls) {
                      lastMsg.toolCalls = [...assistantMessage.toolCalls!]
                    }
                    return updated
                  })
                } else if (data.type === 'tool_result') {
                  if (assistantMessage.toolCalls) {
                    const idx = assistantMessage.toolCalls.findIndex(
                      tc => tc.name === data.name && !tc.result
                    )
                    if (idx !== -1) {
                      assistantMessage.toolCalls[idx] = {
                        ...assistantMessage.toolCalls[idx],
                        result: data.result,
                      }
                    }
                  }
                  setLastSources(prev => prev.map(tc =>
                    tc.name === data.name && !tc.result
                      ? { ...tc, result: data.result }
                      : tc
                  ))
                  setMessages(prev => {
                    const updated = [...prev]
                    const lastMsg = updated[updated.length - 1]
                    if (lastMsg.role === 'assistant' && lastMsg.toolCalls) {
                      lastMsg.toolCalls = [...assistantMessage.toolCalls!]
                    }
                    return updated
                  })
                }
              } catch {
                // 忽略解析错误
              }
            }
          }
        }
      } else {
        const data = await response.json()
        const toolCalls: ToolCall[] = data.tool_calls?.map((tc: { id?: string; name: string; arguments: Record<string, unknown>; result?: string }) => ({
          id: tc.id || crypto.randomUUID(),
          name: tc.name,
          arguments: tc.arguments,
          result: tc.result,
        })) || []

        const assistantMessage: Message = {
          id: crypto.randomUUID(),
          role: 'assistant',
          content: data.reply || '',
          timestamp: new Date(),
          toolCalls,
        }

        if (toolCalls.length > 0) {
          setLastSources(prev => [...prev, ...toolCalls])
        }

        setMessages(prev => [...prev, assistantMessage])
      }
    } catch (error) {
      console.error('Chat error:', error)
      setMessages(prev => [
        ...prev,
        {
          id: crypto.randomUUID(),
          role: 'assistant',
          content: t('chat.errorMessage'),
          timestamp: new Date(),
        },
      ])
    } finally {
      setIsLoading(false)
    }
  }

  const handleRecommend = async () => {
    if (isLoading || isRecommending) return
    setIsRecommending(true)

    try {
      const profile = userProfile || await fetchUserProfile(sessionId)
      const response = await fetch(`${API_BASE}/api/recommend`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          session_id: sessionId,
          message: '请根据我的画像生成高考志愿推荐，按冲稳保给出学校或专业建议。',
          user_context: userProfileToChatContext(profile),
        }),
      })

      if (!response.ok) throw new Error('Recommend failed')
      const data = await response.json() as RecommendResponse
      setRecommendations(data.recommendations || [])
      setRecommendSummary(data.summary || '')
      setGradientSummary(data.gradient_summary || {})
    } catch (error) {
      console.error('Recommend error:', error)
      setMessages(prev => [
        ...prev,
        {
          id: crypto.randomUUID(),
          role: 'assistant',
          content: '推荐生成失败，请稍后再试。',
          timestamp: new Date(),
        },
      ])
    } finally {
      setIsRecommending(false)
    }
  }

  const handleFavoriteToggle = useCallback((item: RecommendationItem) => {
    const key = recommendationKey(item)
    setFavoriteKeys(prev => {
      const next = prev.includes(key)
        ? prev.filter(itemKey => itemKey !== key)
        : [...prev, key]

      void saveFavoriteKeysToServer(sessionId, next).catch(() => {
        // 收藏已写入 localStorage；后端同步失败不阻断用户操作。
      })
      return next
    })
  }, [sessionId])

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleSubmit(e as unknown as React.FormEvent)
    }
  }

  return (
    <div role="region" aria-label={t('a11y.chatRegion', { defaultValue: '聊天区域' })} className="flex flex-col lg:flex-row h-[calc(100vh-140px)] sm:h-[calc(100vh-100px)] gap-0 lg:gap-6">
      {/* 聊天区域 */}
      <div className="flex-1 flex flex-col border-2 border-ink bg-paper min-h-0">
        {/* 消息头部 */}
        <div className="border-b-2 border-ink px-4 sm:px-6 py-3 bg-paper-dark/50/50 flex-shrink-0">
          <div className="flex items-center justify-between">
            <h2 className="font-serif font-bold text-ink text-base sm:text-lg">{t('chat.title')}</h2>
            <div className="flex items-center gap-2 sm:gap-3">
              {messages.length > 0 && (
                <div className="flex items-center gap-1">
                  <button
                    onClick={() => window.open(`${API_BASE}/api/session/${sessionId}/export`, '_blank')}
                    aria-label={t('chat.exportMarkdown')}
                    className="text-xs font-mono text-ink-light hover:text-ink
                               border border-ink/30 hover:border-ink
                               px-2 py-1 transition-colors"
                  >
                    Markdown
                  </button>
                  <button
                    onClick={() => window.open(`${API_BASE}/api/session/${sessionId}/export/pdf`, '_blank')}
                    aria-label={t('chat.exportPdf')}
                    className="text-xs font-mono text-ink-light hover:text-ink
                               border border-ink/30 hover:border-ink
                               px-2 py-1 transition-colors"
                  >
                    PDF
                  </button>
                </div>
              )}
              {/* 移动端数据来源切换 */}
              {lastSources.length > 0 && (
                <button
                  onClick={() => setShowSources(prev => !prev)}
                  aria-label={t('sourcePanel.title') + ` (${lastSources.length})`}
                  aria-expanded={showSources}
                  className="lg:hidden text-xs font-mono text-ink-light hover:text-ink
                             border border-ink/30 px-2 py-1 transition-colors"
                >
                  {t('sourcePanel.title')} ({lastSources.length})
                </button>
              )}
              <span className="text-xs font-mono text-ink-light hidden sm:inline">{t('chat.liveConsult')}</span>
            </div>
          </div>
        </div>

        <RecommendationOverview
          recommendations={recommendations}
          summary={recommendSummary}
          gradientSummary={gradientSummary}
          favoriteKeys={favoriteKeys}
          onFavoriteToggle={handleFavoriteToggle}
        />

        {/* Messages */}
        <div role="log" aria-label={t('a11y.messageLog', { defaultValue: '消息记录' })} aria-live="polite" aria-relevant="additions" className="flex-1 min-h-0 overscroll-contain">
          {messages.length === 0 && !isLoading && (
            <div className="text-center py-10 sm:py-16 px-3 sm:px-6">
              <div className="quote-mark mb-4">"</div>
              <p className="text-lg sm:text-xl font-serif text-ink mb-2">
                {t('chat.welcomeTitle')}
              </p>
              <p className="text-sm text-ink-light font-serif">
                {t('chat.welcomeDesc')}
              </p>
              <div className="rule-single mt-8 max-w-xs mx-auto" />
            </div>
          )}

          {isLoading && messages.length === 0 && (
            <div className="p-3 sm:p-6 space-y-4 sm:space-y-6">
              <MessageSkeleton />
              <MessageSkeleton isUser />
              <MessageSkeleton />
            </div>
          )}

          {messages.length > 0 && (
            <List
              listRef={setListApi}
              rowCount={rowCount}
              rowHeight={dynamicRowHeight}
              rowComponent={ChatRow}
              // eslint-disable-next-line @typescript-eslint/no-explicit-any
              rowProps={{ messages, isLoading, dynamicRowHeight, t } as any}
              overscanCount={5}
              className="scrollbar-thin"
              style={{ height: '100%', width: '100%' }}
            />
          )}
        </div>

        {/* Input Area - 读者来信投稿区 */}
        <form onSubmit={handleSubmit} aria-label={t('a11y.chatForm', { defaultValue: '发送消息' })} className="border-t-2 border-ink p-3 sm:p-4 bg-paper-dark/30/30 flex-shrink-0">
          <ProfileProgress profile={resolvedProfile} />
          <div className="mb-3 flex flex-wrap items-center gap-2">
            <button
              type="button"
              onClick={handleRecommend}
              disabled={isLoading || isRecommending}
              className="border border-ink/40 bg-paper px-3 py-1.5 text-xs font-serif font-bold text-ink
                         hover:border-ink disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
            >
              {isRecommending ? '推荐生成中' : '生成志愿推荐'}
            </button>
          </div>
          <div className="flex items-end gap-2 sm:gap-3">
            <div className="flex-1 min-w-0">
              <label htmlFor="chat-input" className="text-xs text-ink-light font-mono mb-1 sm:mb-2">{t('chat.readerLetter')}</label>
              <textarea
                id="chat-input"
                ref={inputRef}
                value={input}
                onChange={e => setInput(e.target.value)}
                onKeyDown={handleKeyDown}
                placeholder={t('chat.inputPlaceholder')}
                aria-label={t('chat.inputPlaceholder')}
                aria-busy={isLoading}
                className="w-full resize-none border-2 border-ink bg-paper
                           px-3 sm:px-4 py-2 sm:py-3 font-serif text-ink
                           placeholder:text-ink-light/50
                           focus:outline-none focus:border-gold transition-colors"
                rows={2}
                disabled={isLoading}
              />
            </div>
            <button
              type="submit"
              disabled={!input.trim() || isLoading}
              aria-label={t('chat.send')}
              className="px-4 sm:px-6 py-2 sm:py-3 bg-ink text-paper
                         font-serif font-bold hover:bg-ink-light
                         disabled:opacity-50 disabled:cursor-not-allowed transition-colors self-end
                         text-sm sm:text-base flex-shrink-0"
            >
              {t('chat.send')}
            </button>
          </div>
        </form>
      </div>

      {/* 数据来源面板 - 桌面端固定显示，移动端可切换 */}
      <div className={`
        ${showSources ? 'block' : 'hidden'} lg:block
        lg:w-[320px] xl:w-[380px] flex-shrink-0
        fixed lg:static inset-0 z-40 lg:z-auto
        bg-paper lg:bg-transparent
      `}>
        {/* 移动端遮罩 */}
        {showSources && (
          <div
            className="lg:hidden absolute inset-0 bg-black/30"
            onClick={() => setShowSources(false)}
            onKeyDown={(e) => { if (e.key === 'Escape') setShowSources(false) }}
            role="button"
            aria-label={t('a11y.closePanel', { defaultValue: '关闭面板' })}
            tabIndex={0}
          />
        )}
        <div className={`
          ${showSources ? 'absolute right-0 top-0 bottom-0 w-[85vw] max-w-[380px]' : ''}
          lg:relative lg:w-full
        `}>
          <SourcePanel sources={lastSources} onClose={() => setShowSources(false)} />
        </div>
      </div>
    </div>
  )
}
