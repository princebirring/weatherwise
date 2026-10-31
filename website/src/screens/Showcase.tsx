import { useState } from 'react'
import { api } from '../api'
import { Logo } from '../components/Icon'
import { ErrorBox, LanguagePicker, Loading } from '../components/Shell'
import { useAsync } from '../components/useAsync'
import { Link } from '../router'
import { useLanguage, type T } from '../text'
import type { TextKey } from '../text/en'
import type { HazardScore, Language, Replay, ReplayEvent } from '../types'

const TOOLS = ['find_place', 'resolve_place', 'hazard_outlook', 'official_alerts', 'find_shelters', 'backtest', 'cap_alerts', 'message_policy']

const LAYERS = [1, 2, 3, 4, 5] as const
const RULES = [1, 2, 3] as const

/** The page for judges and partners: what WeatherWise is, and the proof it works. */
export function Showcase() {
  const { t } = useLanguage()
  const events = useAsync(() => api.replays(), 'replays')
  return (
    <div className="page">
      <header className="site-header">
        <div className="wrap">
          <Link href="/" className="row" style={{ textDecoration: 'none', color: 'var(--ink)' }}><Logo /><b style={{ fontSize: 21 }}>{t('brand.name')}</b></Link>
          <nav aria-label={t('show.sections')}>
            <a href="#parts">{t('show.whatItDoes')}</a>
            <a href="#replay">{t('show.proof')}</a>
            <a href="#how">{t('show.how')}</a>
            <a href="#developers">{t('show.developers')}</a>
          </nav>
          <div className="row" style={{ marginLeft: 'auto' }}>
            <LanguagePicker />
            <Link href="/app" className="btn">{t('show.tryLive')}</Link>
          </div>
        </div>
      </header>

      <main>
        <section className="wrap hero">
          <div>
            <span className="kicker" style={{ color: 'var(--action)' }}>{t('show.kicker')}</span>
            <h1>{t('show.headline')}</h1>
            <p>{t('show.lede')}</p>
            <div className="row" style={{ flexWrap: 'wrap', gap: 12 }}>
              <Link href="/app" className="btn">{t('show.tryLive')}</Link>
              <a href="#replay" className="btn secondary">{t('show.replayCta')}</a>
            </div>
          </div>
          <div>{events.data?.slice(0, 2).map((e) => <HeroStat key={e.id} event={e} />)}</div>
        </section>

        <section id="parts" className="wrap section">
          <h2>{t('show.partsTitle')}</h2>
          <div className="grid-auto">
            {([['show.part1', 'show.part1Title', 'show.part1Body', 'var(--orange)'],
               ['show.part2', 'show.part2Title', 'show.part2Body', 'var(--action)'],
               ['show.part3', 'show.part3Title', 'show.part3Body', 'var(--flood)']] as const).map(([k, title, body, color]) => (
              <article key={k} className="card stack" style={{ padding: 24, borderRadius: 20 }}>
                <span className="kicker" style={{ color }}>{t(k)}</span>
                <h3 style={{ fontSize: 23 }}>{t(title)}</h3>
                <p style={{ color: 'var(--ink-2)', lineHeight: 1.5 }}>{t(body)}</p>
              </article>
            ))}
          </div>
        </section>

        <section id="replay" className="band">
          <div className="wrap section stack" style={{ gap: 18 }}>
            <div className="stack" style={{ gap: 6 }}>
              <h2 style={{ marginBottom: 0 }}>{t('show.replayTitle')}</h2>
              <p style={{ fontSize: 17, color: 'var(--ink-2)', maxWidth: 760 }}>{t('show.replayLede')}</p>
            </div>
            {events.loading && <Loading />}
            {events.error && <ErrorBox error={events.error} retry={events.retry} />}
            {events.data && <Replays events={events.data} />}
          </div>
        </section>

        <section id="how" className="wrap section stack" style={{ gap: 16 }}>
          <h2 style={{ marginBottom: 0 }}>{t('show.howTitle')}</h2>
          <div className="grid-auto" style={{ gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))' }}>
            {LAYERS.map((n) => (
              <div key={n} className="card stack" style={{ gap: 6, padding: 18 }}>
                <span className="kicker" style={{ color: 'var(--action)', fontSize: 12 }}>{t(`show.layer${n}n` as TextKey)}</span>
                <b style={{ fontSize: 18 }}>{t(`show.layer${n}t` as TextKey)}</b>
                <span style={{ fontSize: 15, color: 'var(--ink-2)' }}>{t(`show.layer${n}b` as TextKey)}</span>
              </div>
            ))}
          </div>
          <div className="grid-auto">
            {RULES.map((n) => (
              <p key={n} style={{ background: 'var(--action-soft)', borderRadius: 16, padding: 18, fontSize: 16 }}>
                <b>{t(`show.rule${n}b` as TextKey)}</b> {t(`show.rule${n}t` as TextKey)}
              </p>
            ))}
          </div>
        </section>

        <section id="developers" className="dark">
          <div className="wrap section" style={{ display: 'flex', flexWrap: 'wrap', gap: 32 }}>
            <div className="stack" style={{ flex: '999 1 420px', minWidth: 0 }}>
              <h2 style={{ marginBottom: 0 }}>{t('show.devTitle')}</h2>
              <p style={{ fontSize: 17 }}>{t('show.devBody')}</p>
              <div className="row mono" style={{ flexWrap: 'wrap', gap: 8 }}>{TOOLS.map((x) => <span key={x} className="chip">{x}</span>)}</div>
            </div>
            <pre className="code mono" style={{ flex: '1 1 360px', minWidth: 0, margin: 0 }}>{`uv run python -m weatherwise.mcp_server.server
# or over HTTP
uv run python -m weatherwise.mcp_server.server --http`}</pre>
          </div>
        </section>

        <section className="wrap section">
          <div className="card stack" style={{ gap: 4 }}>
            <b style={{ fontSize: 18 }}>{t('show.builtWith')}</b>
            <span lang="en">Strands Agents · Amazon Bedrock AgentCore · Claude on Amazon Bedrock · Model Context Protocol</span>
          </div>
        </section>
      </main>

      <footer className="site-footer">
        <div className="wrap" style={{ display: 'flex', flexWrap: 'wrap', gap: '12px 32px' }}>
          <span style={{ flex: '999 1 420px' }}><b style={{ color: 'var(--ink)' }}>{t('show.footerNotOfficial')}</b> {t('show.footerFollow')}</span>
          <span style={{ flex: '1 1 320px' }}>{t('show.footerSources')}</span>
        </div>
      </footer>
    </div>
  )
}

