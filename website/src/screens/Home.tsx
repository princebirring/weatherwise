import { useEffect } from 'react'
import { chipsOf, dayIcon, dayLevel, iconOf, levelOf, shortDate, sortDetections, titleOf, weekday, whenOf } from '../hazards'
import { Icon } from '../components/Icon'
import { ErrorBox, Loading } from '../components/Shell'
import type { Async } from '../components/useAsync'
import { Link } from '../router'
import { useLanguage } from '../text'
import type { Detection, Outlook, PlaceAndOutlook, SavedPlace, Status } from '../types'

/** Today: one big answer to "is it safe, and what do I do?" */
export function Home({ place, data, status, onPlace }: {
  place: SavedPlace; data: Async<PlaceAndOutlook>; status: Status | null; onPlace: (p: SavedPlace) => void
}) {
  const { t, language } = useLanguage()

  // "Use my location" saves a bare point; name it once the place is resolved.
  const facts = data.data?.place
  useEffect(() => {
    if (facts && !place.label) {
      onPlace({ ...place, name: facts.name || place.name, label: [facts.admin.district, facts.admin.state].filter(Boolean).join(', ') })
    }
  }, [facts, place, onPlace])

  if (data.loading) return <main className="app-main"><Loading /></main>
  if (data.error || !data.data) return <main className="app-main">{data.error && <ErrorBox error={data.error} retry={data.retry} />}</main>

  const { outlook } = data.data
  const detections = sortDetections(outlook.detections)
  const top = detections[0]
  const floodMode = outlook.flood_guide.mode

  return (
    <main className="app-main">
      {top ? <DangerCard d={top} outlook={outlook} place={place} /> : <CalmCard outlook={outlook} />}

      {floodMode && (
        <Link href="/app/flood" className={`btn big ${floodMode === 'urgent' ? 'danger' : 'flood'}`}>
          <Icon name="waves" size={28} />{floodMode === 'urgent' ? t('flood.urgentTag') : t('today.floodGuide')}
        </Link>
      )}

      {detections.length > 1 && (
        <section className="stack" style={{ gap: 8 }}>
          <h2 className="h-mid">{t('today.alsoComing')}</h2>
          {detections.slice(1).map((d, i) => (
            <Link key={`${d.hazard}-${d.first_day}-${i}`} href={`/app/todo/${i + 1}`} className={`mini-warn lv-${levelOf(d)}`}>
              <Icon name={iconOf(d.hazard)} size={26} />
              <span><b>{titleOf(d, t)}</b><span>{whenOf(d, language)}</span></span>
              <Icon name="send" size={22} />
            </Link>
          ))}
        </section>
      )}

      <Week outlook={outlook} />

      {status?.agents_ready && (
        <Link href="/app/ask" className="btn big secondary"><Icon name="chat" size={26} />{t('today.ask')}</Link>
      )}
      <p className="small" style={{ textAlign: 'center', fontSize: 15 }}>{t('today.checked', shortDate(outlook.issue_date, language))}</p>
    </main>
  )
}

function CalmCard({ outlook }: { outlook: Outlook }) {
  const { t } = useLanguage()
  if (outlook.data_missing.length > 0) {
    return (
      <section className="hero-card lv-missing" role="status">
        <div className="hero-icon"><Icon name="alert" size={56} /></div>
        <h1>{t('today.missingTitle')}</h1>
        <p>{t('today.missingBody')}</p>
      </section>
    )
  }
  return (
    <section className="hero-card lv-green" role="status">
      <div className="hero-icon"><Icon name="check" size={60} /></div>
      <h1>{t('today.safeTitle')}</h1>
      <p>{t('today.safeBody')}</p>
    </section>
  )
}

function DangerCard({ d, outlook, place }: { d: Detection; outlook: Outlook; place: SavedPlace }) {
  const { t, language } = useLanguage()
  const title = titleOf(d, t)
  const when = whenOf(d, language)
  const shareText = `${title}: ${when}. ${place.name}. — ${t('brand.name')} ${window.location.origin}/app`
  const share = () => {
    if (navigator.share) void navigator.share({ text: shareText }).catch(() => {})
    else window.open(`https://wa.me/?text=${encodeURIComponent(shareText)}`, '_blank', 'noopener')
  }
  return (
    <>
      <section className={`hero-card lv-${levelOf(d)}`} role="alert">
        <div className="hero-icon"><Icon name={iconOf(d.hazard)} size={56} /></div>
        <h1>{title}</h1>
        <p className="when">{when}</p>
        <div className="chips">{chipsOf(d, outlook.days, place.name, t).map((c) => <span key={c}>{c}</span>)}</div>
      </section>
      <Link href="/app/todo/0" className="btn big">{t('today.whatToDo')}</Link>
      <button type="button" className="btn big share" onClick={share}><Icon name="share" size={24} />{t('today.share')}</button>
    </>
  )
}

function Week({ outlook }: { outlook: Outlook }) {
  const { t, language } = useLanguage()
  return (
    <section aria-label={t('today.week')}>
      <ol className="week">
        {outlook.days.map((d) => {
          const level = dayLevel(d)
          return (
            <li key={d.day} className={level ?? ''} aria-label={`${weekday(d.day, language)}: ${d.tmax_c === null ? '–' : Math.round(d.tmax_c)}°, ${level ? t('today.danger') : t('today.noDanger')}`}>
              <span className="wd">{weekday(d.day, language)}</span>
              <Icon name={dayIcon(d)} size={26} />
              <b>{d.tmax_c === null ? '–' : `${Math.round(d.tmax_c)}°`}</b>
            </li>
          )
        })}
      </ol>
    </section>
  )
}
