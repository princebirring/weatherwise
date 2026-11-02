import { api } from '../api'
import { Icon, Logo, type IconName } from '../components/Icon'
import { ErrorBox, LanguagePicker, Loading } from '../components/Shell'
import { useAsync } from '../components/useAsync'
import { Link } from '../router'
import { useLanguage } from '../text'
import type { TextKey } from '../text/en'
import type { ReplayEvent } from '../types'
import { FlowDiagram } from './showcase/FlowDiagram'
import { PhoneDemo } from './showcase/PhoneDemo'
import { proofNumbers, Replays } from './showcase/Replays'
import { RulesDiagram } from './showcase/RulesDiagram'

const TOOLS = ['find_place', 'resolve_place', 'hazard_outlook', 'official_alerts', 'find_shelters', 'backtest', 'cap_alerts', 'message_policy']

// The three parts of AWS's climate-resilience example, each with the gap we measured and our answer.
const PARTS: { n: 1 | 2 | 3; icon: IconName; color: string }[] = [
  { n: 1, icon: 'heat', color: 'var(--orange)' },
  { n: 2, icon: 'home', color: 'var(--action)' },
  { n: 3, icon: 'waves', color: 'var(--flood)' },
]

// Strands features as they are used in weatherwise/agents (names are the SDK's, kept in English).
const FEATURES: [string, TextKey][] = [
  ['MCP tools', 'show.featMcp'], ['Agents as tools', 'show.featAgents'], ['Skills', 'show.featSkills'],
  ['Hooks', 'show.featHooks'], ['Steering', 'show.featSteering'], ['Graph', 'show.featGraph'],
  ['Evals', 'show.featEvals'], ['AgentCore Runtime', 'show.featRuntime'],
]

const LIMITS: TextKey[] = ['show.limit1', 'show.limit2', 'show.limit3', 'show.limit4']

/** The page for judges and partners: what WeatherWise does, how it decides, the proof, and how it is built. */
export function Showcase() {
  const { t } = useLanguage()
  const events = useAsync(() => api.replays(), 'replays')
  return (
    <div className="page">
      <header className="site-header">
        <div className="wrap">
          <Link href="/" className="row" style={{ textDecoration: 'none', color: 'var(--ink)' }}><Logo /><b style={{ fontSize: 21 }}>{t('brand.name')}</b></Link>
          <nav aria-label={t('show.sections')}>
            <a href="#why">{t('show.navWhy')}</a>
            <a href="#decide">{t('show.navDecide')}</a>
            <a href="#replay">{t('show.proof')}</a>
            <a href="#built">{t('show.navBuilt')}</a>
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
              <Link href="/app" className="btn big">{t('show.tryLive')}</Link>
              <a href="#replay" className="btn big secondary">{t('show.replayCta')}</a>
            </div>
            {events.data ? <HeroProof events={events.data} /> : events.loading && <section className="hero-proof" aria-hidden="true" />}
          </div>
          <PhoneDemo />
        </section>

        <section id="why" className="wrap section">
          <SectionHead n="01" title={t('show.whyTitle')} lede={t('show.whyLede')} />
          <div className="grid-auto parts">
            {PARTS.map(({ n, icon, color }) => (
              <article key={n} className="part-card">
                <div className="row" style={{ gap: 12 }}>
                  <span className="part-icon" style={{ color }}><Icon name={icon} size={28} /></span>
                  <span className="stack" style={{ gap: 0 }}>
                    <span className="kicker" style={{ color }}>{t(`show.part${n}`)}</span>
                    <h3>{t(`show.part${n}Title`)}</h3>
                  </span>
                </div>
                <div className="gap-answer">
                  <p><span className="mini-label">{t('show.gapLabel')}</span>{t(`show.gap${n}`)}</p>
                  <p className="answer"><span className="mini-label">{t('show.answerLabel')}</span>{t(`show.answer${n}`)}</p>
                </div>
              </article>
            ))}
          </div>
        </section>

        <section id="decide" className="band">
          <div className="wrap section">
            <SectionHead n="02" title={t('show.decideTitle')} lede={t('show.decideLede')} />
            <RulesDiagram />
          </div>
        </section>

        <section id="replay" className="wrap section stack" style={{ gap: 18 }}>
          <SectionHead n="03" title={t('show.replayTitle')} lede={t('show.replayLede')} />
          {events.loading && <Loading />}
          {events.error && <ErrorBox error={events.error} retry={events.retry} />}
          {events.data && <Replays events={events.data} />}
        </section>

        <section id="built" className="band">
          <div className="wrap section stack" style={{ gap: 22 }}>
            <SectionHead n="04" title={t('show.builtTitle')} lede={t('show.builtLede')} />
            <FlowDiagram />
            <div className="stack" style={{ gap: 10 }}>
              <h3 className="h-mid">{t('show.strandsTitle')}</h3>
              <ul className="features">
                {FEATURES.map(([name, desc]) => <li key={name}><b className="mono" lang="en">{name}</b><span>{t(desc)}</span></li>)}
              </ul>
            </div>
            <div className="grid-auto">
              {([1] as const).map((n) => (
                <p key={n} className="rule-tile"><b>{t(`show.rule${n}b`)}</b> {t(`show.rule${n}t`)}</p>
              ))}
            </div>
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
          <SectionHead n="05" title={t('show.limitsTitle')} />
          <ul className="limits">{LIMITS.map((k) => <li key={k}>{t(k)}</li>)}</ul>
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

function SectionHead({ n, title, lede }: { n: string; title: string; lede?: string }) {
  return (
    <div className="section-head">
      <span className="section-n" aria-hidden="true">{n}</span>
      <h2>{title}</h2>
      {lede && <p>{lede}</p>}
    </div>
  )
}

/** Three numbers beside the headline, computed from the replays' own scores. */
function HeroProof({ events }: { events: ReplayEvent[] }) {
  const { t, language } = useLanguage()
  const all = useAsync(() => Promise.all(events.map((e) => api.replay(e.id))), events.map((e) => e.id).join(','))
  // While loading, an empty block keeps the numbers' place (index.css .hero-proof).
  if (!all.data) return all.loading ? <section className="hero-proof" aria-hidden="true" /> : null
  const p = proofNumbers(events, all.data)
  return (
    <section className="hero-proof" aria-label={t('show.proof')}>
      <div>
        {p.best && (
          <a href="#replay"><b>{p.best.days}</b><span>{t(p.best.days === 1 ? 'show.leadOne' : 'show.lead', p.best.event.titles[language])}</span></a>
        )}
        {p.floods > 0 && (
          <a href="#replay"><b>{p.floodsWarned} / {p.floods}</b>
            <span>{t('show.statFloods')}{p.floodFalseAlarms === 0 ? `, ${t('show.statNoFalse')}` : ''}</span></a>
        )}
        <a href="#replay"><b>{events.length}</b><span>{t('show.statReplays')}</span></a>
      </div>
    </section>
  )
}
