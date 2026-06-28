import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import App from '../../App'
import { ThemeProvider } from '../../contexts/ThemeContext'
import { API_BASE } from '../../config'

// Mock react-i18next to return Chinese text for known keys
vi.mock('react-i18next', () => ({
  useTranslation: () => ({
    t: (key: string, opts?: Record<string, unknown>) => {
      const overrides: Record<string, string | string[]> = {
        'header.title': '张雪峰AI',
        'header.subtitle': 'ZHANG XUEFENG AI',
        'header.backHome': '返回首页',
        'header.switchToDark': '切换到暗色模式',
        'header.switchToLight': '切换到亮色模式',
        'header.nightMode': '夜间',
        'header.dayMode': '日间',
        'scenarios.gaokao.title': '高考志愿填报',
        'scenarios.gaokao.subtitle': '科学填报，不浪费每一分',
        'scenarios.gaokao.section': '高考志愿',
        'scenarios.gaokao.description': '基于历年录取数据',
        'scenarios.kaoyan.title': '考研择校择专业',
        'scenarios.kaoyan.subtitle': '精准定位，高效备考',
        'scenarios.kaoyan.section': '考研规划',
        'scenarios.kaoyan.description': '院校专业深度分析',
        'scenarios.career.title': '职业规划',
        'scenarios.career.subtitle': '找准方向，赢在起点',
        'scenarios.career.section': '职业发展',
        'scenarios.career.description': '行业就业前景分析',
        'scenarios.startConsult': '开始咨询',
        'portal.mainTitle': '张雪峰AI志愿填报助手',
        'portal.mainSubtitle': '让每个选择都不留遗憾',
        'portal.description': '基于大数据和AI技术',
        'portal.descriptionLine2': '为您提供精准的志愿填报建议',
        'portal.dateLabel': '志愿填报季',
        'portal.nationalEdition': '全国版',
        'portal.pageLabel': '第 1 页',
        'sessions.title': '历史会话',
        'dataBrief.title': '数据概览',
        'footer.issue': '免责声明',
        'footer.motto': '选择比努力更重要',
        'footer.copyright': '2026',
        'chat.title': '在线咨询',
        'chat.send': '发送',
        'chat.inputPlaceholder': '请输入你的问题...',
        'chat.welcomeTitle': '你好，我是张雪峰',
        'chat.welcomeDesc': '有什么志愿填报问题',
        'chat.errorMessage': '抱歉，出现了错误',
        'chat.analyzing': '分析中...',
        'chat.liveConsult': '实时咨询',
        'chat.export': '导出',
        'chat.readerLetter': '读者来信',
        'sourcePanel.title': '数据来源',
        'mobileNav.home': '首页',
        'mobileNav.chat': '咨询',
        'mobileNav.profile': '我的',
        'form.stepOf': `${opts?.current ?? 1} / ${opts?.total ?? 4}`,
        'form.gaokao.steps.score.label': '高考分数',
        'form.gaokao.steps.score.placeholder': '请输入分数',
        'form.gaokao.steps.score.hint': '请输入预估或实际分数',
        'form.gaokao.steps.score.note': '建议使用最近一次模考成绩',
        'form.gaokao.steps.province.label': '省份',
        'form.gaokao.steps.province.selectPlaceholder': '请选择省份',
        'form.gaokao.steps.province.hint': '不同省份分数线差异很大',
        'form.gaokao.steps.province.note': '请按高考报名所在省份填写',
        'form.gaokao.steps.subject.label': '选科方向',
        'form.gaokao.steps.subject.hint': '不同选科对应专业范围不同',
        'form.gaokao.steps.subject.note': '按你的实际科类或选科组合选择',
        'form.gaokao.steps.familyBudget.label': '家庭条件',
        'form.gaokao.steps.familyBudget.hint': '预算会影响城市和院校策略',
        'form.gaokao.steps.familyBudget.note': '这里只做粗粒度判断即可',
        'form.subjects.science': '理科',
        'form.subjects.arts': '文科',
        'form.subjects.physics': '物理',
        'form.subjects.history': '历史',
        'form.subjects.comprehensive': '综合',
        'form.budget.low': '工薪阶层',
        'form.budget.medium': '中等家庭',
        'form.budget.high': '较好家庭',
        'form.budget.unlimited': '优越家庭',
        'form.versionLabels': ['壹', '贰', '叁', '肆'],
        'form.editorNote': '编者按：',
        'form.back': '返回',
        'form.prevStep': '上一步',
        'form.nextStep': '下一步',
        'form.startConsult': '开始咨询',
        'form.skipDirect': '跳过，直接进入咨询',
        'form.pageLabel': `第 ${opts?.page ?? 1} 页`,
        'a11y.skipToContent': '跳转到主要内容',
        'a11y.mainContent': '主要内容',
        'a11y.footer': '页脚',
        'a11y.mobileNav': '移动端导航',
        'a11y.chatRegion': '聊天区域',
        'a11y.messageLog': '消息记录',
        'a11y.chatForm': '发送消息',
        'a11y.soulForm': '信息收集表单',
        'a11y.formProgress': `步骤 ${opts?.current ?? 1}，共 ${opts?.total ?? 4} 步`,
        'a11y.scenarioCards': '咨询场景选择',
        'a11y.closePanel': '关闭面板',
      }
      if (overrides[key]) return overrides[key]
      if (opts?.defaultValue) return opts.defaultValue as string
      return key
    },
    i18n: {
      language: 'zh',
      changeLanguage: vi.fn(),
    },
  }),
  Trans: ({ children }: { children: React.ReactNode }) => children,
}))

