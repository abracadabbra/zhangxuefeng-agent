import { useTranslation } from 'react-i18next'
import type { Message } from '../types'

interface MessageBubbleProps {
  message: Message
}

export default function MessageBubble({ message }: MessageBubbleProps) {
  const { t } = useTranslation()
  const isUser = message.role === 'user'

  return (
    <div className={`flex ${isUser ? 'justify-end' : 'justify-start'}`}>
      <div className={`flex max-w-[85%] sm:max-w-[80%] ${isUser ? 'flex-row-reverse' : 'flex-row'} gap-2 sm:gap-3`}>
        {/* Avatar */}
        <div
          className={`w-8 h-8 sm:w-10 sm:h-10 flex items-center justify-center flex-shrink-0 ${
            isUser ? 'bg-gold' : 'bg-ink'
          }`}
        >
          <span className={`text-xs sm:text-sm font-bold font-serif ${isUser ? 'text-ink' : 'text-gold'}`}>
            {isUser ? '读' : '张'}
          </span>
        </div>

        {/* Message Content */}
        <div
          className={`px-4 sm:px-5 py-3 sm:py-4 ${
            isUser
              ? 'bg-gold-light/20 border-2 border-gold'
              : 'bg-paper-card border-2 border-ink shadow-warm'
          }`}
        >
          {/* AI 消息标题装饰 */}
          {!isUser && (
            <div className="flex items-center gap-2 mb-2 sm:mb-3 pb-2 border-b border-rule">
              <span className="quote-mark text-xl sm:text-2xl leading-none">"</span>
              <span className="text-xs font-mono text-ink-light">{t('messageBubble.columnArticle')}</span>
            </div>
          )}

          {/* 用户消息标题 */}
          {isUser && (
            <div className="text-xs font-mono text-ink-light mb-1 sm:mb-2">{t('messageBubble.readerLetter')}</div>
          )}

          {/* 消息内容 */}
          <div className={`whitespace-pre-wrap break-words font-serif leading-relaxed text-sm sm:text-base ${
            isUser ? 'text-ink' : 'text-ink'
          }`}>
            {message.content}
          </div>

          {/* Tool Calls */}
          {message.toolCalls && message.toolCalls.length > 0 && (
            <div className="mt-3 sm:mt-4 pt-3 border-t border-rule">
              <p className="text-xs font-mono text-ink-light mb-2">{t('messageBubble.dataSources')}</p>
              {message.toolCalls.map((tc, idx) => (
                <div key={idx} className="flex items-center gap-2 text-xs py-1">
                  <span className="w-5 h-5 bg-ink text-gold flex items-center justify-center font-mono text-[10px]">
                    {idx + 1}
                  </span>
                  <span className="font-mono text-ink-light">{tc.name}</span>
                  {tc.result && (
                    <span className="stamp text-[10px] py-0 px-1">{t('messageBubble.fetched')}</span>
                  )}
                </div>
              ))}
            </div>
          )}

          {/* Timestamp */}
          <div className={`text-xs mt-2 sm:mt-3 pt-2 border-t border-rule font-mono ${
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
