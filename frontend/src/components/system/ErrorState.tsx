import type { ReactNode } from 'react'

type Props = {
  message: string
  hint?: string
  onRetry?: () => void
  centered?: boolean
  action?: ReactNode
}

export function ErrorState({ message, hint, onRetry, centered = true, action }: Props) {
  return (
    <div className={`state-container error${centered ? ' centered' : ''}`}>
      <span className="state-title">{message}</span>
      {hint && <p className="state-hint">{hint}</p>}
      {onRetry && (
        <button className="btn-ghost" type="button" onClick={onRetry}>
          Try again
        </button>
      )}
      {action}
    </div>
  )
}
