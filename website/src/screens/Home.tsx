import { GROUP_ICONS, GROUPS, groupOf, groupStatus, iconOf, levelOf, LOCALES, officialTitle, shortDate, sortDetections, titleOf, whenOf, yourDay } from '../hazards'
import { Icon } from '../components/Icon'
import { Listen } from '../components/Listen'
import { ErrorBox, Loading } from '../components/Shell'
import type { Async } from '../components/useAsync'
import type { InstallPrompt } from '../components/useInstallPrompt'
import { Link } from '../router'
import { useGuidance, useLanguage } from '../text'
import type { TextKey } from '../text/en'
import type { Language, OfficialAlert, OfficialAlerts, Outlook, PlaceAndOutlook, SavedPlace } from '../types'

/** Today, as loud as the day is. Most days: "Your day" (what to do on the farm) and "Danger
 *  watch" (three quiet lights). Our own warning: a banner on top. An official red alert or a
 *  flood "move now": the whole screen is that one message and the calls. */
export function Home({ place, data, official, offline, install, onDismissInstall }: {
  place: SavedPlace; data: Async<PlaceAndOutlook>; official: Async<OfficialAlerts>; offline: boolean
  install: InstallPrompt | null; onDismissInstall?: () => void
}) {
  const { t, language } = useLanguage()

  // Official warnings come first, and do not wait for our forecast (it may be slow or down).
  const officialNow: OfficialAlerts | null = official.data
    ?? (official.error ? { status: 'unavailable', alerts: [], source: null } : data.data?.outlook.official ?? null)
  const timezone = data.data?.place.timezone
  const alerts = officialNow?.status === 'ok' ? officialNow.alerts : []
  const red = alerts.filter((a) => a.level === 'red')
  const floodUrgent = data.data?.outlook.flood_guide.mode === 'urgent'
  if (red.length || floodUrgent) return <Emergency alert={red[0]} floodUrgent={floodUrgent} timezone={timezone} />

  const title = <h1 className="sr-only">{t('today.screenTitle', place.name)}</h1>
  const officialTop = (
    <>
      {officialNow?.status === 'unavailable' && <p className="official-note warn" role="status"><Icon name="alert" size={22} />{t('official.unavailable')}</p>}
      {alerts.map((a) => <OfficialBanner key={a.id} alert={a} timezone={timezone} />)}
    </>
  )

  if (data.loading) return <main className="app-main">{title}{officialTop}<Loading /></main>
  if (data.error || !data.data) {
    return <main className="app-main">{title}{officialTop}{data.error && <ErrorBox error={data.error} retry={data.retry} />}</main>
  }

  const { outlook } = data.data
  const lines = outlook.data_missing.length && !outlook.days.length
    ? [{ icon: 'alert' as const, text: t('today.missingBody') }]
    : yourDay(outlook.days, language, t)
  const tiles = GROUPS.map((g) => ({ group: g, ...tileOf(g, outlook, t) }))

  return (
    <main className="app-main">
      {title}
      {offline && <p className="official-note warn" role="status"><Icon name="alert" size={22} />{t('offline.banner', shortDate(outlook.issue_date, language))}</p>}
      {officialTop}
      <DangerBanner outlook={outlook} />

      <section className="stack" style={{ gap: 8 }} aria-labelledby="day-heading">
        <div className="section-row">
          <h2 id="day-heading" className="label">{t('day.title')}</h2>
          <Listen round text={[...lines.map((l) => l.text), ...tiles.map((x) => `${t(`tile.${x.group}`)}: ${x.word}`)].join('. ')} />
        </div>
        <div className="day-card">
          {lines.map((l) => (
            <p key={l.text} className={`day-line ${l.icon}`}><span><Icon name={l.icon} size={24} /></span>{l.text}</p>
          ))}
        </div>
      </section>

      <section className="stack" style={{ gap: 8 }} aria-labelledby="watch-heading">
        <h2 id="watch-heading" className="label muted">{t('watch.title')}</h2>
        <div className="tiles">
          {tiles.map((x) => (
            <Link key={x.group} href={`/app/${x.group}`} className={`tile ${x.className}`}>
              <Icon name={GROUP_ICONS[x.group]} size={30} />
              <b>{t(`tile.${x.group}`)}</b>
              <span>{x.word}</span>
            </Link>
          ))}
        </div>
      </section>

      {officialNow?.status === 'ok' && alerts.length === 0 && <p className="small" style={{ textAlign: 'center' }}>{t('official.none')}</p>}

      {install && (
        <section className="card stack install">
          <b className="h-mid">{t('install.title')}</b>
          <p>{t('install.body')}</p>
          <div className="pair">
            <button type="button" className="btn big secondary" onClick={onDismissInstall}>{t('install.later')}</button>
            <button type="button" className="btn big" onClick={() => void install.prompt()}>{t('install.button')}</button>
          </div>
        </section>
      )}
    </main>
  )
}

/** A danger light: grey and "Quiet" unless a check found something, in IMD's colours and words. */
function tileOf(group: (typeof GROUPS)[number], outlook: Outlook, t: ReturnType<typeof useLanguage>['t']) {
  const s = groupStatus(group, outlook)
  if (s.level) return { word: t(`level.${s.level}`), className: `lv-${s.level}` }
  if (s.missing) return { word: t('watch.missing'), className: 'lv-missing' }
  return { word: t('watch.quiet'), className: 'calm' }
}

