import type { ReactNode } from 'react'

type Props = {
  title: string
  hint?: string
  action?: ReactNode
  centered?: boolean
}

export function EmptyState({ title, hint, action, centered = true }: Props) {
  return (
    <div className={`state-container${centered ? ' centered' : ''}`}>
      <span className="state-title">{title}</span>
      {hint && <p className="state-hint">{hint}</p>}
      {action}
    </div>
  )
}
