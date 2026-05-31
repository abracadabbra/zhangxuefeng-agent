interface SkeletonProps {
  variant?: 'text' | 'avatar' | 'card'
  width?: string | number
  height?: string | number
  lines?: number
  className?: string
}

export default function Skeleton({
  variant = 'text',
  width,
  height,
  lines = 1,
  className = '',
}: SkeletonProps) {
  const baseClass = 'bg-ink/10-muted/20 animate-pulse rounded'

  if (variant === 'avatar') {
    return (
      <div
        aria-hidden="true"
        className={`${baseClass} flex-shrink-0 ${className}`}
        style={{
          width: width ?? 40,
          height: height ?? 40,
          borderRadius: 0,
        }}
      />
    )
  }

  if (variant === 'card') {
    return (
      <div
        aria-hidden="true"
        className={`${baseClass} ${className}`}
        style={{ width: width ?? '100%', height: height ?? 120, borderRadius: 0 }}
      />
    )
  }

  // text variant: render N lines, last line shorter
  return (
    <div aria-hidden="true" className={`space-y-2 ${className}`}>
      {Array.from({ length: lines }, (_, i) => (
        <div
          key={i}
          className={`${baseClass} h-4`}
          style={{ width: i === lines - 1 ? '60%' : (width ?? '100%') }}
        />
      ))}
    </div>
  )
}

/** Full chat message skeleton for the loading state */
export function MessageSkeleton({ isUser = false }: { isUser?: boolean }) {
  return (
    <div className={`flex ${isUser ? 'justify-end' : 'justify-start'}`}>
      <div className={`flex max-w-[85%] sm:max-w-[80%] ${isUser ? 'flex-row-reverse' : 'flex-row'} gap-2 sm:gap-3`}>
        <Skeleton variant="avatar" width={32} height={32} className="sm:!w-10 sm:!h-10" />
        <div className="px-4 sm:px-5 py-3 sm:py-4 border-2 border-ink/10/30 bg-paper">
          <Skeleton variant="text" lines={isUser ? 2 : 4} />
        </div>
      </div>
    </div>
  )
}
