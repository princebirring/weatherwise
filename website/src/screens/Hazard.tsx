import { useState } from 'react'
import { api } from '../api'
import { chipsOf, groupStatus, iconOf, levelOf, shortDate, titleOf, whenOf, type HazardGroup } from '../hazards'
import { Icon, type IconName } from '../components/Icon'
import { Listen } from '../components/Listen'
import { Link } from '../router'
import { ErrorBox, Helplines, Loading, ScreenHeader } from '../components/Shell'
import { useAsync, type Async } from '../components/useAsync'
import { Week } from '../components/Week'
import { saved } from '../storage'
import { useGuidance, useLanguage } from '../text'
import type { AdviceItem, Detection, Guidance, Outlook, PlaceAndOutlook, SavedPlace } from '../types'

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

const list = (key: keyof typeof ICONS, items: AdviceItem[]): Card[] =>
  items.map((a, i) => ({ icon: ICONS[key][i] ?? 'check', label: a.who, text: a.what }))

/** The advice for a group, most urgent first: the work-heat level line, or sowing when that is the risk. */
// A long phone number in an advice line (e.g. the Kisan Call Centre, 1800-180-1551) becomes a call button.
const phoneIn = (text: string) => text.match(/\b1800[-\s]?\d{3}[-\s]?\d{4}\b|\b\d{3,5}[-\s]\d{3}[-\s]\d{4}\b/)?.[0] ?? null

function adviceFor(group: HazardGroup, detections: Detection[], g: Guidance): Card[] {
  if (group === 'heat') {
    const work = detections.find((d) => d.hazard === 'work_heat')
    const level = work ? g.work_heat?.[work.severity] : undefined
    const first: Card[] = level ? [{ icon: 'heat', label: '', text: level }] : []
    return [...first, ...list('heat', g.heat), { icon: 'alert', label: '', text: g.heatstroke, call108: true }]
  }
  if (group === 'dry') {
    const sowingFirst = detections[0]?.hazard === 'sowing_risk'
    const dry = list('dry_spell', g.dry_spell)
    const sowing = list('sowing', g.sowing)
    return sowingFirst ? [...sowing, ...dry] : [...dry, ...sowing]
  }
  return list('heavy_rain', g.heavy_rain)
}

/** One page per danger, in the order a family needs it: what is coming, what to do,
 *  how to prepare (floods), where to go, who to call. */
export function HazardPage({ group, place, data }: { group: HazardGroup; place: SavedPlace; data: Async<PlaceAndOutlook> }) {
  const { t } = useLanguage()
  const guidance = useGuidance()
  const header = <ScreenHeader back="/app" title={t(`group.${group}`)} />

  if (data.loading || !guidance) return <>{header}<main className="app-main"><Loading /></main></>
  if (data.error || !data.data) {
    return <>{header}<main className="app-main">{data.error && <ErrorBox error={data.error} retry={data.retry} />}</main></>
  }

  const { outlook } = data.data
  if (group === 'flood' && outlook.flood_guide.mode === 'urgent') {
    return <>{header}<main className="app-main"><UrgentFlood guidance={guidance} /><NearestPlaces place={place} kind="flood" /><Helplines /></main></>
  }

  const status = groupStatus(group, outlook)
  const danger = status.detections.length > 0
  const cards = adviceFor(group, status.detections, guidance)
  const statusLines = danger
    ? status.detections.map((d) => titleOf(d, t))
    : [status.missing ? t('row.missing') : t(`page.calm.${group}`)]
  const adviceTitle = danger ? t('page.whatNow') : t(`page.when.${group}`)

  return (
    <>
      {header}
      <main className="app-main">
        {danger
          ? status.detections.map((d, i) => <Warning key={`${d.hazard}-${d.first_day}`} d={d} outlook={outlook} place={place} main={i === 0} />)
          : (
            // A calm week is one quiet line, not a card that looks like an alert.
            <p className={`calm-line ${status.missing ? 'missing' : ''}`} role="status">
              <Icon name={status.missing ? 'alert' : 'check'} size={22} />
              <b>{statusLines[0]}</b>
            </p>
          )}

        <section className="stack" style={{ gap: 10 }} aria-labelledby="advice-heading">
          <div className="section-row">
            <h2 id="advice-heading" className="h-mid">{adviceTitle}</h2>
            <Listen round text={[...statusLines, adviceTitle, ...cards.map((c) => [c.label, c.text].filter(Boolean).join(': '))].join('. ')} />
          </div>
          {cards.map((c) => (
            <article key={c.text} className={`advice ${c.call108 ? 'warn' : ''}`}>
              <span className="advice-icon"><Icon name={c.icon} size={34} /></span>
              <span className="stack" style={{ gap: 2 }}>
                {c.label && <span className="advice-label">{c.label}</span>}
                <span className="advice-text">{c.text}</span>
                {c.call108 && <a href="tel:108" className="btn danger">{t('todo.call108')}</a>}
                {!c.call108 && phoneIn(c.text) && <a href={`tel:${phoneIn(c.text)!.replace(/\D/g, '')}`} className="btn secondary">{t('advice.call', phoneIn(c.text)!)}</a>}
              </span>
            </article>
          ))}
        </section>

        {/* The agents explain and fit the advice to the person; the level above stays the rules' call. */}
        <Link href={`/app/ask?q=${encodeURIComponent(t(`ask.q.${group}`))}`} className="btn secondary ask-about">
          <Icon name="chat" size={22} /> {t('ask.aboutThis')}
        </Link>

        <Week outlook={outlook} />
        {group === 'flood' && <FloodSteps place={place} mode={outlook.flood_guide.mode} guidance={guidance} />}
        {group !== 'dry' && <NearestPlaces place={place} kind={group === 'heat' ? 'heat' : 'flood'} />}
        {danger && <ShareButton d={status.detections[0]} place={place} />}
        {/* The red Help tab is always there; the numbers repeat here only when there is a warning. */}
        {danger && <Helplines />}
      </main>
    </>
  )
}

