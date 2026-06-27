import { useState, useEffect, Suspense, lazy } from 'react'
import { useTranslation } from 'react-i18next'
import Loading from './components/Loading'
import { useTheme } from './contexts/useTheme'
import { updateUserProfile } from './api/profile'
import { API_BASE } from './config'
import type { UserProfile } from './types'

/* ── Lazy-loaded components (code-split) ──────────────────── */
const ChatInterface = lazy(() => import('./components/ChatInterface'))
const SoulQuestionForm = lazy(() => import('./components/SoulQuestionForm'))

// Pre-declared lazy chunks for code-splitting (consumed by ChatInterface or future views)
const RecommendationCard = lazy(() => import('./components/RecommendationCard'))
const DataVisualization = lazy(() => import('./components/DataVisualization'))
const AdmissionSimulator = lazy(() => import('./components/AdmissionSimulator'))

// Ensure lazy chunks are registered at module scope for Vite code-splitting
void RecommendationCard
void DataVisualization
void AdmissionSimulator

type View = 'portal' | 'form' | 'chat'
type Scenario = 'gaokao' | 'kaoyan' | 'career'

interface SessionSummary {
  session_id: string
  created_at: string
  message_count: number
}

interface PersistedAppState {
  view: View
  scenario: Scenario
  sessionId: string
  userProfile: UserProfile | null
}

const APP_STATE_STORAGE_KEY = 'zhangxuefeng-agent:app-state'

function readPersistedAppState(): PersistedAppState | null {
  try {
    const raw = window.localStorage.getItem(APP_STATE_STORAGE_KEY)
    if (!raw) return null
    const parsed = JSON.parse(raw) as Partial<PersistedAppState>
    if (!parsed || typeof parsed !== 'object') return null
    if (
      (parsed.view !== 'portal' && parsed.view !== 'form' && parsed.view !== 'chat') ||
      (parsed.scenario !== 'gaokao' && parsed.scenario !== 'kaoyan' && parsed.scenario !== 'career') ||
      typeof parsed.sessionId !== 'string'
    ) {
      return null
    }
    return {
      view: parsed.view,
      scenario: parsed.scenario,
      sessionId: parsed.sessionId,
      userProfile: parsed.userProfile ?? null,
    }
  } catch {
    return null
  }
}

