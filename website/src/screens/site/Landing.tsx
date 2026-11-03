import { Icon, type IconName } from '../../components/Icon'
import { Link } from '../../router'
import { useLanguage } from '../../text'
import type { TextKey } from '../../text/en'
import { PhoneDemo } from '../showcase/PhoneDemo'
import { Person } from './People'
import { BEST_LEAD, SAFETY, SCORECARD } from './results'
import { SectionTitle } from './SiteLayout'
import { REPO, TEAM } from './team'

// The pitch, in the order a first-time visitor needs it: what it is, why it is needed, what it
// does, whether it works, what it is built on, where it runs, and who is behind it.

const BUILT_WITH = ['Strands Agents', 'Amazon Bedrock', 'Bedrock AgentCore', 'Amazon ECS', 'MCP', 'IMD · SACHET']

// Akola, April 2026 (show.gap1): the weather station against its 25 km forecast square.
const GAP = { low: 38, high: 50, line: 45, station: 46.9, forecast: 43.6 }

const JOBS: { icon: IconName; tone: string; title: TextKey; body: TextKey; part: TextKey }[] = [
  { icon: 'heat', tone: 'heat', part: 'show.part1', title: 'show.part1Title', body: 'site.job1' },
  { icon: 'home', tone: 'action', part: 'show.part2', title: 'show.part2Title', body: 'site.job2' },
  { icon: 'waves', tone: 'flood', part: 'show.part3', title: 'show.part3Title', body: 'site.job3' },
]
const PERKS: TextKey[] = ['site.perk1', 'site.perk2', 'site.perk3', 'site.perk4']

// The disasters it warned about ahead of time, longest warning first. All ten, misses included, are on /impact.
const AHEAD = SCORECARD.filter((r) => r.outcome === 'ahead').sort((a, b) => (b.days ?? 0) - (a.days ?? 0))
const MAX_DAYS = BEST_LEAD.days ?? 9

// How a question becomes an answer, left to right (AWS parts marked), and who else can plug in.
const FLOW: { icon: IconName; title?: TextKey; name?: string; body: TextKey; aws?: boolean }[] = [
  { icon: 'phone', title: 'site.flowPhoneT', body: 'site.flowPhoneB' },
  { icon: 'home', name: 'Amazon ECS', body: 'site.flowApiB', aws: true },
  { icon: 'chat', name: 'Bedrock AgentCore', body: 'site.flowCoreB', aws: true },
  { icon: 'shield', name: 'Climate Risk MCP', body: 'site.flowMcpB', aws: true },
  { icon: 'sun', title: 'site.flowDataT', body: 'site.flowDataB' },
]
const PILLARS: { name: string; body: TextKey }[] = [
  { name: 'Strands Agents', body: 'site.pillarStrands' },
  { name: 'Amazon Bedrock AgentCore', body: 'site.pillarCore' },
  { name: 'Climate Risk MCP server', body: 'site.pillarMcp' },
]

// India's land (about 2.97 million km²) in 25 km forecast squares (625 km² each), rounded.
const INDIA_SQUARES = '5,000'
const COVER: { icon: IconName; title: TextKey; body: TextKey; tone: string }[] = [
  { icon: 'pin', title: 'site.coverIndiaT', body: 'site.coverIndia', tone: 'now' },
  { icon: 'send', title: 'site.coverAfricaT', body: 'site.coverAfrica', tone: 'next' },
  { icon: 'check', title: 'site.coverCostT', body: 'site.coverCost', tone: '' },
]

