import { useState, useEffect } from 'react'
import ChatInterface from './components/ChatInterface'
import SoulQuestionForm from './components/SoulQuestionForm'
import type { UserProfile } from './types'

type View = 'portal' | 'form' | 'chat'
type Scenario = 'gaokao' | 'kaoyan' | 'career'

interface SessionSummary {
  session_id: string
  created_at: string
  message_count: number
}

const SCENARIOS = [
  {
    id: 'gaokao' as Scenario,
    title: '高考志愿填报',
    subtitle: '分数出来别慌，我帮你算明白',
    icon: '🎓',
    section: 'A 版',
    description: '3700+ 院校、580+ 专业、85000+ 分数线',
  },
  {
    id: 'kaoyan' as Scenario,
    title: '考研规划',
    subtitle: '选对学校和专业，比努力更重要',
    icon: '📚',
    section: 'B 版',
    description: '院校报录比、复试线、调剂信息全覆盖',
  },
  {
    id: 'career' as Scenario,
    title: '职业规划',
    subtitle: '选专业之前，先看看就业真相',
    icon: '💼',
    section: 'C 版',
    description: '专业就业率、薪资水平、行业趋势分析',
  },
]

function App() {
  const [view, setView] = useState<View>('portal')
  const [scenario, setScenario] = useState<Scenario>('gaokao')
  const [sessionId, setSessionId] = useState(() => crypto.randomUUID())

  const handleScenarioSelect = (s: Scenario) => {
    setSessionId(crypto.randomUUID())
    setScenario(s)
    setView('form')
  }

  const [userProfile, setUserProfile] = useState<UserProfile | null>(null)

  const handleFormComplete = (profile: UserProfile) => {
    setUserProfile(profile)
    // 将 profile 保存到后端 Redis
    const fields: Record<string, string> = {}
    if (profile.score != null) fields['score'] = String(profile.score)
    if (profile.province) fields['province'] = profile.province
    if (profile.subject) fields['subject'] = profile.subject
    if (profile.familyCondition) fields['family_background'] = profile.familyCondition
    if (profile.budget) fields['target_city'] = profile.budget

    Promise.all(
      Object.entries(fields).map(([field, value]) =>
        fetch(`/api/profile/${sessionId}`, {
          method: 'PUT',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ field, value }),
        })
      )
    ).catch(() => {})

    setView('chat')
  }

  const handleResumeSession = (sid: string) => {
    setSessionId(sid)
    setView('chat')
  }

  const handleBackToPortal = () => {
    setView('portal')
  }

  return (
    <div className="min-h-screen flex flex-col bg-paper paper-texture">
      {/* Header - 报头风格 */}
      <header className="bg-paper-dark/80 backdrop-blur-md border-b-2 border-ink sticky top-0 z-50">
        <div className="max-w-6xl mx-auto px-4 py-3">
          <div className="flex items-center justify-between">
            <button
              onClick={handleBackToPortal}
              className="flex items-center gap-3 group"
            >
              <div className="w-12 h-12 bg-ink flex items-center justify-center">
                <span className="text-gold font-bold text-xl font-serif">张</span>
              </div>
              <div className="text-left">
                <h1 className="text-xl font-bold text-ink font-serif leading-tight tracking-wide">
                  张雪峰 AI 咨询
                </h1>
                <p className="text-xs text-ink-light font-mono tracking-widest uppercase">
                  Data-Driven Truth
                </p>
              </div>
            </button>

            {view !== 'portal' && (
              <button
                onClick={handleBackToPortal}
                className="px-4 py-2 text-sm font-serif text-ink border border-ink hover:bg-ink hover:text-paper transition-colors"
              >
                ← 返回首页
              </button>
            )}
          </div>
        </div>
      </header>

      {/* Main Content */}
      <main className="flex-1">
        {view === 'portal' && (
          <PortalHome onSelect={handleScenarioSelect} onResume={handleResumeSession} />
        )}
        {view === 'form' && (
          <SoulQuestionForm
            scenario={scenario}
            onComplete={handleFormComplete}
            onBack={handleBackToPortal}
          />
        )}
        {view === 'chat' && (
          <div className="max-w-7xl mx-auto p-4 h-[calc(100vh-80px)]">
            <ChatInterface sessionId={sessionId} userProfile={userProfile} />
          </div>
        )}
      </main>

      {/* Footer - 报纸页脚 */}
      {view === 'portal' && (
        <footer className="border-t-2 border-ink bg-paper-dark/50 py-4">
          <div className="max-w-6xl mx-auto px-4 flex flex-wrap justify-between items-center text-xs text-ink-light font-mono">
            <span>第 2026 期 · 高考特刊</span>
            <span>数据驱动 · 说真话 · 不画饼</span>
            <span>© 张雪峰 AI 咨询</span>
          </div>
        </footer>
      )}
    </div>
  )
}

