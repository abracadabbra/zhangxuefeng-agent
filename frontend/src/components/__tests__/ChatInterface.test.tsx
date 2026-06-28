import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import ChatInterface from '../ChatInterface'
import { API_BASE } from '../../config'

// Mock react-i18next
vi.mock('react-i18next', () => ({
  useTranslation: () => ({
    t: (key: string, opts?: Record<string, unknown>) => {
      if (opts?.defaultValue) return opts.defaultValue as string
      return key
    },
  }),
}))

// Mock child components
vi.mock('../MessageBubble', () => ({
  default: ({ message }: { message: { role: string; content: string } }) => (
    <div data-testid={`message-${message.role}`}>{message.content}</div>
  ),
}))

vi.mock('../SourcePanel', () => ({
  default: ({ sources }: { sources: unknown[] }) => (
    <div data-testid="source-panel">Sources: {sources.length}</div>
  ),
}))

function apiUrl(path: string) {
  return `${API_BASE}${path}`
}

describe('ChatInterface', () => {
  beforeEach(() => {
    vi.restoreAllMocks()
    window.localStorage.clear()
    // Default mock for session history fetch
    vi.spyOn(globalThis, 'fetch').mockResolvedValue({
      ok: false,
      json: () => Promise.resolve(null),
    } as Response)
  })

  it('renders the chat region', () => {
    render(<ChatInterface sessionId="test-session" />)
    expect(screen.getByRole('region', { name: '聊天区域' })).toBeInTheDocument()
  })

  it('shows welcome message when no messages', () => {
    render(<ChatInterface sessionId="test-session" />)
    expect(screen.getByText('chat.welcomeTitle')).toBeInTheDocument()
    expect(screen.getByText('chat.welcomeDesc')).toBeInTheDocument()
  })

  it('renders the input textarea and send button', () => {
    render(<ChatInterface sessionId="test-session" />)
    expect(screen.getByLabelText('chat.inputPlaceholder')).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /chat\.send/i })).toBeInTheDocument()
  })

  it('shows question progress for missing profile fields', () => {
    render(<ChatInterface sessionId="test-session" />)

    expect(screen.getByLabelText('追问进度')).toBeInTheDocument()
    expect(screen.getByText('必要信息 0/4')).toBeInTheDocument()
    expect(screen.getByText('0%')).toBeInTheDocument()
    expect(screen.getByText('还差：分数、省份、科类/选科、家庭条件')).toBeInTheDocument()
  })

  it('shows completed question progress for complete profile', () => {
    render(
      <ChatInterface
        sessionId="test-session"
        userProfile={{
          score: 650,
          province: '北京',
          subject: '物理 化学 生物',
          familyCondition: '工薪阶层',
        }}
      />,
    )

    expect(screen.getByText('必要信息 4/4')).toBeInTheDocument()
    expect(screen.getByText('100%')).toBeInTheDocument()
    expect(screen.getByText(/必要信息已齐，可以生成更完整的推荐/)).toBeInTheDocument()
  })

  it('includes enhanced profile fields in optional progress hints', () => {
    render(
      <ChatInterface
        sessionId="test-session"
        userProfile={{
          score: 650,
          province: '北京',
          subject: '物理 化学 生物',
          familyCondition: '工薪阶层',
          targetCity: '北京',
          riskTolerance: '稳健',
          careerGoal: '计算机',
        }}
      />,
    )

    expect(screen.getByText(/可补充：省份批次、选科限制/)).toBeInTheDocument()
  })

  it('loads session history on mount', async () => {
    const mockHistory = {
      messages: [
        { role: 'user', content: '你好' },
        { role: 'assistant', content: '你好！有什么可以帮你的？' },
      ],
    }
    vi.spyOn(globalThis, 'fetch').mockResolvedValue({
      ok: true,
      json: () => Promise.resolve(mockHistory),
    } as Response)

    render(<ChatInterface sessionId="test-session" />)

    await waitFor(() => {
      expect(globalThis.fetch).toHaveBeenCalledWith(apiUrl('/api/session/test-session'))
    })

    await waitFor(() => {
      expect(screen.getByText('你好')).toBeInTheDocument()
      expect(screen.getByText('你好！有什么可以帮你的？')).toBeInTheDocument()
    })
  })

  it('opens Markdown and PDF report exports from the chat header', async () => {
    const user = userEvent.setup()
    const openSpy = vi.spyOn(window, 'open').mockImplementation(() => null)
    const mockHistory = {
      messages: [
        { role: 'user', content: '你好' },
        { role: 'assistant', content: '你好！有什么可以帮你的？' },
      ],
    }
    vi.spyOn(globalThis, 'fetch').mockResolvedValue({
      ok: true,
      json: () => Promise.resolve(mockHistory),
    } as Response)

    render(<ChatInterface sessionId="test-session" />)

    await waitFor(() => {
      expect(screen.getByText('你好！有什么可以帮你的？')).toBeInTheDocument()
    })

    await user.click(screen.getByRole('button', { name: 'chat.exportMarkdown' }))
    await user.click(screen.getByRole('button', { name: 'chat.exportPdf' }))

    expect(openSpy).toHaveBeenCalledWith(apiUrl('/api/session/test-session/export'), '_blank')
    expect(openSpy).toHaveBeenCalledWith(apiUrl('/api/session/test-session/export/pdf'), '_blank')
  })

  it('sends a message and displays it', async () => {
    const user = userEvent.setup()

    // Mock SSE response
    const encoder = new TextEncoder()
    const stream = new ReadableStream({
      start(controller) {
        controller.enqueue(encoder.encode('data: {"type":"text","content":"回复内容"}\n\n'))
        controller.close()
      },
    })

    vi.spyOn(globalThis, 'fetch').mockImplementation((url) => {
      if (typeof url === 'string' && url === apiUrl('/api/chat')) {
        return Promise.resolve({
          ok: true,
          headers: new Headers({ 'content-type': 'text/event-stream' }),
          body: stream,
        } as Response)
      }
      return Promise.resolve({
        ok: false,
        json: () => Promise.resolve(null),
      } as Response)
    })

    render(<ChatInterface sessionId="test-session" />)

    const input = screen.getByLabelText('chat.inputPlaceholder')
    await user.type(input, '测试消息')

    const sendButton = screen.getByRole('button', { name: /chat\.send/i })
    await user.click(sendButton)

    // User message should appear
    await waitFor(() => {
      expect(screen.getByText('测试消息')).toBeInTheDocument()
    })

    // API should be called
    await waitFor(() => {
      expect(globalThis.fetch).toHaveBeenCalledWith(
        apiUrl('/api/chat'),
        expect.objectContaining({ method: 'POST' }),
      )
    })
  })

  it('does not send empty messages', async () => {
    const user = userEvent.setup()
    render(<ChatInterface sessionId="test-session" />)

    const sendButton = screen.getByRole('button', { name: /chat\.send/i })
    await user.click(sendButton)

    expect((globalThis.fetch as ReturnType<typeof vi.fn>).mock.calls).not.toContainEqual([
      apiUrl('/api/chat'),
      expect.anything(),
    ])
    expect(globalThis.fetch).toHaveBeenCalledWith(apiUrl('/api/session/test-session'))
  })

  it('shows error message on fetch failure', async () => {
    const user = userEvent.setup()

    vi.spyOn(globalThis, 'fetch').mockImplementation((url) => {
      if (typeof url === 'string' && url.includes('/api/session')) {
        return Promise.resolve({ ok: false, json: () => Promise.resolve(null) } as Response)
      }
      return Promise.reject(new Error('Network error'))
    })

    render(<ChatInterface sessionId="test-session" />)

    const input = screen.getByLabelText('chat.inputPlaceholder')
    await user.type(input, '测试')

    const sendButton = screen.getByRole('button', { name: /chat\.send/i })
    await user.click(sendButton)

    await waitFor(() => {
      expect(screen.getByText('chat.errorMessage')).toBeInTheDocument()
    })
  })

  it('handles Enter key to send message', async () => {
    const user = userEvent.setup()

    const encoder = new TextEncoder()
    const stream = new ReadableStream({
      start(controller) {
        controller.enqueue(encoder.encode('data: {"type":"text","content":"ok"}\n\n'))
        controller.close()
      },
    })

    vi.spyOn(globalThis, 'fetch').mockImplementation((url) => {
      if (typeof url === 'string' && url.includes('/api/session')) {
        return Promise.resolve({ ok: false, json: () => Promise.resolve(null) } as Response)
      }
      return Promise.resolve({
        ok: true,
        headers: new Headers({ 'content-type': 'text/event-stream' }),
        body: stream,
      } as Response)
    })

    render(<ChatInterface sessionId="test-session" />)

    const input = screen.getByLabelText('chat.inputPlaceholder')
    await user.type(input, '测试消息{Enter}')

    await waitFor(() => {
      expect(screen.getByText('测试消息')).toBeInTheDocument()
    })
  })

  it('shows loading indicator while waiting for response', async () => {
    const user = userEvent.setup()

    // Never-resolving promise to keep loading state
    vi.spyOn(globalThis, 'fetch').mockImplementation((url) => {
      if (typeof url === 'string' && url.includes('/api/session')) {
        return Promise.resolve({ ok: false, json: () => Promise.resolve(null) } as Response)
      }
      return new Promise(() => {})
    })

    render(<ChatInterface sessionId="test-session" />)

    const input = screen.getByLabelText('chat.inputPlaceholder')
    await user.type(input, '测试')

    const sendButton = screen.getByRole('button', { name: /chat\.send/i })
    await user.click(sendButton)

    await waitFor(() => {
      expect(screen.getByRole('status')).toBeInTheDocument()
    })
  })

  it('sends user profile context on first message', async () => {
    const user = userEvent.setup()
    const userProfile = { score: 600, province: '北京', subject: '理科' }

    const encoder = new TextEncoder()
    vi.spyOn(globalThis, 'fetch').mockImplementation((url) => {
      if (typeof url === 'string' && url === apiUrl('/api/session/test-session/favorites')) {
        return Promise.resolve({ ok: false, json: () => Promise.resolve(null) } as Response)
      }
      if (typeof url === 'string' && url === apiUrl('/api/session/test-session')) {
        return Promise.resolve({
          ok: true,
          json: () => Promise.resolve({
            messages: [{ role: 'assistant', content: '历史消息' }],
          }),
        } as Response)
      }
      return Promise.resolve({
        ok: true,
        headers: new Headers({ 'content-type': 'text/event-stream' }),
        body: new ReadableStream({
          start(controller) {
            controller.enqueue(encoder.encode('data: {"type":"text","content":"ok"}\n\n'))
            controller.close()
          },
        }),
      } as Response)
    })

    render(<ChatInterface sessionId="test-session" userProfile={userProfile} />)

    const input = screen.getByLabelText('chat.inputPlaceholder')
    await user.type(input, '你好')

    const sendButton = screen.getByRole('button', { name: /chat\.send/i })
    await user.click(sendButton)

    await waitFor(() => {
      const chatCall = (globalThis.fetch as ReturnType<typeof vi.fn>).mock.calls.find(
        (call: unknown[]) => typeof call[0] === 'string' && call[0] === apiUrl('/api/chat'),
      )
      expect(chatCall).toBeDefined()
      const body = JSON.parse(chatCall![1].body)
      expect(body.user_context).toEqual({
        分数: 600,
        省份: '北京',
        科类: '理科',
        家庭条件: undefined,
      })
    })
  })

  it('streams the automatic initial profile message', async () => {
    const userProfile = {
      score: 600,
      province: '北京',
      subject: '理科',
      familyCondition: '工薪阶层',
    }
    const onAutoStartHandled = vi.fn()

    const encoder = new TextEncoder()
    const stream = new ReadableStream({
      start(controller) {
        controller.enqueue(encoder.encode('data: {"type":"text","content":"第一段"}\n\n'))
        controller.enqueue(encoder.encode('data: {"type":"text","content":"第二段"}\n\n'))
        controller.close()
      },
    })

    vi.spyOn(globalThis, 'fetch').mockImplementation((url) => {
      if (typeof url === 'string' && url.includes('/api/session')) {
        return Promise.resolve({ ok: false, json: () => Promise.resolve(null) } as Response)
      }
      return Promise.resolve({
        ok: true,
        headers: new Headers({ 'content-type': 'text/event-stream' }),
        body: stream,
      } as Response)
    })

    render(
      <ChatInterface
        sessionId="auto-init-session"
        userProfile={userProfile}
        autoStartRequestId="req-1"
        onAutoStartHandled={onAutoStartHandled}
      />,
    )

    await waitFor(() => {
      expect(screen.getByText(/第一段第二段/)).toBeInTheDocument()
    })

    const chatCall = (globalThis.fetch as ReturnType<typeof vi.fn>).mock.calls.find(
      (call: unknown[]) => typeof call[0] === 'string' && call[0] === apiUrl('/api/chat'),
    )
    expect(chatCall).toBeDefined()
    const body = JSON.parse(chatCall![1].body)
    expect(body.stream).toBe(true)
    expect(body.user_context).toEqual({
      分数: 600,
      省份: '北京',
      科类: '理科',
      家庭条件: '工薪阶层',
      目标城市: undefined,
      风险偏好: undefined,
      职业方向: undefined,
      省份批次: undefined,
      选科限制: undefined,
      位次: undefined,
      家庭预算: undefined,
      地域偏好: undefined,
      城市层级: undefined,
      职业偏好权重: undefined,
    })
    expect(onAutoStartHandled).toHaveBeenCalledTimes(1)
  })

  it('persists favorite recommendations by session', async () => {
    const user = userEvent.setup()
    const recommendResponse = {
      summary: '建议按冲稳保组合填报。',
      recommendations: [
        {
          school_name: '清华大学',
          reason: '学校实力强，方向匹配。',
          admission_probability: 0.75,
          match_score: 9,
          strategy: '稳',
          risk_points: ['热门专业竞争激烈'],
          alternatives: ['北京邮电大学'],
        },
      ],
      gradient_summary: { 稳: ['清华大学'] },
    }

    vi.spyOn(globalThis, 'fetch').mockImplementation((url) => {
      if (typeof url === 'string' && url.includes('/api/recommend')) {
        return Promise.resolve({
          ok: true,
          json: () => Promise.resolve(recommendResponse),
        } as Response)
      }
      return Promise.resolve({
        ok: false,
        json: () => Promise.resolve(null),
      } as Response)
    })

    render(<ChatInterface sessionId="favorite-session" />)

    await user.click(screen.getByRole('button', { name: '生成志愿推荐' }))

    await waitFor(() => {
      expect(screen.getByRole('button', { name: '收藏 清华大学' })).toBeInTheDocument()
      expect(screen.getByText('已收藏 0 / 1 项')).toBeInTheDocument()
      expect(screen.getByTitle('清华大学')).toBeInTheDocument()
    })

    await user.click(screen.getByRole('button', { name: '收藏 清华大学' }))

    await waitFor(() => {
      expect(screen.getByText('已收藏 1 / 1 项')).toBeInTheDocument()
      expect(window.localStorage.getItem('recommendation-favorites:favorite-session')).toBe(
        JSON.stringify(['school:清华大学']),
      )
      expect(globalThis.fetch).toHaveBeenCalledWith(
        apiUrl('/api/session/favorite-session/favorites'),
        expect.objectContaining({
          method: 'PUT',
          body: JSON.stringify({ favorite_keys: ['school:清华大学'] }),
        }),
      )
    })
  })

  it('loads favorite recommendations from the session API', async () => {
    const user = userEvent.setup()
    const recommendResponse = {
      summary: '建议按冲稳保组合填报。',
      recommendations: [
        {
          school_name: '清华大学',
          reason: '学校实力强，方向匹配。',
          admission_probability: 0.75,
          match_score: 9,
          strategy: '稳',
          risk_points: ['热门专业竞争激烈'],
          alternatives: ['北京邮电大学'],
        },
      ],
      gradient_summary: { 稳: ['清华大学'] },
    }

    vi.spyOn(globalThis, 'fetch').mockImplementation((url) => {
      if (typeof url === 'string' && url.includes('/api/session/favorite-session/favorites')) {
        return Promise.resolve({
          ok: true,
          json: () => Promise.resolve({ favorite_keys: ['school:清华大学'] }),
        } as Response)
      }
      if (typeof url === 'string' && url.includes('/api/recommend')) {
        return Promise.resolve({
          ok: true,
          json: () => Promise.resolve(recommendResponse),
        } as Response)
      }
      return Promise.resolve({
        ok: false,
        json: () => Promise.resolve(null),
      } as Response)
    })

    render(<ChatInterface sessionId="favorite-session" />)

    await user.click(screen.getByRole('button', { name: '生成志愿推荐' }))

    await waitFor(() => {
      expect(screen.getByRole('button', { name: '取消收藏 清华大学' })).toBeInTheDocument()
      expect(screen.getByText('已收藏 1 / 1 项')).toBeInTheDocument()
    })
  })
})
