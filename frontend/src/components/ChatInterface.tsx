import { useState, useRef, useEffect } from 'react'
import { useTranslation } from 'react-i18next'
import MessageBubble from './MessageBubble'
import SourcePanel from './SourcePanel'
import type { Message, ToolCall, UserProfile } from '../types'

interface ChatInterfaceProps {
  sessionId: string
  userProfile?: UserProfile | null
}

export default function ChatInterface({ sessionId, userProfile }: ChatInterfaceProps) {
  const { t } = useTranslation()
  const [messages, setMessages] = useState<Message[]>([])
  const [input, setInput] = useState('')
  const [isLoading, setIsLoading] = useState(false)
  const [profileSent, setProfileSent] = useState(false)
  const [lastSources, setLastSources] = useState<ToolCall[]>([])
  const [showSources, setShowSources] = useState(false)
  const messagesEndRef = useRef<HTMLDivElement>(null)
  const inputRef = useRef<HTMLTextAreaElement>(null)

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }

  useEffect(() => {
    scrollToBottom()
  }, [messages])

  useEffect(() => {
    if (!isLoading) {
      inputRef.current?.focus()
    }
  }, [isLoading])

  // 加载历史消息
  useEffect(() => {
    fetch(`/api/session/${sessionId}`)
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
        body.user_context = {
          分数: userProfile.score,
          省份: userProfile.province,
          科类: userProfile.subject,
          家庭条件: userProfile.familyCondition,
        }
        setProfileSent(true)
      }

      const response = await fetch('/api/chat', {
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

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleSubmit(e as unknown as React.FormEvent)
    }
  }

  return (
    <div className="flex flex-col lg:flex-row h-[calc(100vh-140px)] sm:h-[calc(100vh-100px)] gap-0 lg:gap-6">
      {/* 聊天区域 */}
      <div className="flex-1 flex flex-col border-2 border-ink dark:border-night-border bg-paper dark:bg-night-card min-h-0">
        {/* 消息头部 */}
        <div className="border-b-2 border-ink dark:border-night-border px-4 sm:px-6 py-3 bg-paper-dark/50 dark:bg-night/50 flex-shrink-0">
          <div className="flex items-center justify-between">
            <h2 className="font-serif font-bold text-ink dark:text-paper text-base sm:text-lg">{t('chat.title')}</h2>
            <div className="flex items-center gap-2 sm:gap-3">
              {messages.length > 0 && (
                <button
                  onClick={() => window.open(`/api/session/${sessionId}/export`, '_blank')}
                  className="text-xs font-mono text-ink-light dark:text-night-muted hover:text-ink dark:hover:text-paper
                             border border-ink/30 dark:border-night-border hover:border-ink dark:hover:border-gold
                             px-2 py-1 transition-colors"
                >
                  {t('chat.export')}
                </button>
              )}
              {/* 移动端数据来源切换 */}
              {lastSources.length > 0 && (
                <button
                  onClick={() => setShowSources(prev => !prev)}
                  className="lg:hidden text-xs font-mono text-ink-light dark:text-night-muted hover:text-ink dark:hover:text-paper
                             border border-ink/30 dark:border-night-border px-2 py-1 transition-colors"
                >
                  {t('sourcePanel.title')} ({lastSources.length})
                </button>
              )}
              <span className="text-xs font-mono text-ink-light dark:text-night-muted hidden sm:inline">{t('chat.liveConsult')}</span>
            </div>
          </div>
        </div>

        {/* Messages */}
        <div className="flex-1 overflow-y-auto p-3 sm:p-6 space-y-4 sm:space-y-6 overscroll-contain">
          {messages.length === 0 && (
            <div className="text-center py-10 sm:py-16">
              <div className="quote-mark mb-4">"</div>
              <p className="text-lg sm:text-xl font-serif text-ink dark:text-paper mb-2">
                {t('chat.welcomeTitle')}
              </p>
              <p className="text-sm text-ink-light dark:text-night-muted font-serif">
                {t('chat.welcomeDesc')}
              </p>
              <div className="rule-single mt-8 max-w-xs mx-auto" />
            </div>
          )}

          {messages.map(message => (
            <MessageBubble key={message.id} message={message} />
          ))}

          {isLoading && (
            <div className="flex items-center gap-3 py-4">
              <div className="w-8 h-8 bg-ink dark:bg-gold flex items-center justify-center flex-shrink-0">
                <span className="text-gold dark:text-ink font-bold text-sm font-serif">张</span>
              </div>
              <div className="flex items-center gap-2 text-ink-light dark:text-night-muted">
                <div className="flex space-x-1">
                  <div className="w-2 h-2 bg-ink-light dark:bg-night-muted rounded-full animate-bounce" />
                  <div className="w-2 h-2 bg-ink-light dark:bg-night-muted rounded-full animate-bounce [animation-delay:0.2s]" />
                  <div className="w-2 h-2 bg-ink-light dark:bg-night-muted rounded-full animate-bounce [animation-delay:0.4s]" />
                </div>
                <span className="text-sm font-serif">{t('chat.analyzing')}</span>
              </div>
            </div>
          )}

          <div ref={messagesEndRef} />
        </div>

        {/* Input Area - 读者来信投稿区 */}
        <form onSubmit={handleSubmit} className="border-t-2 border-ink dark:border-night-border p-3 sm:p-4 bg-paper-dark/30 dark:bg-night/30 flex-shrink-0">
          <div className="flex items-end gap-2 sm:gap-3">
            <div className="flex-1 min-w-0">
              <div className="text-xs text-ink-light dark:text-night-muted font-mono mb-1 sm:mb-2">{t('chat.readerLetter')}</div>
              <textarea
                ref={inputRef}
                value={input}
                onChange={e => setInput(e.target.value)}
                onKeyDown={handleKeyDown}
                placeholder={t('chat.inputPlaceholder')}
                className="w-full resize-none border-2 border-ink dark:border-night-border bg-paper dark:bg-night
                           px-3 sm:px-4 py-2 sm:py-3 font-serif text-ink dark:text-paper
                           placeholder:text-ink-light/50 dark:placeholder:text-night-muted/50
                           focus:outline-none focus:border-gold transition-colors"
                rows={2}
                disabled={isLoading}
              />
            </div>
            <button
              type="submit"
              disabled={!input.trim() || isLoading}
              className="px-4 sm:px-6 py-2 sm:py-3 bg-ink dark:bg-gold text-paper dark:text-ink
                         font-serif font-bold hover:bg-ink-light dark:hover:bg-gold/80
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
        bg-paper dark:bg-night lg:bg-transparent
      `}>
        {/* 移动端遮罩 */}
        {showSources && (
          <div
            className="lg:hidden absolute inset-0 bg-black/30"
            onClick={() => setShowSources(false)}
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
