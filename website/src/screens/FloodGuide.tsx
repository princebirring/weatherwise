import { useState } from 'react'
import { Icon } from '../components/Icon'
import { ErrorBox, Helplines, Loading } from '../components/Shell'
import type { Async } from '../components/useAsync'
import { Link } from '../router'
import { saved } from '../storage'
import { useGuidance, useLanguage } from '../text'
import type { PlaceAndOutlook, SavedPlace } from '../types'

type Home = 'village' | 'city'

/** Part 3: prepare mode one step at a time; urgent mode one short message. The mode comes
 *  from hazard_outlook (urgent only on an official red alert or extremely heavy rain within a day). */
export function FloodGuide({ place, data }: { place: SavedPlace; data: Async<PlaceAndOutlook> }) {
  const { t } = useLanguage()
  const guidance = useGuidance()
  const [home, setHome] = useState<Home>(() => (saved.floodStep('home') === 1 ? 'city' : 'village'))
  const key = `${place.lat},${place.lon},${home}`
  const [stepState, setStepState] = useState<{ key: string; step: number }>(() => ({ key, step: saved.floodStep(key) }))
  const step = stepState.key === key ? stepState.step : saved.floodStep(key)

  if (data.loading || !guidance) return <main className="app-main"><Loading /></main>
  if (data.error || !data.data) return <main className="app-main">{data.error && <ErrorBox error={data.error} retry={data.retry} />}</main>

  const mode = data.data.outlook.flood_guide.mode
  if (mode === 'urgent') {
    return (
      <main className="app-main">
        <section className="urgent" role="alert">
          <span className="kicker">{t('flood.urgentTag')}</span>
          <p className="big">{guidance.flood_urgent}</p>
          <p style={{ fontSize: 16 }}>{t('flood.urgentWhy')}</p>
          <a href="tel:112" className="btn big">{t('flood.call112')}</a>
          <a href="tel:1077" className="btn big outline">{t('flood.call1077')}</a>
          <Link href="/app/shelter?kind=flood" className="btn big outline">{t('flood.shelterNames')}</Link>
        </section>
      </main>
    )
  }

  const steps = home === 'city' ? guidance.flood_city : guidance.flood_village
  const finished = step >= steps.length
  const go = (next: number) => {
    const clamped = Math.max(0, Math.min(next, steps.length))
    saved.setFloodStep(key, clamped)
    setStepState({ key, step: clamped })
  }
  const pickHome = (h: Home) => {
    saved.setFloodStep('home', h === 'city' ? 1 : 0)
    setHome(h)
  }

  return (
    <main className="app-main">
      <section className={`hero-card ${mode === 'prepare' ? 'lv-flood' : 'lv-missing'}`} style={{ padding: 18 }}>
        <h1 style={{ fontSize: 24 }}>{mode === 'prepare' ? t('flood.prepareTitle') : t('flood.calmTitle')}</h1>
        <p>{mode === 'prepare' ? t('flood.prepareBody') : t('flood.calmBody')}</p>
      </section>

      <div className="segmented" role="group" aria-label={t('flood.where')}>
        <button type="button" aria-pressed={home === 'village'} onClick={() => pickHome('village')}>{t('flood.village')}</button>
        <button type="button" aria-pressed={home === 'city'} onClick={() => pickHome('city')}>{t('flood.city')}</button>
      </div>

      <div className="dots" aria-hidden="true">{steps.map((s, i) => <i key={s} className={i < step || finished ? 'on' : i === step ? 'now' : ''} />)}</div>

      <section className="todo-card" aria-live="polite">
        <div className={`todo-icon ${finished ? '' : ''}`}><Icon name={finished ? 'check' : 'waves'} size={64} /></div>
        <p className="todo-text">{finished ? t('flood.allDone') : steps[step]}</p>
        <p className="big-note" style={{ marginTop: 'auto' }}>{guidance.flood_always}</p>
      </section>

      {finished ? (
        <button type="button" className="btn big secondary" onClick={() => go(0)}>{t('flood.startAgain')}</button>
      ) : (
        <div className="pair">
          <button type="button" className="btn big secondary" onClick={() => go(step - 1)} disabled={step === 0}>{t('shell.back')}</button>
          <button type="button" className="btn big" onClick={() => go(step + 1)}>{step === steps.length - 1 ? t('todo.done') : t('todo.next')}</button>
        </div>
      )}
      <Link href="/app/shelter?kind=flood" className="btn big secondary">{t('flood.shelterNames')}</Link>
      <p className="fine">{t('flood.progress')}</p>
      <Helplines />
    </main>
  )
}
