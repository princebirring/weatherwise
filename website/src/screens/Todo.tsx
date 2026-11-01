import { useState } from 'react'
import { FLOOD_HAZARDS, HEAT_HAZARDS, sortDetections, titleOf } from '../hazards'
import { Icon, type IconName } from '../components/Icon'
import { Listen } from '../components/Listen'
import { ErrorBox, Loading, ScreenHeader } from '../components/Shell'
import type { Async } from '../components/useAsync'
import { Link, navigate } from '../router'
import { useGuidance, useLanguage } from '../text'
import type { AdviceItem, Detection, Guidance, PlaceAndOutlook } from '../types'

interface Card {
  icon: IconName
  label: string
  text: string
  call108?: boolean
}

// Pictures for each advice list, in the order of the items in rules/languages/*.toml.
const ICONS: Record<string, IconName[]> = {
  heat: ['clock', 'home', 'cow'],
  dry_spell: ['drop', 'plant', 'cow'],
  sowing: ['plant', 'phone'],
  heavy_rain: ['waves', 'alert'],
}

function cardsFor(d: Detection, g: Guidance): Card[] {
  const list = (key: keyof typeof ICONS, items: AdviceItem[]) =>
    items.map((a, i) => ({ icon: ICONS[key][i] ?? 'check', label: a.who, text: a.what }))
  const hazard = d.hazard
  if (HEAT_HAZARDS.has(hazard)) {
    const level = hazard === 'work_heat' ? g.work_heat?.[d.severity] : undefined
    const first: Card[] = level ? [{ icon: 'heat', label: '', text: level }] : []
    return [...first, ...list('heat', g.heat), { icon: 'alert', label: '', text: g.heatstroke, call108: true }]
  }
  if (hazard === 'dry_spell') return list('dry_spell', g.dry_spell)
  if (hazard === 'sowing_risk') return list('sowing', g.sowing)
  return list('heavy_rain', g.heavy_rain)
}

/** What to do about one warning: one big card at a time, with Back / Next. */
export function Todo({ index, data }: { index: number; data: Async<PlaceAndOutlook> }) {
  const { t } = useLanguage()
  const guidance = useGuidance()
  const [step, setStep] = useState(0)

  if (data.loading || !guidance) return <main className="app-main"><Loading /></main>
  if (data.error || !data.data) return <main className="app-main">{data.error && <ErrorBox error={data.error} retry={data.retry} />}</main>

  const d = sortDetections(data.data.outlook.detections)[index]
  if (!d) {
    return (
      <>
        <ScreenHeader back="/app" title={t('tabs.today')} />
        <main className="app-main"><p className="card big-note">{t('todo.notFound')}</p></main>
      </>
    )
  }
  const cards = cardsFor(d, guidance)
  const card = cards[Math.min(step, cards.length - 1)]
  const last = step >= cards.length - 1

  return (
    <>
      <ScreenHeader back="/app" title={t('todo.title', titleOf(d, t))} />
      <main className="app-main">
        <div className="dots" aria-hidden="true">{cards.map((c, i) => <i key={c.text} className={i <= step ? 'on' : ''} />)}</div>
        <section className="todo-card" aria-live="polite">
          <div className={`todo-icon ${card.call108 ? 'warn' : ''}`}><Icon name={card.icon} size={72} /></div>
          {card.label && <p className="todo-label">{card.label}</p>}
          <p className="todo-text">{card.text}</p>
          <Listen text={[card.label, card.text].filter(Boolean).join('. ')} />
          {card.call108 && <a href="tel:108" className="btn big danger">{t('todo.call108')}</a>}
          {last && HEAT_HAZARDS.has(d.hazard) && <Link href="/app/shelter?kind=heat" className="btn big secondary">{t('todo.findCooling')}</Link>}
          {last && FLOOD_HAZARDS.has(d.hazard) && <Link href="/app/flood" className="btn big flood">{t('today.floodGuide')}</Link>}
        </section>
        <div className="pair">
          <button type="button" className="btn big secondary" onClick={() => setStep(step - 1)} disabled={step === 0}>{t('shell.back')}</button>
          <button type="button" className="btn big" onClick={() => (last ? navigate('/app') : setStep(step + 1))}>
            {last ? t('todo.done') : t('todo.next')}
          </button>
        </div>
      </main>
    </>
  )
}
