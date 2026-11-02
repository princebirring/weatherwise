import { Icon } from '../../components/Icon'
import { useLanguage } from '../../text'
import { BEST_LEAD, countOf, SCORECARD, type ScoreRow } from './results'

const MAX_DAYS = BEST_LEAD.days ?? 9

/** Every replayed disaster, one row each: a bar as long as the warning, and the misses in plain sight. */
export function Scorecard() {
  const { t } = useLanguage()
  const sums: [string, string][] = [
    ['ahead', t('site.sumAhead', countOf('ahead'))],
    ['partly', t('site.sumPartly', countOf('partly'))],
    ['conditions', t('site.sumConditions', countOf('conditions'))],
    ['missed', t('site.sumMissed', countOf('missed'))],
  ]
  return (
    <div className="score">
      <ul className="score-sums">
        {sums.map(([kind, text]) => <li key={kind} className={`o-${kind}`}><i />{text}</li>)}
      </ul>
      <ol className="score-rows">
        {SCORECARD.map((r) => <Row key={r.id} r={r} />)}
      </ol>
    </div>
  )
}

function Row({ r }: { r: ScoreRow }) {
  const { t, language } = useLanguage()
  const result = r.outcome === 'ahead' ? t('site.aheadDays', r.days ?? 0)
    : r.outcome === 'partly' ? t('site.partly', r.days ?? 0)
      : r.outcome === 'conditions' ? t('site.conditions') : t('site.missed')
  const share = r.days ? (r.days / MAX_DAYS) * 100 : 0
  return (
    <li className={`score-row o-${r.outcome}`}>
      <span className={`score-kind k-${r.kind}`} title={t(r.kind === 'heat' ? 'site.kindHeat' : 'site.kindFlood')}>
        <Icon name={r.kind === 'heat' ? 'heat' : 'waves'} size={20} label={t(r.kind === 'heat' ? 'site.kindHeat' : 'site.kindFlood')} />
      </span>
      <b className="score-title">{r.titles[language]}</b>
      <span className="score-bar" aria-hidden="true"><i style={{ width: `${share}%` }} /></span>
      <span className="score-result">{result}</span>
    </li>
  )
}
