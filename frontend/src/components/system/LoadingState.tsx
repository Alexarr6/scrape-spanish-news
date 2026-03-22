type Props = {
  label?: string
  hint?: string
  centered?: boolean
}

export function LoadingState({ label = 'Loading…', hint, centered = true }: Props) {
  return (
    <div className={`state-container${centered ? ' centered' : ''}`}>
      <div className="state-loading-indicator" aria-hidden="true" />
      <span className="state-title">{label}</span>
      {hint && <p className="state-hint">{hint}</p>}
    </div>
  )
}