function HeroStat({ event }: { event: ReplayEvent }) {
  const { t, language } = useLanguage()
  const replay = useAsync(() => api.replay(event.id), event.id)
  const head = replay.data && headline(replay.data, t, language)
  if (!head) return null
  return (
    <a href="#replay" className="card" style={{ padding: 20, borderRadius: 18, textDecoration: 'none', color: 'var(--ink)' }}>
      <div className="stat" style={{ color: head.color }}>{head.value}</div>
      <div style={{ marginTop: 6 }}>{head.label}. {event.titles[language]}.</div>
    </a>
  )
}

/** The one number that sums up a replay, computed from its scores. */
function headline(r: Replay, t: T, language: Language): { value: string; label: string; color: string } | null {
  const scores = Object.values(r.verification.scores ?? {})
  const flood = r.verification.scores?.river_flood
  const firstLead = flood?.event_lead_days.find(([, lead]) => lead !== null)
  if (flood && firstLead) return { value: `${firstLead[1]}`, label: t('show.lead', fullDate(firstLead[0], language)), color: 'var(--flood)' }
  const best = scores.filter((s) => s.pod !== null).sort((a, b) => (b.pod ?? 0) - (a.pod ?? 0))[0]
  if (best) return { value: `${Math.round((best.pod ?? 0) * 100)}%`, label: `${t('show.pod')} (${hazardName(best.hazard, t)})`, color: 'var(--orange)' }
  return null
}

const hazardName = (h: string, t: T) => t(`score.${h}` as TextKey)
const LOCALES: Record<Language, string> = { en: 'en-IN', hi: 'hi-IN', mr: 'mr-IN' }
const fullDate = (iso: string, language: Language) =>
  new Intl.DateTimeFormat(LOCALES[language], { day: 'numeric', month: 'short', year: 'numeric', timeZone: 'UTC' }).format(new Date(iso))

function Replays({ events }: { events: ReplayEvent[] }) {
  const { t, language } = useLanguage()
  const [id, setId] = useState(events[0]?.id)
  const replay = useAsync(id ? () => api.replay(id) : null, id ?? '')
  return (
    <>
      <div className="tabs" role="tablist" aria-label={t('show.events')}>
        {events.map((e) => (
          <button key={e.id} type="button" role="tab" aria-selected={e.id === id} onClick={() => setId(e.id)}>{e.titles[language]}</button>
        ))}
      </div>
      <div className="card stack" role="tabpanel" style={{ padding: 22, borderRadius: 20, gap: 14 }}>
        {replay.loading && <Loading />}
        {replay.error && <ErrorBox error={replay.error} retry={replay.retry} />}
        {replay.data && <ReplayView r={replay.data} />}
      </div>
    </>
  )
}