function renderApp() {
  return render(
    <ThemeProvider>
      <App />
    </ThemeProvider>,
  )
}

function apiUrl(path: string) {
  return `${API_BASE}${path}`
}

describe('App', () => {
  beforeEach(() => {
    vi.restoreAllMocks()
    window.localStorage.clear()
    vi.spyOn(globalThis, 'fetch').mockResolvedValue({
      ok: true,
      json: () => Promise.resolve([]),
    } as Response)
  })

  it('renders the portal homepage by default', () => {
    renderApp()
    expect(screen.getByRole('banner')).toBeInTheDocument()
    expect(screen.getByRole('main')).toBeInTheDocument()
  })

  it('renders scenario cards on the portal', () => {
    renderApp()
    const list = screen.getByRole('list', { name: '咨询场景选择' })
    expect(list).toBeInTheDocument()
  })

  it('displays three scenario options', () => {
    renderApp()
    const scenarioButtons = screen.getAllByRole('listitem')
    expect(scenarioButtons).toHaveLength(3)
  })

  it('navigates to form view when a scenario is selected', async () => {
    const user = userEvent.setup()
    renderApp()

    const scenarioButtons = screen.getAllByRole('listitem')
    await user.click(scenarioButtons[0])

    await waitFor(() => {
      expect(screen.getByRole('form')).toBeInTheDocument()
    })
  })

  it('navigates back to portal from form view', async () => {
    const user = userEvent.setup()
    renderApp()

    // Go to form
    const scenarioButtons = screen.getAllByRole('listitem')
    await user.click(scenarioButtons[0])

    await waitFor(() => {
      expect(screen.getByRole('form')).toBeInTheDocument()
    })

    // Click back button
    const backButton = screen.getByRole('button', { name: '返回' })
    await user.click(backButton)

    await waitFor(() => {
      expect(screen.getByRole('list', { name: '咨询场景选择' })).toBeInTheDocument()
    })
  })

  it('toggles theme when theme button is clicked', async () => {
    const user = userEvent.setup()
    renderApp()

    // There are two theme buttons (header + mobile nav), get the first one (header)
    const themeButtons = screen.getAllByRole('button', { name: /切换到暗色模式|切换到亮色模式/i })
    expect(themeButtons.length).toBeGreaterThanOrEqual(1)

    await user.click(themeButtons[0])

    await waitFor(() => {
      expect(document.documentElement.classList.contains('dark')).toBe(true)
    })
  })

  it('toggles language when language button is clicked', async () => {
    const user = userEvent.setup()
    renderApp()

    const langButton = screen.getByRole('button', { name: /Switch to English|切换到中文/i })
    expect(langButton).toBeInTheDocument()
    await user.click(langButton)
  })

  it('shows header with title', () => {
    renderApp()
    expect(screen.getByText('张雪峰AI')).toBeInTheDocument()
  })

  it('loads sessions on portal mount', async () => {
    const mockSessions = [
      { session_id: 'abc-123', created_at: '2026-05-30T10:00:00Z', message_count: 5 },
    ]
    vi.spyOn(globalThis, 'fetch').mockResolvedValue({
      ok: true,
      json: () => Promise.resolve(mockSessions),
    } as Response)

    renderApp()

    await waitFor(() => {
      expect(globalThis.fetch).toHaveBeenCalledWith(apiUrl('/api/sessions?limit=10'))
    })
  })

  it('shows back-to-home button when not on portal', async () => {
    const user = userEvent.setup()
    renderApp()

    // Navigate to form
    const scenarioButtons = screen.getAllByRole('listitem')
    await user.click(scenarioButtons[0])

    await waitFor(() => {
      expect(screen.getByRole('form')).toBeInTheDocument()
    })

    expect(screen.getByRole('banner')).toBeInTheDocument()
    expect(screen.getByRole('button', { name: '返回首页' })).toBeInTheDocument()
  })

  it('restores the persisted chat session after refresh', async () => {
    const storedState = {
      view: 'chat',
      scenario: 'gaokao',
      sessionId: 'persisted-session',
      userProfile: {
        score: 620,
        province: '北京',
        subject: '理科',
        familyCondition: '工薪阶层',
      },
    }
    window.localStorage.setItem('zhangxuefeng-agent:app-state', JSON.stringify(storedState))

    vi.spyOn(globalThis, 'fetch').mockImplementation((url) => {
      if (typeof url === 'string' && url === apiUrl('/api/chat')) {
        return Promise.resolve({
          ok: true,
          headers: new Headers({ 'content-type': 'text/event-stream' }),
          body: new ReadableStream({
            start(controller) {
              controller.enqueue(new TextEncoder().encode('data: {"type":"text","content":"已恢复会话"}\n\n'))
              controller.close()
            },
          }),
        } as Response)
      }
      return Promise.resolve({
        ok: false,
        json: () => Promise.resolve(null),
      } as Response)
    })

    renderApp()

    await waitFor(() => {
      expect(screen.getByRole('region', { name: '聊天区域' })).toBeInTheDocument()
    })
    expect(globalThis.fetch).not.toHaveBeenCalledWith(
      apiUrl('/api/chat'),
      expect.anything(),
    )
  })

  it('auto-sends the initial message after refreshing to portal and completing the form again', async () => {
    const user = userEvent.setup()
    const profile = {
      score: 620,
      province: '北京',
      subject: '理科',
      familyCondition: '工薪阶层',
    }
    let chatRequestBody: Record<string, unknown> | null = null

    window.localStorage.setItem('zhangxuefeng-agent:app-state', JSON.stringify({
      view: 'portal',
      scenario: 'gaokao',
      sessionId: 'stale-session',
      userProfile: {
        score: 500,
        province: '河南',
        subject: '文科',
      },
    }))

    vi.spyOn(globalThis, 'fetch').mockImplementation((url, init) => {
      if (typeof url !== 'string') {
        return Promise.resolve({ ok: false, json: () => Promise.resolve(null) } as Response)
      }

      if (url === apiUrl('/api/sessions?limit=10')) {
        return Promise.resolve({ ok: true, json: () => Promise.resolve([]) } as Response)
      }
      if (url.startsWith(apiUrl('/api/profile/')) && init?.method === 'PUT') {
        return Promise.resolve({ ok: true, json: () => Promise.resolve({}) } as Response)
      }
      if (url.includes('/api/session/') && url.endsWith('/favorites')) {
        return Promise.resolve({ ok: false, json: () => Promise.resolve(null) } as Response)
      }
      if (url.includes('/api/session/')) {
        return Promise.resolve({ ok: false, json: () => Promise.resolve(null) } as Response)
      }
      if (url === apiUrl('/api/chat')) {
        chatRequestBody = init?.body ? JSON.parse(String(init.body)) : null
        return Promise.resolve({
          ok: true,
          headers: new Headers({ 'content-type': 'text/event-stream' }),
          body: new ReadableStream({
            start(controller) {
              controller.enqueue(new TextEncoder().encode('data: {"type":"text","content":"好的，开始分析"}\n\n'))
              controller.close()
            },
          }),
        } as Response)
      }

      return Promise.resolve({ ok: false, json: () => Promise.resolve(null) } as Response)
    })

    renderApp()

    await user.click(screen.getAllByRole('listitem')[0])
    await waitFor(() => {
      expect(screen.getByRole('form')).toBeInTheDocument()
    })

    await user.type(screen.getByLabelText('高考分数'), String(profile.score))
    await user.click(screen.getByRole('button', { name: '下一步' }))
    await user.selectOptions(screen.getByRole('combobox', { name: '省份' }), profile.province)
    await user.click(screen.getByRole('button', { name: '下一步' }))
    await user.click(screen.getByRole('radio', { name: profile.subject }))
    await user.click(screen.getByRole('button', { name: '下一步' }))
    await user.click(screen.getByRole('radio', { name: profile.familyCondition }))
    await user.click(screen.getByRole('button', { name: '开始咨询' }))

    await waitFor(() => {
      expect(screen.getByRole('region', { name: '聊天区域' })).toBeInTheDocument()
    })

    await waitFor(() => {
      expect(chatRequestBody).not.toBeNull()
    })

    expect(chatRequestBody).toMatchObject({
      stream: true,
      user_context: {
        分数: 620,
        省份: '北京',
        科类: '理科',
        家庭条件: '工薪阶层',
      },
    })
  })
})
