type Props = {
  label?: string
}

export function SectionDivider({ label }: Props) {
  return (
    <>
      <hr className="section-divider" />
      {label && <div className="section-divider-label">{label}</div>}
    </>
  )
}
