import type { Message } from '../types'

interface MessageBubbleProps {
  message: Message
}

export default function MessageBubble({ message }: MessageBubbleProps) {
  const isUser = message.role === 'user'

  return (
    <div className={`flex ${isUser ? 'justify-end' : 'justify-start'}`}>
      <div className={`flex max-w-[85%] ${isUser ? 'flex-row-reverse' : 'flex-row'} gap-3`}>
        {/* Avatar */}
        <div
          className={`w-10 h-10 flex items-center justify-center flex-shrink-0 ${
            isUser ? 'bg-gold' : 'bg-ink'
          }`}
        >
          <span className={`text-sm font-bold font-serif ${isUser ? 'text-ink' : 'text-gold'}`}>
            {isUser ? '读' : '张'}
          </span>
        </div>

        {/* Message Content */}
        <div
          className={`px-5 py-4 ${
            isUser
              ? 'bg-gold-light border-2 border-gold'
              : 'bg-paper border-2 border-ink shadow-warm'
          }`}
        >
          {/* AI 消息标题装饰 */}
          {!isUser && (
            <div className="flex items-center gap-2 mb-3 pb-2 border-b border-rule">
              <span className="quote-mark text-2xl leading-none">"</span>
              <span className="text-xs font-mono text-ink-light">专栏文章</span>
            </div>
          )}

          {/* 用户消息标题 */}
          {isUser && (
            <div className="text-xs font-mono text-ink-light mb-2">读者来信</div>
          )}

          {/* 消息内容 */}
          <div className={`whitespace-pre-wrap break-words font-serif leading-relaxed ${
            isUser ? 'text-ink' : 'text-ink'
          }`}>
            {message.content}
          </div>

          {/* Tool Calls */}
          {message.toolCalls && message.toolCalls.length > 0 && (
            <div className="mt-4 pt-3 border-t border-rule">
              <p className="text-xs font-mono text-ink-light mb-2">数据来源：</p>
              {message.toolCalls.map((tc, idx) => (
                <div key={idx} className="flex items-center gap-2 text-xs py-1">
                  <span className="w-5 h-5 bg-ink text-gold flex items-center justify-center font-mono text-[10px]">
                    {idx + 1}
                  </span>
                  <span className="font-mono text-ink-light">{tc.name}</span>
                  {tc.result && (
                    <span className="stamp text-[10px] py-0 px-1">已获取</span>
                  )}
                </div>
              ))}
            </div>
          )}

          {/* Timestamp */}
          <div className={`text-xs mt-3 pt-2 border-t border-rule font-mono ${
            isUser ? 'text-ink-light' : 'text-ink-light'
          }`}>
            {message.timestamp.toLocaleTimeString('zh-CN', {
              hour: '2-digit',
              minute: '2-digit',
            })}
          </div>
        </div>
      </div>
    </div>
  )
}
