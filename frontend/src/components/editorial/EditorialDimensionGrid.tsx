import { formatConfidence, humanizeValue } from './editorialFormat'

type Props = {
  article_type: string
  article_type_confidence: number
  bias_label: string
  bias_confidence: number
  tone_emotional: string
  tone_target: string
  opinionatedness: string
  sensationalism: string
  rhetorical_certainty: string
  compact?: boolean
}

const dimensionRows = (props: Props) => [
  ['Article type', `${humanizeValue(props.article_type)} · ${formatConfidence(props.article_type_confidence)}`],
  ['Bias read', `${humanizeValue(props.bias_label)} · ${formatConfidence(props.bias_confidence)}`],
  ['Emotional tone', humanizeValue(props.tone_emotional)],
  ['Tone target', humanizeValue(props.tone_target)],
  ['Opinionatedness', humanizeValue(props.opinionatedness)],
  ['Sensationalism', humanizeValue(props.sensationalism)],
  ['Rhetorical certainty', humanizeValue(props.rhetorical_certainty)],
] as const

export function EditorialDimensionGrid(props: Props) {
  return (
    <div className={`editorial-dimension-grid${props.compact ? ' compact' : ''}`}>
      {dimensionRows(props).map(([label, value]) => (
        <div key={label} className="editorial-dimension-item">
          <span className="editorial-dimension-label">{label}</span>
          <span className="editorial-dimension-value">{value}</span>
        </div>
      ))}
    </div>
  )
}