/** Our most serious warning this week (or the flood guide in prepare mode), and the way to what to do. */
function DangerBanner({ outlook }: { outlook: Outlook }) {
  const { t, language } = useLanguage()
  const top = sortDetections(outlook.detections)[0]
  const prepare = outlook.flood_guide.mode === 'prepare'
  if (!top && !prepare) return null
  const group = top ? groupOf(top.hazard) : 'flood'
  const level = top ? levelOf(top) : 'orange'
  return (
    <section className={`danger-banner lv-${level}`} role="alert">
      <h2 className="row"><Icon name={top ? iconOf(top.hazard) : 'waves'} size={32} />{top ? titleOf(top, t) : t('flood.prepareTitle')}</h2>
      <p className="when">{top ? whenOf(top, language) : t('flood.prepareBody')}</p>
      <Link href={`/app/${group}`} className="btn big">{t('today.whatToDo')}<Icon name="send" size={22} /></Link>
    </section>
  )
}

const untilOf = (iso: string, language: Language, timezone?: string) => new Intl.DateTimeFormat(LOCALES[language],
  { weekday: 'short', hour: 'numeric', minute: '2-digit', timeZone: timezone }).format(new Date(iso))

function languageName(code: string, language: Language) {
  try { return new Intl.DisplayNames([LOCALES[language]], { type: 'language' }).of(code) ?? code } catch { return code }
}

/** Who translated an official message, or which language it is in when nobody did. */
function OfficialSource({ alert }: { alert: OfficialAlert }) {
  const { t, language } = useLanguage()
  const own = alert.translations[language]
  const note = own && alert.language !== language ? t('official.translatedBy') : !own ? t('official.original', languageName(alert.language, language)) : ''
  return <>{note && <p className="fine-on">{note}</p>}<p className="fine-on">{t('official.source')}</p></>
}

/** An official warning that is not red: a slim banner; the full message one tap away. */
function OfficialBanner({ alert: a, timezone }: { alert: OfficialAlert; timezone?: string }) {
  const { t, language } = useLanguage()
  const own = a.translations[language]
  return (
    <article className={`official lv-${a.level === 'green' ? 'calm' : a.level}`} role="alert">
      <span className="kicker">{t('official.kicker', a.source)} · {t(`official.level.${a.level}` as TextKey)}</span>
      <h2 className="official-title"><Icon name="shield" size={26} />{officialTitle(a.event, language, t)}</h2>
      <p className="when-small">{t('official.until', untilOf(a.ends, language, timezone))}</p>
      <details>
        <summary>{t('official.more')}</summary>
        <div className="stack" style={{ gap: 8, marginTop: 8 }}>
          <p className="official-message" lang={own ? language : a.language}>{own ?? a.message}</p>
          <Listen text={own ?? a.message} lang={own ? language : a.language} />
          <OfficialSource alert={a} />
        </div>
      </details>
    </article>
  )
}

/** The whole screen for an official red alert or a flood "move now": one message and the calls. */
function Emergency({ alert: a, floodUrgent, timezone }: { alert?: OfficialAlert; floodUrgent: boolean; timezone?: string }) {
  const { t, language, policy } = useLanguage()
  const guidance = useGuidance()
  const h = policy?.helplines ?? { emergency: '112', ambulance: '108', disaster: '1077' }
  const own = a ? a.translations[language] ?? null : null
  const officialText = a ? own ?? a.message : null
  const line = floodUrgent && guidance ? guidance.flood_urgent : officialText ?? ''
  const flood = floodUrgent || !!a?.flood_related
  const group = flood ? 'flood' : a && /heat/i.test(a.event) ? 'heat' : null
  return (
    <main className="app-main emergency" role="alert">
      <span className="kicker">{a ? `${t('official.kicker', a.source)} · ${t('official.level.red')}` : t('flood.urgentTag')}</span>
      <h1 className="row"><Icon name="alert" size={34} />{a ? officialTitle(a.event, language, t) : t('flood.urgentTag')}</h1>
      <p className="when">{a ? t('official.until', untilOf(a.ends, language, timezone)) : t('flood.urgentWhy')}</p>
      <p className="big">{line}</p>
      <Listen text={line} lang={line === officialText && a && !own ? a.language : language} />
      <div className="two">
        <a href={`tel:${h.emergency}`} className="call-white"><b>{h.emergency}</b>{t('help.emergency')}</a>
        <a href={`tel:${h.disaster}`} className="call-outline"><b>{h.disaster}</b>{t('help.disaster')}</a>
      </div>
      {group && (
        <Link href={`/app/${group}`} className="btn big outline">
          <Icon name="home" size={24} />{flood ? t('flood.shelterNames') : t('today.whatToDo')}
        </Link>
      )}
      {a && officialText !== line && (
        <section className="emergency-official">
          <span className="kicker">{t('emergency.official')}</span>
          <p lang={own ? language : a.language}>{officialText}</p>
          <OfficialSource alert={a} />
        </section>
      )}
    </main>
  )
}
