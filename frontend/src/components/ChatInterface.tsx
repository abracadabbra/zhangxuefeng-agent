import { useState, useRef, useEffect } from 'react'
import MessageBubble from './MessageBubble'
import SourcePanel from './SourcePanel'
import type { Message, ToolCall } from '../types'

interface ChatInterfaceProps {
  sessionId: string
}

export default function ChatInterface({ sessionId }: ChatInterfaceProps) {
  const [messages, setMessages] = useState<Message[]>([])
  const [input, setInput] = useState('')
  const [isLoading, setIsLoading] = useState(false)
  // 独立维护数据来源状态，避免因 messages 变化导致闪烁
  const [lastSources, setLastSources] = useState<ToolCall[]>([])
  const messagesEndRef = useRef<HTMLDivElement>(null)
  const inputRef = useRef<HTMLTextAreaElement>(null)

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }

  useEffect(() => {
    scrollToBottom()
  }, [messages])

  // 加载完成后重新聚焦输入框
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
      const response = await fetch('/api/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          session_id: sessionId,
          message: userMessage.content,
          stream: true,
        }),
      })

      if (!response.ok) throw new Error('请求失败')

      const contentType = response.headers.get('content-type') || ''

      // 检查是否为 SSE 流式响应
      if (contentType.includes('text/event-stream')) {
        // SSE 流式处理
        const reader = response.body?.getReader()
        if (!reader) throw new Error('无法读取响应流')

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
                  // 追加到 sources（累积模式）
                  setLastSources(prev => [...prev, toolCall])
                  // 触发消息更新
                  setMessages(prev => {
                    const updated = [...prev]
                    const lastMsg = updated[updated.length - 1]
                    if (lastMsg.role === 'assistant' && lastMsg.toolCalls) {
                      lastMsg.toolCalls = [...assistantMessage.toolCalls!]
                    }
                    return updated
                  })
                } else if (data.type === 'tool_result') {
                  // 更新 assistantMessage 中的 toolCall
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
                  // 更新 sources 中对应的结果（追加模式）
                  setLastSources(prev => prev.map(tc =>
                    tc.name === data.name && !tc.result
                      ? { ...tc, result: data.result }
                      : tc
                  ))
                  // 触发消息更新
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
        // 普通 JSON 响应处理
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

        // 有 tool_calls 时追加到 sources（累积模式）
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
          content: '抱歉，发生了错误，请重试。',
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
    <div className="flex h-[calc(100vh-100px)] gap-6">
      {/* 聊天区域 - 占 2/3 */}
      <div className="flex-1 flex flex-col border-2 border-ink bg-paper">
        {/* 消息头部 */}
        <div className="border-b-2 border-ink px-6 py-3 bg-paper-dark/50">
          <div className="flex items-center justify-between">
            <h2 className="font-serif font-bold text-ink text-lg">专栏对话</h2>
            <div className="flex items-center gap-3">
              {messages.length > 0 && (
                <button
                  onClick={() => window.open(`/api/session/${sessionId}/export`, '_blank')}
                  className="text-xs font-mono text-ink-light hover:text-ink border border-ink/30 hover:border-ink px-2 py-1 transition-colors"
                >
                  导出
                </button>
              )}
              <span className="text-xs font-mono text-ink-light">实时咨询</span>
            </div>
          </div>
        </div>

        {/* Messages */}
        <div className="flex-1 overflow-y-auto p-6 space-y-6">
          {messages.length === 0 && (
            <div className="text-center py-16">
              <div className="quote-mark mb-4">"</div>
              <p className="text-xl font-serif text-ink mb-2">
                你好！我是张雪峰 AI 助手
              </p>
              <p className="text-sm text-ink-light font-serif">
                高考志愿填报、考研择校、职业规划，有什么问题尽管问我！
              </p>
              <div className="rule-single mt-8 max-w-xs mx-auto" />
            </div>
          )}

          {messages.map(message => (
            <MessageBubble key={message.id} message={message} />
          ))}

          {isLoading && (
            <div className="flex items-center gap-3 py-4">
              <div className="w-8 h-8 bg-ink flex items-center justify-center">
                <span className="text-gold font-bold text-sm font-serif">张</span>
              </div>
              <div className="flex items-center gap-2 text-ink-light">
                <div className="flex space-x-1">
                  <div className="w-2 h-2 bg-ink-light rounded-full animate-bounce" />
                  <div className="w-2 h-2 bg-ink-light rounded-full animate-bounce [animation-delay:0.2s]" />
                  <div className="w-2 h-2 bg-ink-light rounded-full animate-bounce [animation-delay:0.4s]" />
                </div>
                <span className="text-sm font-serif">正在分析数据...</span>
              </div>
            </div>
          )}

          <div ref={messagesEndRef} />
        </div>

        {/* Input Area - 读者来信投稿区 */}
        <form onSubmit={handleSubmit} className="border-t-2 border-ink p-4 bg-paper-dark/30">
          <div className="flex items-end gap-3">
            <div className="flex-1">
              <div className="text-xs text-ink-light font-mono mb-2">读者来信</div>
              <textarea
                ref={inputRef}
                value={input}
                onChange={e => setInput(e.target.value)}
                onKeyDown={handleKeyDown}
                placeholder="输入你的问题..."
                className="w-full resize-none border-2 border-ink bg-paper px-4 py-3 font-serif text-ink placeholder:text-ink-light/50 focus:outline-none focus:border-gold transition-colors"
                rows={2}
                disabled={isLoading}
              />
            </div>
            <button
              type="submit"
              disabled={!input.trim() || isLoading}
              className="px-6 py-3 bg-ink text-paper font-serif font-bold hover:bg-ink-light disabled:opacity-50 disabled:cursor-not-allowed transition-colors self-end"
            >
              发送
            </button>
          </div>
        </form>
      </div>

      {/* 数据来源面板 - 占 1/3，参考文献风格 */}
      <SourcePanel sources={lastSources} />
    </div>
  )
}
