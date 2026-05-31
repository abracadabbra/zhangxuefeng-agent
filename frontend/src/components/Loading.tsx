import { useTranslation } from 'react-i18next'

interface LoadingProps {
  message?: string
  fullScreen?: boolean
}

export default function Loading({ message, fullScreen = false }: LoadingProps) {
  const { t } = useTranslation()

  const content = (
    <div
      role="status"
      aria-label={t('loading.aria', { defaultValue: '正在加载' })}
      className="flex flex-col items-center justify-center gap-4 py-12"
    >
      {/* Newspaper-style loading animation */}
      <div className="relative w-16 h-16">
        <div className="absolute inset-0 border-2 border-ink dark:border-night-border" />
        <div className="absolute inset-1 border border-ink/40 dark:border-night-border/40 animate-pulse" />
        <div className="absolute inset-0 flex items-center justify-center">
          <span className="text-2xl font-serif font-bold text-ink dark:text-paper animate-pulse">
            张
          </span>
        </div>
      </div>

      <div className="flex flex-col items-center gap-1">
        <p className="text-sm font-serif text-ink dark:text-paper tracking-wider">
          {message || t('loading.default', { defaultValue: '正在准备...' })}
        </p>
        <div className="flex gap-1">
          <span className="w-1.5 h-1.5 bg-ink dark:bg-paper rounded-full animate-bounce [animation-delay:0ms]" />
          <span className="w-1.5 h-1.5 bg-ink dark:bg-paper rounded-full animate-bounce [animation-delay:150ms]" />
          <span className="w-1.5 h-1.5 bg-ink dark:bg-paper rounded-full animate-bounce [animation-delay:300ms]" />
        </div>
      </div>
    </div>
  )

  if (fullScreen) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-paper dark:bg-night paper-texture">
        {content}
      </div>
    )
  }

  return content
}