function App() {
  const persistedState = readPersistedAppState()
  const { t, i18n } = useTranslation()
  const [view, setView] = useState<View>(persistedState?.view ?? 'portal')
  const [scenario, setScenario] = useState<Scenario>(persistedState?.scenario ?? 'gaokao')
  const [sessionId, setSessionId] = useState(() => persistedState?.sessionId ?? crypto.randomUUID())
  const [userProfile, setUserProfile] = useState<UserProfile | null>(persistedState?.userProfile ?? null)
  const [autoStartRequestId, setAutoStartRequestId] = useState<string | null>(null)
  const { theme, toggleTheme } = useTheme()

  const toggleLanguage = () => {
    const newLang = i18n.language === 'zh' ? 'en' : 'zh'
    i18n.changeLanguage(newLang)
  }

  const scenarios = [
    {
      id: 'gaokao' as Scenario,
      title: t('scenarios.gaokao.title'),
      subtitle: t('scenarios.gaokao.subtitle'),
      icon: '🎓',
      section: t('scenarios.gaokao.section'),
      description: t('scenarios.gaokao.description'),
    },
    {
      id: 'kaoyan' as Scenario,
      title: t('scenarios.kaoyan.title'),
      subtitle: t('scenarios.kaoyan.subtitle'),
      icon: '📚',
      section: t('scenarios.kaoyan.section'),
      description: t('scenarios.kaoyan.description'),
    },
    {
      id: 'career' as Scenario,
      title: t('scenarios.career.title'),
      subtitle: t('scenarios.career.subtitle'),
      icon: '💼',
      section: t('scenarios.career.section'),
      description: t('scenarios.career.description'),
    },
  ]

  const handleScenarioSelect = (s: Scenario) => {
    setSessionId(crypto.randomUUID())
    setScenario(s)
    setUserProfile(null)
    setAutoStartRequestId(null)
    setView('form')
  }

  const handleFormComplete = (profile: UserProfile) => {
    setUserProfile(profile)
    setAutoStartRequestId(crypto.randomUUID())
    updateUserProfile(sessionId, profile).catch(() => {})
    setView('chat')
  }

  const handleResumeSession = (sid: string) => {
    setSessionId(sid as ReturnType<typeof crypto.randomUUID>)
    setUserProfile(null)
    setAutoStartRequestId(null)
    setView('chat')
  }

  const handleBackToPortal = () => {
    setAutoStartRequestId(null)
    setView('portal')
  }

  useEffect(() => {
    const nextState: PersistedAppState = {
      view,
      scenario,
      sessionId,
      userProfile,
    }
    window.localStorage.setItem(APP_STATE_STORAGE_KEY, JSON.stringify(nextState))
  }, [sessionId, scenario, userProfile, view])

  return (
    <div className="min-h-screen flex flex-col bg-paper paper-texture">
      {/* Skip to main content link */}
      <a
        href="#main-content"
        className="sr-only focus:not-sr-only focus:fixed focus:top-2 focus:left-2 focus:z-[100]
                   focus:px-4 focus:py-2 focus:bg-ink focus:text-paper focus:font-serif focus:font-bold"
      >
        {t('a11y.skipToContent', { defaultValue: '跳转到主要内容' })}
      </a>

      {/* Header */}
      <header role="banner" className="bg-paper-dark/80 backdrop-blur-md border-b-2 border-ink sticky top-0 z-50">
        <div className="max-w-6xl mx-auto px-4 py-3">
          <div className="flex items-center justify-between">
            <button
              onClick={handleBackToPortal}
              className="flex items-center gap-3 group"
              aria-label={t('header.title')}
            >
              <div className="w-10 h-10 sm:w-12 sm:h-12 bg-ink flex items-center justify-center">
                <span className="text-gold font-bold text-lg sm:text-xl font-serif">张</span>
              </div>
              <div className="text-left">
                <h1 className="text-lg sm:text-xl font-bold text-ink font-serif leading-tight tracking-wide">
                  {t('header.title')}
                </h1>
                <p className="text-[10px] sm:text-xs text-ink-light font-mono tracking-widest uppercase">
                  {t('header.subtitle')}
                </p>
              </div>
            </button>

            <div className="flex items-center gap-2">
              {/* Language switch */}
              <button
                onClick={toggleLanguage}
                className="w-9 h-9 flex items-center justify-center border border-ink/30
                           hover:bg-ink/10 transition-colors text-xs font-mono font-bold text-ink"
                aria-label={i18n.language === 'zh' ? 'Switch to English' : '切换到中文'}
              >
                {i18n.language === 'zh' ? 'EN' : '中'}
              </button>

              {/* Theme toggle */}
              <button
                onClick={toggleTheme}
                className="w-9 h-9 flex items-center justify-center border border-ink/30
                           hover:bg-ink/10 transition-colors"
                aria-label={theme === 'light' ? t('header.switchToDark') : t('header.switchToLight')}
              >
                {theme === 'light' ? (
                  <svg className="w-4 h-4 text-ink" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                    <path strokeLinecap="round" strokeLinejoin="round" d="M21.752 15.002A9.72 9.72 0 0 1 18 15.75c-5.385 0-9.75-4.365-9.75-9.75 0-1.33.266-2.597.748-3.752A9.753 9.753 0 0 0 3 11.25C3 16.635 7.365 21 12.75 21a9.753 9.753 0 0 0 9.002-5.998Z" />
                  </svg>
                ) : (
                  <svg className="w-4 h-4 text-gold" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                    <path strokeLinecap="round" strokeLinejoin="round" d="M12 3v2.25m6.364.386-1.591 1.591M21 12h-2.25m-.386 6.364-1.591-1.591M12 18.75V21m-4.773-4.227-1.591 1.591M5.25 12H3m4.227-4.773L5.636 5.636M15.75 12a3.75 3.75 0 1 1-7.5 0 3.75 3.75 0 0 1 7.5 0Z" />
                  </svg>
                )}
              </button>

              {view !== 'portal' && (
                <button
                  onClick={handleBackToPortal}
                  className="hidden sm:block px-4 py-2 text-sm font-serif text-ink
                             border border-ink
                             hover:bg-ink hover:text-paper transition-colors"
                  aria-label={t('header.backHome')}
                >
                  {t('header.backHome')}
                </button>
              )}
            </div>
          </div>
        </div>
      </header>

      {/* Main Content */}
      <main id="main-content" role="main" aria-label={t('a11y.mainContent', { defaultValue: '主要内容' })} className="flex-1 pb-16 sm:pb-0">
        {view === 'portal' && (
          <PortalHome onSelect={handleScenarioSelect} onResume={handleResumeSession} scenarios={scenarios} />
        )}
        {view === 'form' && (
          <Suspense fallback={<Loading fullScreen />}>
            <SoulQuestionForm
              scenario={scenario}
              onComplete={handleFormComplete}
              onBack={handleBackToPortal}
            />
          </Suspense>
        )}
        {view === 'chat' && (
          <Suspense fallback={<Loading fullScreen />}>
            <div className="max-w-7xl mx-auto p-2 sm:p-4 h-[calc(100vh-80px)] sm:h-[calc(100vh-80px)]">
              <ChatInterface
                sessionId={sessionId}
                userProfile={userProfile}
                scenario={scenario}
                autoStartRequestId={autoStartRequestId}
                onAutoStartHandled={() => setAutoStartRequestId(null)}
              />
            </div>
          </Suspense>
        )}
      </main>

      {/* Footer (portal only, desktop) */}
      {view === 'portal' && (
        <footer role="contentinfo" aria-label={t('a11y.footer', { defaultValue: '页脚' })} className="hidden sm:block border-t-2 border-ink bg-paper-dark/50 py-4">
          <div className="max-w-6xl mx-auto px-4 flex flex-wrap justify-between items-center text-xs text-ink-light font-mono">
            <span>{t('footer.issue')}</span>
            <span>{t('footer.motto')}</span>
            <span>{t('footer.copyright')}</span>
          </div>
        </footer>
      )}

      {/* Mobile bottom nav */}
      <MobileBottomNav
        view={view}
        onBackToPortal={handleBackToPortal}
        onToggleTheme={toggleTheme}
        theme={theme}
      />
    </div>
  )
}