function Warning({ d, outlook, place, main }: { d: Detection; outlook: Outlook; place: SavedPlace; main: boolean }) {
  const { t, language } = useLanguage()
  const chips = chipsOf(d, outlook.days, place.name, t)
  if (!main) {
    return (
      <article className={`mini-warn lv-${levelOf(d)}`}>
        <Icon name={iconOf(d.hazard)} size={26} />
        <span><b>{titleOf(d, t)}</b><span>{whenOf(d, language)} · {chips.join(' · ')}</span></span>
      </article>
    )
  }
  return (
    <section className={`hero-card compact lv-${levelOf(d)}`} role="alert">
      <h2 className="row" style={{ justifyContent: 'center' }}><Icon name={iconOf(d.hazard)} size={40} />{titleOf(d, t)}</h2>
      <p className="when">{whenOf(d, language)}</p>
      <div className="chips">{chips.map((c) => <span key={c}>{c}</span>)}</div>
    </section>
  )
}

function ShareButton({ d, place }: { d: Detection; place: SavedPlace }) {
  const { t, language } = useLanguage()
  const text = `${titleOf(d, t)}: ${whenOf(d, language)}. ${place.name}. — ${t('brand.name')} ${window.location.origin}/app`
  const share = () => {
    if (navigator.share) void navigator.share({ text }).catch(() => {})
    else window.open(`https://wa.me/?text=${encodeURIComponent(text)}`, '_blank', 'noopener')
  }
  return <button type="button" className="btn big share" onClick={share}><Icon name="share" size={24} />{t('today.share')}</button>
}

/** Urgent mode: one short message and the calls (only on an official red alert or extremely heavy rain within a day). */
function UrgentFlood({ guidance }: { guidance: Guidance }) {
  const { t } = useLanguage()
  return (
    <section className="urgent" role="alert">
      <span className="kicker">{t('flood.urgentTag')}</span>
      <p className="big">{guidance.flood_urgent}</p>
      <Listen text={guidance.flood_urgent} />
      <p className="big-note">{t('flood.urgentWhy')}</p>
      <a href="tel:112" className="btn big">{t('flood.call112')}</a>
      <a href="tel:1077" className="btn big outline">{t('flood.call1077')}</a>
    </section>
  )
}

type Home = 'village' | 'city'