/* ── Portal Homepage - 报纸头版风格 ────────────────────────── */
function PortalHome({ onSelect, onResume }: { onSelect: (s: Scenario) => void; onResume: (sid: string) => void }) {
  const [sessions, setSessions] = useState<SessionSummary[]>([])

  useEffect(() => {
    fetch('/api/sessions?limit=10')
      .then(r => r.json())
      .then(data => setSessions(data))
      .catch(() => {})
  }, [])
  const today = new Date()
  const dateStr = `${today.getFullYear()} 年 ${today.getMonth() + 1} 月 ${today.getDate()} 日`

  return (
    <div className="max-w-5xl mx-auto px-4 py-8 sm:py-12">
      {/* Masthead 报头区域 */}
      <div className="text-center mb-10">
        {/* 顶部装饰线 */}
        <div className="rule-thick mb-4" />
        <div className="rule-double mb-6" />

        {/* 日期和卷号 */}
        <div className="flex justify-between items-center text-xs font-mono text-ink-light mb-4 px-4">
          <span>{dateStr}</span>
          <span>第 2026 期 · 高考特刊</span>
          <span>全国版</span>
        </div>

        {/* 主标题 */}
        <h2 className="text-4xl sm:text-6xl font-black text-ink font-serif leading-tight mb-3 tracking-wide">
          选学校、选专业、选城市
        </h2>
        <div className="flex items-center justify-center gap-4 mb-4">
          <div className="h-px flex-1 bg-ink" />
          <span className="text-lg sm:text-2xl font-bold text-gold font-serif">
            先看数据，再做决定
          </span>
          <div className="h-px flex-1 bg-ink" />
        </div>

        {/* 副标题 */}
        <p className="text-base sm:text-lg text-ink-light max-w-2xl mx-auto leading-relaxed font-serif">
          不画饼、不灌鸡汤、不和稀泥。
          <br className="hidden sm:block" />
          我是张雪峰 AI 咨询，用数据帮你做最务实的选择。
        </p>

        <div className="rule-double mt-6" />
        <div className="rule-single mt-1" />
      </div>

      {/* 三个场景卡片 - 报纸分类广告风格 */}
      <div className="grid gap-6 sm:grid-cols-3 mb-10">
        {SCENARIOS.map((s) => (
          <button
            key={s.id}
            onClick={() => onSelect(s.id)}
            className="group relative bg-paper border-2 border-ink p-6 text-left transition-all duration-300 hover:shadow-warm-xl hover:-translate-y-1 focus-visible:ring-2 focus-visible:ring-gold focus-visible:ring-offset-2 outline-none"
          >
            {/* 版面标识 */}
            <div className="absolute top-0 left-0 bg-ink text-paper px-3 py-1 text-xs font-mono font-bold">
              {s.section}
            </div>

            {/* Icon */}
            <div className="text-4xl mb-4 mt-4">
              {s.icon}
            </div>

            {/* 标题 */}
            <h3 className="text-xl font-bold text-ink font-serif mb-2 tracking-wide">
              {s.title}
            </h3>

            {/* 副标题 */}
            <p className="text-ink-light text-sm leading-relaxed mb-3 font-serif italic">
              {s.subtitle}
            </p>

            {/* 描述 */}
            <p className="text-xs text-ink-light font-mono mb-4">
              {s.description}
            </p>

            {/* 分割线和进入按钮 */}
            <div className="rule-single pt-3">
              <div className="flex items-center gap-1 text-gold font-bold text-sm group-hover:gap-2 transition-all font-serif">
                开始咨询
                <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                  <path strokeLinecap="round" strokeLinejoin="round" d="M13.5 4.5 21 12m0 0-7.5 7.5M21 12H3" />
                </svg>
              </div>
            </div>
          </button>
        ))}
      </div>

      {/* 历史会话 */}
      {sessions.length > 0 && (
        <div className="border-2 border-ink bg-paper p-4 mb-6">
          <div className="flex items-center gap-2 mb-3">
            <span className="stamp text-xs">历史会话</span>
            <div className="h-px flex-1 bg-ink" />
          </div>
          <div className="space-y-2">
            {sessions.map(s => (
              <button
                key={s.session_id}
                onClick={() => onResume(s.session_id)}
                className="w-full flex items-center justify-between px-4 py-2 border border-ink/30 hover:border-ink hover:bg-paper-dark/50 transition-colors text-left"
              >
                <span className="font-mono text-sm text-ink truncate max-w-[60%]">
                  {s.session_id.slice(0, 8)}...
                </span>
                <span className="text-xs text-ink-light font-mono">
                  {s.message_count} 条消息
                </span>
                <span className="text-xs text-ink-light font-mono">
                  {new Date(s.created_at).toLocaleDateString()}
                </span>
              </button>
            ))}
          </div>
        </div>
      )}

      {/* 底部数据快报横条 */}
      <div className="border-2 border-ink bg-paper-dark p-4">
        <div className="flex items-center gap-2 mb-3">
          <span className="stamp text-xs">数据快报</span>
          <div className="h-px flex-1 bg-ink" />
        </div>
        <div className="grid grid-cols-3 gap-4 text-center">
          <div>
            <div className="text-2xl sm:text-3xl font-bold text-ink font-mono">3,700+</div>
            <div className="text-xs text-ink-light font-serif mt-1">覆盖全国院校</div>
          </div>
          <div>
            <div className="text-2xl sm:text-3xl font-bold text-ink font-mono">580+</div>
            <div className="text-xs text-ink-light font-serif mt-1">本科专业</div>
          </div>
          <div>
            <div className="text-2xl sm:text-3xl font-bold text-ink font-mono">85,000+</div>
            <div className="text-xs text-ink-light font-serif mt-1">录取分数线</div>
          </div>
        </div>
      </div>

      {/* 底部装饰 */}
      <div className="rule-single mt-8" />
      <div className="text-center mt-4">
        <span className="text-xs text-ink-light font-mono">— 第 1 版 —</span>
      </div>
    </div>
  )
}

export default App