/* ── Mobile Bottom Nav ─────────────────────────────────── */
function MobileBottomNav({
  view,
  onBackToPortal,
  onToggleTheme,
  theme,
}: {
  view: View
  onBackToPortal: () => void
  onToggleTheme: () => void
  theme: 'light' | 'dark'
}) {
  const { t } = useTranslation()

  return (
    <nav role="navigation" aria-label={t('a11y.mobileNav', { defaultValue: '移动端导航' })} className="sm:hidden fixed bottom-0 left-0 right-0 z-50 bg-paper
                    border-t-2 border-ink
                    safe-area-bottom">
      <div className="flex items-center justify-around h-14">
        <button
          onClick={onBackToPortal}
          aria-label={t('mobileNav.home')}
          aria-current={view === 'portal' ? 'page' : undefined}
          className={`flex flex-col items-center gap-0.5 px-3 py-1 transition-colors
            ${view === 'portal' ? 'text-gold' : 'text-ink-light'}`}
        >
          <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
            <path strokeLinecap="round" strokeLinejoin="round" d="m2.25 12 8.954-8.955c.44-.439 1.152-.439 1.591 0L21.75 12M4.5 9.75v10.125c0 .621.504 1.125 1.125 1.125H9.75v-4.875c0-.621.504-1.125 1.125-1.125h2.25c.621 0 1.125.504 1.125 1.125V21h4.125c.621 0 1.125-.504 1.125-1.125V9.75M8.25 21h8.25" />
          </svg>
          <span className="text-[10px] font-mono">{t('mobileNav.home')}</span>
        </button>

        <button
          onClick={onToggleTheme}
          aria-label={theme === 'light' ? t('header.switchToDark') : t('header.switchToLight')}
          className="flex flex-col items-center gap-0.5 px-3 py-1 text-ink-light transition-colors"
        >
          {theme === 'light' ? (
            <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M21.752 15.002A9.72 9.72 0 0 1 18 15.75c-5.385 0-9.75-4.365-9.75-9.75 0-1.33.266-2.597.748-3.752A9.753 9.753 0 0 0 3 11.25C3 16.635 7.365 21 12.75 21a9.753 9.753 0 0 0 9.002-5.998Z" />
            </svg>
          ) : (
            <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M12 3v2.25m6.364.386-1.591 1.591M21 12h-2.25m-.386 6.364-1.591-1.591M12 18.75V21m-4.773-4.227-1.591 1.591M5.25 12H3m4.227-4.773L5.636 5.636M15.75 12a3.75 3.75 0 1 1-7.5 0 3.75 3.75 0 0 1 7.5 0Z" />
            </svg>
          )}
          <span className="text-[10px] font-mono">{theme === 'light' ? t('header.nightMode') : t('header.dayMode')}</span>
        </button>

        <button
          aria-label={t('mobileNav.chat')}
          aria-current={view === 'chat' ? 'page' : undefined}
          className={`flex flex-col items-center gap-0.5 px-3 py-1 transition-colors
            ${view === 'chat' ? 'text-gold' : 'text-ink-light'}`}
        >
          <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
            <path strokeLinecap="round" strokeLinejoin="round" d="M20.25 8.511c.884.284 1.5 1.128 1.5 2.097v4.286c0 1.136-.847 2.1-1.98 2.193-.34.027-.68.052-1.02.072v3.091l-3-3c-1.354 0-2.694-.055-4.02-.163a2.115 2.115 0 0 1-.825-.242m9.345-8.334a2.126 2.126 0 0 0-.476-.095 48.64 48.64 0 0 0-8.048 0c-1.131.094-1.976 1.057-1.976 2.192v4.286c0 .837.46 1.58 1.155 1.951m9.345-8.334V6.637c0-1.621-1.152-3.026-2.76-3.235A48.455 48.455 0 0 0 11.25 3c-2.115 0-4.198.137-6.24.402-1.608.209-2.76 1.614-2.76 3.235v6.226c0 1.621 1.152 3.026 2.76 3.235.577.075 1.157.14 1.74.194V21l4.155-4.155" />
          </svg>
          <span className="text-[10px] font-mono">{t('mobileNav.chat')}</span>
        </button>

        <button
          aria-label={t('mobileNav.profile')}
          className="flex flex-col items-center gap-0.5 px-3 py-1 text-ink-light transition-colors"
        >
          <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
            <path strokeLinecap="round" strokeLinejoin="round" d="M15.75 6a3.75 3.75 0 1 1-7.5 0 3.75 3.75 0 0 1 7.5 0ZM4.501 20.118a7.5 7.5 0 0 1 14.998 0A17.933 17.933 0 0 1 12 21.75c-2.676 0-5.216-.584-7.499-1.632Z" />
          </svg>
          <span className="text-[10px] font-mono">{t('mobileNav.profile')}</span>
        </button>
      </div>
    </nav>
  )
}

