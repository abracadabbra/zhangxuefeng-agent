import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import ChatInterface from '../ChatInterface'

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

describe('ChatInterface', () => {
  beforeEach(() => {
    vi.restoreAllMocks()
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
      expect(globalThis.fetch).toHaveBeenCalledWith('/api/session/test-session')
    })

    await waitFor(() => {
      expect(screen.getByText('你好')).toBeInTheDocument()
      expect(screen.getByText('你好！有什么可以帮你的？')).toBeInTheDocument()
    })
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

    vi.spyOn(globalThis, 'fetch').mockResolvedValue({
      ok: true,
      headers: new Headers({ 'content-type': 'text/event-stream' }),
      body: stream,
    } as Response)

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
        '/api/chat',
        expect.objectContaining({ method: 'POST' }),
      )
    })
  })

  it('does not send empty messages', async () => {
    const user = userEvent.setup()
    render(<ChatInterface sessionId="test-session" />)

    const sendButton = screen.getByRole('button', { name: /chat\.send/i })
    await user.click(sendButton)

    // Only the initial fetch for session history should have been called
    expect(globalThis.fetch).toHaveBeenCalledTimes(1)
    expect(globalThis.fetch).toHaveBeenCalledWith('/api/session/test-session')
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
    const stream = new ReadableStream({
      start(controller) {
        controller.enqueue(encoder.encode('data: {"type":"text","content":"ok"}\n\n'))
        controller.close()
      },
    })

    vi.spyOn(globalThis, 'fetch').mockImplementation((url, init) => {
      if (typeof url === 'string' && url.includes('/api/session')) {
        return Promise.resolve({ ok: false, json: () => Promise.resolve(null) } as Response)
      }
      return Promise.resolve({
        ok: true,
        headers: new Headers({ 'content-type': 'text/event-stream' }),
        body: stream,
      } as Response)
    })

    render(<ChatInterface sessionId="test-session" userProfile={userProfile} />)

    const input = screen.getByLabelText('chat.inputPlaceholder')
    await user.type(input, '你好')

    const sendButton = screen.getByRole('button', { name: /chat\.send/i })
    await user.click(sendButton)

    await waitFor(() => {
      const chatCall = (globalThis.fetch as ReturnType<typeof vi.fn>).mock.calls.find(
        (call: unknown[]) => typeof call[0] === 'string' && call[0] === '/api/chat',
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
})