function ReplayView({ r }: { r: Replay }) {
  const { t, language } = useLanguage()
  const river = r.flood_level_m3s !== null && r.timeline.some((d) => d.observed.river_m3s !== null)
  const metric = (d: Replay['timeline'][number]) => (river ? d.observed.river_m3s : d.observed.tmax) ?? null
  const values = r.timeline.map(metric)
  const known = values.filter((v): v is number => v !== null)
  const floor = river ? 0 : Math.min(...known, ...r.timeline.map((d) => d.observed.normal_tmax ?? Infinity)) - 3
  const top = Math.max(...known, river ? (r.flood_level_m3s ?? 0) * 1.04 : -Infinity)
  const y = (v: number) => ((v - floor) / (top - floor)) * 100
  const cols = { gridTemplateColumns: `repeat(${r.timeline.length}, minmax(0, 1fr))` }
  const scores = Object.values(r.verification.scores ?? {}).filter((s) => s.hits + s.misses + s.false_alarms > 0)
  const conditions = r.verification.conditions_met

  return (
    <>
      <div className="row" style={{ flexWrap: 'wrap', alignItems: 'baseline', gap: '6px 20px' }}>
        <b style={{ fontSize: 21 }}>{r.event.titles[language]}</b>
        <span className="small">
          {river ? t('show.riverAxis', Math.round(r.flood_level_m3s ?? 0).toLocaleString('en-IN')) : t('show.tmaxAxis')}
        </span>
      </div>
      <div className="timeline">
        <div className="inner">
          <div className="plot" style={cols} role="img"
            aria-label={r.timeline.map((d, i) => `${d.day}: ${values[i] ?? '–'}${d.what_happened.length ? ` (${d.what_happened.join(', ')})` : ''}`).join('; ')}>
            {river && <div className="refline" style={{ bottom: `${y(r.flood_level_m3s ?? 0)}%` }} />}
            {r.timeline.map((d, i) => (
              <div key={d.day} style={{ position: 'relative', height: '100%', display: 'flex', alignItems: 'flex-end' }}>
                <i className={d.what_happened.length ? 'hit' : ''} style={{ width: '100%', height: `${values[i] === null ? 0 : y(values[i] as number)}%` }} />
                {!river && d.observed.normal_tmax != null && (
                  <span style={{ position: 'absolute', left: 0, right: 0, bottom: `${y(d.observed.normal_tmax)}%`, borderTop: '2px dashed var(--ink)' }} />
                )}
              </div>
            ))}
          </div>
          <div className="marks" style={cols} aria-hidden="true">
            {r.timeline.map((d) => <span key={d.day} className={d.flood_guide ? 'guide' : d.would_have_sent.length ? 'warned' : ''} title={d.would_have_sent.join(', ')} />)}
          </div>
          <div className="labels" style={cols} aria-hidden="true">
            {r.timeline.map((d) => <span key={d.day}>{Number(d.day.slice(8))}</span>)}
          </div>
        </div>
      </div>
      <div className="legend" style={{ fontSize: 14, color: 'var(--ink-2)' }}>
        {river && <span><i className="swatch" style={{ background: 'var(--flood)' }} />{t('show.legendGuide')}</span>}
        <span><i className="swatch" style={{ background: '#9DB8DA' }} />{t('show.legendWarned')}</span>
        <span><i className="swatch" style={{ background: 'var(--red)' }} />{t('show.legendHappened')}</span>
      </div>

      <div className="grid-auto" style={{ gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))' }}>
        {scores.map((s) => <ScoreCards key={s.hazard} s={s} />)}
        {conditions && (
          <div className="mini">
            <b>{Object.values(conditions).filter((hs) => hs.includes('heat_wave')).length} / {Object.keys(conditions).length}</b>
            {t('show.conditionsDays')}
          </div>
        )}
      </div>
      <p className="small">{r.mode === 'as_issued' ? t('show.noArchive') : t('show.conditionsOnly')}</p>
    </>
  )
}

function ScoreCards({ s }: { s: HazardScore }) {
  const { t, language } = useLanguage()
  const name = hazardName(s.hazard, t)
  const lead = s.event_lead_days.find(([, l]) => l !== null)
  return (
    <>
      {lead && <div className="mini"><b>{lead[1]}</b>{t('show.lead', fullDate(lead[0], language))} · {name}</div>}
      {s.pod !== null && <div className="mini"><b>{Math.round(s.pod * 100)}%</b>{t('show.pod')} · {name}</div>}
      <div className="mini"><b>{s.far === null ? '–' : `${Math.round(s.far * 100)}%`}</b>{t('show.far')} · {name}</div>
    </>
  )
}