/* ── Portal Homepage ────────────────────────── */
function PortalHome({ onSelect, onResume, scenarios }: {
  onSelect: (s: Scenario) => void
  onResume: (sid: string) => void
  scenarios: Array<{
    id: Scenario
    title: string
    subtitle: string
    icon: string
    section: string
    description: string
  }>
}) {
  const { t } = useTranslation()
  const [sessions, setSessions] = useState<SessionSummary[]>([])

  useEffect(() => {
    fetch(`${API_BASE}/api/sessions?limit=10`)
      .then(r => r.json())
      .then(data => setSessions(data))
      .catch(() => {})
  }, [])
  const today = new Date()
  const dateStr = `${today.getFullYear()} 年 ${today.getMonth() + 1} 月 ${today.getDate()} 日`

  return (
    <div className="max-w-5xl mx-auto px-4 py-6 sm:py-12">
      {/* Masthead */}
      <div className="text-center mb-8 sm:mb-10">
        <div className="rule-thick mb-4" />
        <div className="rule-double mb-6" />

        <div className="flex justify-between items-center text-[10px] sm:text-xs font-mono text-ink-light mb-4 px-2 sm:px-4">
          <span>{dateStr}</span>
          <span className="hidden sm:inline">{t('portal.dateLabel')}</span>
          <span>{t('portal.nationalEdition')}</span>
        </div>

        <h2 className="text-3xl sm:text-6xl font-black text-ink font-serif leading-tight mb-3 tracking-wide">
          {t('portal.mainTitle')}
        </h2>
        <div className="flex items-center justify-center gap-2 sm:gap-4 mb-4 px-2">
          <div className="h-px flex-1 bg-ink-border" />
          <span className="text-base sm:text-2xl font-bold text-gold font-serif whitespace-nowrap">
            {t('portal.mainSubtitle')}
          </span>
          <div className="h-px flex-1 bg-ink-border" />
        </div>

        <p className="text-sm sm:text-lg text-ink-light max-w-2xl mx-auto leading-relaxed font-serif px-2">
          {t('portal.description')}
          <br className="hidden sm:block" />
          {t('portal.descriptionLine2')}
        </p>

        <div className="rule-double mt-6" />
        <div className="rule-single mt-1" />
      </div>

      {/* Scenario cards */}
      <div role="list" aria-label={t('a11y.scenarioCards', { defaultValue: '咨询场景选择' })} className="grid gap-4 sm:gap-6 grid-cols-1 sm:grid-cols-3 mb-8 sm:mb-10">
        {scenarios.map((s) => (
          <button
            key={s.id}
            role="listitem"
            aria-label={`${s.title} - ${s.subtitle}`}
            onClick={() => onSelect(s.id)}
            className="group relative bg-paper border-2 border-ink
                       p-5 sm:p-6 text-left transition-all duration-300
                       hover:shadow-warm-xl hover:-translate-y-1
                       active:scale-[0.98] sm:active:scale-100
                       focus-visible:ring-2 focus-visible:ring-gold focus-visible:ring-offset-2 outline-none"
          >
            <div className="absolute top-0 left-0 bg-ink text-paper px-3 py-1 text-xs font-mono font-bold">
              {s.section}
            </div>

            <div className="text-3xl sm:text-4xl mb-3 sm:mb-4 mt-4">
              {s.icon}
            </div>

            <h3 className="text-lg sm:text-xl font-bold text-ink font-serif mb-2 tracking-wide">
              {s.title}
            </h3>

            <p className="text-ink-light text-sm leading-relaxed mb-3 font-serif italic">
              {s.subtitle}
            </p>

            <p className="text-xs text-ink-light font-mono mb-4">
              {s.description}
            </p>

            <div className="rule-single pt-3">
              <div className="flex items-center gap-1 text-gold font-bold text-sm group-hover:gap-2 transition-all font-serif">
                {t('scenarios.startConsult')}
                <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                  <path strokeLinecap="round" strokeLinejoin="round" d="M13.5 4.5 21 12m0 0-7.5 7.5M21 12H3" />
                </svg>
              </div>
            </div>
          </button>
        ))}
      </div>

      {/* Session history */}
      {sessions.length > 0 && (
        <div role="region" aria-label={t('sessions.title')} className="border-2 border-ink bg-paper p-4 mb-6">
          <div className="flex items-center gap-2 mb-3">
            <span className="stamp text-xs">{t('sessions.title')}</span>
            <div className="h-px flex-1 bg-ink-border" />
          </div>
          <div className="space-y-2">
            {sessions.map(s => (
              <button
                key={s.session_id}
                onClick={() => onResume(s.session_id)}
                aria-label={t('sessions.resumeLabel', { id: s.session_id.slice(0, 8), count: s.message_count, defaultValue: `恢复会话 ${s.session_id.slice(0, 8)}，${s.message_count} 条消息` })}
                className="w-full flex items-center justify-between px-4 py-3 sm:py-2
                           border border-ink/30
                           hover:border-ink
                           hover:bg-paper-dark/50 transition-colors text-left
                           active:bg-paper-dark"
              >
                <span className="font-mono text-sm text-ink truncate max-w-[40%] sm:max-w-[60%]">
                  {s.session_id.slice(0, 8)}...
                </span>
                <span className="text-xs text-ink-light font-mono hidden sm:inline">
                  {t('sessions.messages', { count: s.message_count })}
                </span>
                <span className="text-xs text-ink-light font-mono">
                  {new Date(s.created_at).toLocaleDateString()}
                </span>
              </button>
            ))}
          </div>
        </div>
      )}

      {/* Data highlights */}
      <div className="border-2 border-ink bg-paper-dark p-4">
        <div className="flex items-center gap-2 mb-3">
          <span className="stamp text-xs">{t('dataBrief.title')}</span>
          <div className="h-px flex-1 bg-ink-border" />
        </div>
        <div className="grid grid-cols-3 gap-4 text-center">
          <div>
            <div className="text-xl sm:text-3xl font-bold text-ink font-mono">3,700+</div>
            <div className="text-[10px] sm:text-xs text-ink-light font-serif mt-1">{t('dataBrief.universities')}</div>
          </div>
          <div>
            <div className="text-xl sm:text-3xl font-bold text-ink font-mono">580+</div>
            <div className="text-[10px] sm:text-xs text-ink-light font-serif mt-1">{t('dataBrief.majors')}</div>
          </div>
          <div>
            <div className="text-xl sm:text-3xl font-bold text-ink font-mono">85,000+</div>
            <div className="text-[10px] sm:text-xs text-ink-light font-serif mt-1">{t('dataBrief.scores')}</div>
          </div>
        </div>
      </div>

      <div className="rule-single mt-8" />
      <div className="text-center mt-4">
        <span className="text-xs text-ink-light font-mono">{t('portal.pageLabel')}</span>
      </div>
    </div>
  )
}

export default App