/** The NDMA household steps as a checklist: tick what is done; progress stays on this phone. */
function FloodSteps({ place, mode, guidance }: { place: SavedPlace; mode: Outlook['flood_guide']['mode']; guidance: Guidance }) {
  const { t } = useLanguage()
  const [home, setHome] = useState<Home>(saved.floodHome)
  const key = `${place.lat},${place.lon},${home}`
  const [done, setDone] = useState<{ key: string; steps: number[] }>(() => ({ key, steps: saved.floodDone(key) }))
  const ticked = new Set(done.key === key ? done.steps : saved.floodDone(key))
  const steps = home === 'city' ? guidance.flood_city : guidance.flood_village

  const toggle = (i: number) => {
    const next = new Set(ticked)
    if (next.has(i)) next.delete(i)
    else next.add(i)
    const list = [...next].sort((a, b) => a - b)
    saved.setFloodDone(key, list)
    setDone({ key, steps: list })
  }
  const pickHome = (h: Home) => { saved.setFloodHome(h); setHome(h) }

  // Open when the guide is in prepare mode; on a calm week, folded to one line with the progress.
  return (
    <details className="steps" open={mode === 'prepare'}>
      <summary className="steps-head">
        <h2 id="steps-heading" className="h-mid">{t('flood.stepsTitle')}</h2>
        <span className="steps-count">{t('flood.stepsDone', `${ticked.size} / ${steps.length}`)}</span>
      </summary>
      <div className="stack" style={{ gap: 10, marginTop: 10 }}>
      <p className="big-note">{mode === 'prepare' ? t('flood.prepareBody') : t('flood.calmBody')}</p>
      <div className="segmented" role="group" aria-label={t('flood.where')}>
        <button type="button" aria-pressed={home === 'village'} onClick={() => pickHome('village')}>{t('flood.village')}</button>
        <button type="button" aria-pressed={home === 'city'} onClick={() => pickHome('city')}>{t('flood.city')}</button>
      </div>
      <ol className="checklist">
        {steps.map((s, i) => (
          <li key={s}>
            <label className={ticked.has(i) ? 'done' : ''}>
              <input type="checkbox" checked={ticked.has(i)} onChange={() => toggle(i)} />
              <span>{s}</span>
            </label>
          </li>
        ))}
      </ol>
      {ticked.size === steps.length && <p className="card big-note" role="status"><b>{t('flood.allDone')}</b></p>}
      <p className="big-note"><b>{guidance.flood_always}</b></p>
      <p className="small">{t('flood.progress')}</p>
      </div>
    </details>
  )
}

/** The nearest checked cooling place (heat) or shelter (flood). Floods: names only, never a route. */
function NearestPlaces({ place, kind }: { place: SavedPlace; kind: 'heat' | 'flood' }) {
  const { t, language } = useLanguage()
  const guidance = useGuidance()
  const result = useAsync(() => api.shelters(place.lat, place.lon, kind), `${place.lat},${place.lon},${kind}`)
  const r = result.data
  const disaster = r?.helpline.disaster ?? '1077'

  return (
    <section className="stack" style={{ gap: 10 }} aria-labelledby="places-heading">
      <h2 id="places-heading" className="h-mid">{kind === 'heat' ? t('todo.findCooling') : t('flood.shelterNames')}</h2>
      {kind === 'flood' && guidance && <p className="alert-box blue big-note"><b>{guidance.flood_safety_line}</b></p>}
      {result.loading && <Loading label={t('state.loadingShelters')} />}
      {result.error && <ErrorBox error={result.error} retry={result.retry} />}
      {r && (
        <>
          {r.places.slice(0, 3).map((p) => (
            <article key={p.name} className="place-card">
              <div className="row">
                <span className="place-icon"><Icon name="home" size={30} /></span>
                <span className="stack" style={{ gap: 0 }}>
                  <b>{p.name}</b>
                  <span>{t('shelter.km', p.km)} · {t('shelter.checkedOn', shortDate(p.checked_on, language))}</span>
                </span>
              </div>
              <div className="pair">
                <a href={`tel:${p.contact || disaster}`} className="btn">{t('shelter.callFirst')}</a>
                {/* The server never sends a route for floods; this guard keeps it that way here too. */}
                {kind === 'heat' && p.directions_link && (
                  <a href={p.directions_link} target="_blank" rel="noopener noreferrer" className="btn secondary">{t('shelter.showWay')}</a>
                )}
              </div>
            </article>
          ))}
          {r.places.length === 0 && (
            <div className="card stack">
              <p className="big-note">{t(kind === 'heat' ? 'shelter.noneNearHeat' : 'shelter.noneNearFlood', Math.round(r.search_km))}</p>
              <a href={`tel:${disaster}`} className="btn">{t('flood.call1077')}</a>
            </div>
          )}
          {kind === 'flood' && <p className="big-note">{t('shelter.noRoute')}</p>}
          {r.stale_nearby > 0 && <p className="small">{t('shelter.stale', r.stale_nearby)}</p>}
          {r.health_facilities && r.health_facilities.length > 0 && (
            <section className="card stack" style={{ gap: 8 }}>
              <h3 className="h-mid">{t('shelter.healthTitle')}</h3>
              {r.health_facilities.map((h) => (
                <div key={h.name} className="row" style={{ justifyContent: 'space-between' }}>
                  <span>{h.name}</span><b style={{ flex: 'none' }}>{t('shelter.km', h.km)}</b>
                </div>
              ))}
              <span className="small">{t('shelter.healthNote')}</span>
            </section>
          )}
          {r.health_status === 'unavailable' && <p className="card big-note">{t('shelter.healthUnavailable')}</p>}
        </>
      )}
    </section>
  )
}