export function Landing() {
  const { t, language, policy } = useLanguage()
  const pos = (v: number) => `${((v - GAP.low) / (GAP.high - GAP.low)) * 100}%`

  return (
    <>
      <section className="l-hero">
        <div className="wrap l-hero-grid">
          <div className="l-hero-copy">
            <span className="eyebrow">{t('show.kicker')}</span>
            <h1>{t('site.headline')}</h1>
            <p className="l-lede">{t('site.lede')}</p>
            <div className="l-ctas">
              <Link href="/app" className="btn big">{t('site.openApp')}</Link>
              <Link href="/how-it-works" className="btn big secondary">{t('site.navHow')}</Link>
            </div>
            <dl className="l-stats">
              <div><dt>{t('site.statLeadValue', BEST_LEAD.days ?? 0)}</dt><dd>{t('site.statLead', BEST_LEAD.titles[language])}</dd></div>
              <div><dt>0</dt><dd>{t('site.statNumbers')}</dd></div>
              <div><dt>3</dt><dd>{t('site.statLanguages')}</dd></div>
            </dl>
          </div>
          {/* The demo needs the safety advice from the API; until then an empty phone keeps the hero's shape. */}
          {policy ? <PhoneDemo /> : <figure className="phone-demo" aria-hidden="true"><div className="phone-tabs" /><div className="phone" /></figure>}
        </div>
        <div className="wrap l-built">
          <span>{t('site.builtWith')}</span>
          <ul>{BUILT_WITH.map((x) => <li key={x} lang="en">{x}</li>)}</ul>
        </div>
      </section>

      <section className="l-dark">
        <div className="wrap l-gap">
          <div>
            <SectionTitle kicker={t('site.problemKicker')} title={t('site.problemTitle')} lede={t('site.problemLede')} />
            <p className="l-gap-then">{t('site.problemThen')}</p>
          </div>
          <figure className="gap-fig">
            <figcaption>{t('site.gapCaption')}</figcaption>
            <div className="gap-plot">
              <span className="gap-line" style={{ left: pos(GAP.line) }}><em>{t('site.gapLine', GAP.line)}</em></span>
              <div className="gap-row">
                <span>{t('site.gapStation')}</span>
                <span className="gap-track"><i className="hot" style={{ width: pos(GAP.station) }} /><b>{GAP.station} °C</b></span>
              </div>
              <div className="gap-row">
                <span>{t('site.gapForecast')}</span>
                <span className="gap-track"><i style={{ width: pos(GAP.forecast) }} /><b>{GAP.forecast} °C</b></span>
              </div>
            </div>
            <p className="gap-note">{t('site.gapRain')}</p>
          </figure>
        </div>
      </section>

      <section className="l-section">
        <div className="wrap">
          <SectionTitle kicker={t('site.jobsKicker')} title={t('site.jobsTitle')} lede={t('site.jobsLede')} />
          <div className="jobs">
            {JOBS.map((j) => (
              <article key={j.title} className={`job t-${j.tone}`}>
                <span className="job-icon"><Icon name={j.icon} size={30} /></span>
                <span className="job-part">{t(j.part)}</span>
                <h3>{t(j.title)}</h3>
                <p>{t(j.body)}</p>
              </article>
            ))}
          </div>
          <ul className="perks">{PERKS.map((k) => <li key={k}><Icon name="check" size={20} />{t(k)}</li>)}</ul>
        </div>
      </section>

      <section className="l-section l-band" id="impact">
        <div className="wrap">
          <SectionTitle kicker={t('site.navImpact')} title={t('site.impactTitle')} lede={t('site.impactLede')} />
          <ol className="leads">
            {AHEAD.map((r) => (
              <li key={r.id} className={`lead t-${r.kind}`}>
                <span className="lead-icon"><Icon name={r.kind === 'flood' ? 'waves' : 'heat'} size={26} /></span>
                <b>{t('site.impactDays', r.days ?? 0)}</b>
                <span className="lead-bar" aria-hidden="true"><i style={{ width: `${((r.days ?? 0) / MAX_DAYS) * 100}%` }} /></span>
                <span className="lead-title">{r.titles[language]}</span>
              </li>
            ))}
          </ol>
          <Link href="/impact" className="more">{t('site.impactAll', SCORECARD.length)} <Icon name="send" size={18} /></Link>
        </div>
      </section>

      <section className="l-dark l-aws" id="built">
        <div className="wrap">
          <SectionTitle kicker={t('site.awsKicker')} title={t('site.awsTitle')} lede={t('site.awsLede')} />
          <ol className="stack-flow">
            {FLOW.map((n) => (
              <li key={n.body} className={n.aws ? 'aws' : ''}>
                <span className="sf-icon"><Icon name={n.icon} size={22} /></span>
                <b lang={n.name ? 'en' : undefined}>{n.name ?? t(n.title!)}</b>
                <span>{t(n.body)}</span>
              </li>
            ))}
          </ol>
          <p className="stack-also"><Icon name="send" size={18} /><b>{t('site.flowYoursT')}</b>{t('site.flowYoursB')} → <span lang="en">Climate Risk MCP</span></p>
          <div className="pillars">
            {PILLARS.map((p) => (
              <article key={p.name}>
                <h3 lang="en">{p.name}</h3>
                <p>{t(p.body)}</p>
              </article>
            ))}
          </div>
          <div className="safety">
            <p className="safety-head"><Icon name="shield" size={20} />{t('site.safetyStrip')}</p>
            <div><b>{SAFETY.mistakesCaught.join(' / ')}</b><span>{t('site.safety1')}</span></div>
            <div><b>{SAFETY.goodDraftsPassed.join(' / ')}</b><span>{t('site.safety2')}</span></div>
            <div><b>{SAFETY.unsafeNeverSent.join(' / ')}</b><span>{t('site.safety3')}</span></div>
          </div>
          <div className="l-ctas">
            <Link href="/how-it-works" className="btn big">{t('site.howDecided')}</Link>
            <Link href="/developers" className="btn big outline">{t('site.plugIn')}</Link>
          </div>
        </div>
      </section>

      <section className="l-section" id="coverage">
        <div className="wrap cover">
          <figure className="globe">
            <img src="/coverage-globe.svg" width={640} height={640} alt={t('site.globeAlt')} />
            <figcaption>
              <span className="now"><i />{t('site.legendIndia')}</span>
              <span className="next"><i />{t('site.legendAfrica')}</span>
            </figcaption>
          </figure>
          <div>
            <SectionTitle kicker={t('site.coverKicker')} title={t('site.coverTitle')} />
            <ul className="cover-list">
              {COVER.map((c) => (
                <li key={c.title} className={c.tone}>
                  <span className="trust-icon"><Icon name={c.icon} size={22} /></span>
                  <span><b>{t(c.title)}</b>{t(c.body, INDIA_SQUARES)}</span>
                </li>
              ))}
            </ul>
          </div>
        </div>
      </section>

      <section className="l-section" id="team">
        <div className="wrap">
          <SectionTitle kicker={t('site.teamKicker')} title={t('site.teamTitle')} />
          <div className="team">{TEAM.map((m) => <Person key={m.name} m={m} short />)}</div>
          <Link href="/about" className="more">{t('site.aboutMore')} <Icon name="send" size={18} /></Link>
        </div>
      </section>

      <section className="l-final">
        <div className="wrap l-final-grid">
          <div>
            <h2>{t('site.finalTitle')}</h2>
            <p>{t('site.finalBody')}</p>
            <div className="l-ctas">
              <Link href="/app" className="btn big">{t('site.openApp')}</Link>
              <a href={REPO} target="_blank" rel="noreferrer" className="btn big outline">{t('site.readCode')}</a>
            </div>
          </div>
          <figure className="qr">
            <img src="/qr-app.svg" width={150} height={150} alt={t('site.qrAlt')} />
            <figcaption>{t('site.qrCaption')}</figcaption>
          </figure>
        </div>
      </section>
    </>
  )
}
