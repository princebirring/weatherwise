import { useEffect } from 'react'
import { chipsOf, dayIcon, dayLevel, iconOf, levelOf, LOCALES, officialTitle, shortDate, sortDetections, titleOf, weekday, whenOf } from '../hazards'
import { Icon } from '../components/Icon'
import { Listen } from '../components/Listen'
import { ErrorBox, Loading } from '../components/Shell'
import type { Async } from '../components/useAsync'
import { Link } from '../router'
import { useLanguage } from '../text'
import type { TextKey } from '../text/en'
import type { Detection, OfficialAlerts, Outlook, PlaceAndOutlook, SavedPlace, Status } from '../types'

/** Today: one big answer to "is it safe, and what do I do?" */
export function Home({ place, data, official, status, onPlace }: {
  place: SavedPlace; data: Async<PlaceAndOutlook>; official: Async<OfficialAlerts>; status: Status | null
  onPlace: (p: SavedPlace) => void
}) {
  const { t, language } = useLanguage()

  // "Use my location" saves a bare point; name it once the place is resolved.
  const facts = data.data?.place
  useEffect(() => {
    if (facts && !place.label) {
      onPlace({ ...place, name: facts.name || place.name, label: [facts.admin.district, facts.admin.state].filter(Boolean).join(', ') })
    }
  }, [facts, place, onPlace])

  // Official warnings come first, and do not wait for our forecast (it may be slow or down).
  const officialNow: OfficialAlerts | null = official.data
    ?? (official.error ? { status: 'unavailable', alerts: [], source: null } : data.data?.outlook.official ?? null)
  const timezone = data.data?.place.timezone
  const officialSection = officialNow && <OfficialWarnings official={officialNow} timezone={timezone} />

  if (data.loading) return <main className="app-main">{officialSection}<Loading /></main>
  if (data.error || !data.data) {
    return <main className="app-main">{officialSection}{data.error && <ErrorBox error={data.error} retry={data.retry} />}</main>
  }

  const { outlook } = data.data
  const detections = sortDetections(outlook.detections)
  const top = detections[0]
  const floodMode = outlook.flood_guide.mode

  return (
    <main className="app-main">
      {/* Official warnings always come first; our own checks follow. */}
      {officialSection}
      {top
        ? <DangerCard d={top} outlook={outlook} place={place} />
        : <CalmCard outlook={outlook} afterOfficial={(officialNow?.alerts.length ?? 0) > 0} />}

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

function CalmCard({ outlook, afterOfficial }: { outlook: Outlook; afterOfficial: boolean }) {
  const { t } = useLanguage()
  if (outlook.data_missing.length > 0) {
    return (
      <>
        <section className="hero-card lv-missing" role="status">
          <div className="hero-icon"><Icon name="alert" size={56} /></div>
          <h1>{t('today.missingTitle')}</h1>
          <p>{t('today.missingBody')}</p>
        </section>
        <Listen text={`${t('today.missingTitle')}. ${t('today.missingBody')}`} />
      </>
    )
  }
  const title = afterOfficial ? t('today.nothingMore') : t('today.safeTitle')
  return (
    <>
      <section className={`hero-card lv-calm ${afterOfficial ? 'quiet' : ''}`} role="status">
        {!afterOfficial && <div className="hero-icon"><Icon name="shield" size={56} /></div>}
        <h1>{title}</h1>
        <p>{t('today.safeBody')}</p>
      </section>
      {!afterOfficial && <Listen text={`${title}. ${t('today.safeBody')}`} />}
    </>
  )
}

/** Official warnings in force for this place, most serious first, in the person's language. */
function OfficialWarnings({ official, timezone }: { official: OfficialAlerts; timezone?: string }) {
  const { t, language } = useLanguage()
  if (official.status === 'unavailable') {
    return <p className="official-note warn" role="status"><Icon name="alert" size={22} />{t('official.unavailable')}</p>
  }
  if (official.status !== 'ok') return null
  if (official.alerts.length === 0) {
    return <p className="official-note" role="status"><Icon name="shield" size={22} />{t('official.none')}</p>
  }
  const until = (iso: string) => new Intl.DateTimeFormat(LOCALES[language],
    { weekday: 'short', hour: 'numeric', minute: '2-digit', timeZone: timezone }).format(new Date(iso))
  const languageName = (code: string) => {
    try { return new Intl.DisplayNames([LOCALES[language]], { type: 'language' }).of(code) ?? code } catch { return code }
  }
  return (
    <section className="stack" style={{ gap: 10 }}>
      {official.alerts.map((a) => {
        const own = a.translations[language]
        const translated = !!own && a.language !== language
        return (
          <article key={a.id} className={`official lv-${a.level === 'green' ? 'calm' : a.level}`} role="alert">
            <span className="kicker">{t('official.kicker', a.source)}</span>
            <h1 className="official-title"><Icon name="shield" size={28} />{officialTitle(a.event, language, t)}</h1>
            <div className="chips">
              <span>{t(`official.level.${a.level}` as TextKey)}</span>
              <span>{t('official.until', until(a.ends))}</span>
            </div>
            <p className="official-message" lang={own ? language : a.language}>{own ?? a.message}</p>
            <Listen text={own ?? a.message} lang={own ? language : a.language} />
            <p className="fine-on">{translated ? t('official.translatedBy') : !own ? t('official.original', languageName(a.language)) : ''}</p>
            <p className="fine-on">{t('official.source')}</p>
          </article>
        )
      })}
    </section>
  )
}

function DangerCard({ d, outlook, place }: { d: Detection; outlook: Outlook; place: SavedPlace }) {
  const { t, language } = useLanguage()
  const title = titleOf(d, t)
  const when = whenOf(d, language)
  const chips = chipsOf(d, outlook.days, place.name, t)
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
        <div className="chips">{chips.map((c) => <span key={c}>{c}</span>)}</div>
      </section>
      <Link href="/app/todo/0" className="btn big">{t('today.whatToDo')}</Link>
      <Listen text={[title, when, ...chips].join('. ')} />
      <button type="button" className="btn big share" onClick={share}><Icon name="share" size={24} />{t('today.share')}</button>
    </>
  )
}

// Rain worth showing on the week strip: a whole millimetre or more (a display choice, not a warning line).
const wet = (mm: number | null) => mm !== null && Math.round(mm) >= 1

function Week({ outlook }: { outlook: Outlook }) {
  const { t, language } = useLanguage()
  return (
    <section aria-label={t('today.week')}>
      <ol className="week">
        {outlook.days.map((d) => {
          const level = dayLevel(d)
          return (
            <li key={d.day} className={level ?? ''} aria-label={`${weekday(d.day, language)}: ${d.tmax_c === null ? '–' : Math.round(d.tmax_c)}°${wet(d.rain_mm) ? `, ${t('today.rainMm', Math.round(d.rain_mm as number))}` : ''}, ${level ? t('today.danger') : t('today.noDanger')}`}>
              <span className="wd">{weekday(d.day, language)}</span>
              <Icon name={dayIcon(d)} size={26} />
              <b>{d.tmax_c === null ? '–' : `${Math.round(d.tmax_c)}°`}</b>
              {wet(d.rain_mm) && <span className="rain">{t('today.rainMm', Math.round(d.rain_mm as number))}</span>}
            </li>
          )
        })}
      </ol>
    </section>
  )
}
