import { Icon, type IconName } from '../../components/Icon'
import { Link } from '../../router'
import { useLanguage } from '../../text'
import type { TextKey } from '../../text/en'
import { PhoneDemo } from '../showcase/PhoneDemo'
import { Scorecard } from './Scorecard'
import { BEST_LEAD, SAFETY, SCORECARD } from './results'
import { SectionTitle } from './SiteLayout'
import { REPO, TEAM, type Member } from './team'

// The pitch, in the order a first-time visitor needs it: what it is, why it is needed, what it
// does, whether it works, whether to trust it, who it is for, and who is behind it.

const BUILT_WITH = ['Strands Agents', 'Amazon Bedrock', 'Bedrock AgentCore', 'Amazon ECS', 'MCP', 'IMD · SACHET']

// Akola, April 2026 (show.gap1): the weather station against its 25 km forecast square.
const GAP = { low: 38, high: 50, line: 45, station: 46.9, forecast: 43.6 }

const JOBS: { icon: IconName; tone: string; title: TextKey; body: TextKey; part: TextKey }[] = [
  { icon: 'heat', tone: 'heat', part: 'show.part1', title: 'show.part1Title', body: 'site.job1' },
  { icon: 'home', tone: 'action', part: 'show.part2', title: 'show.part2Title', body: 'site.job2' },
  { icon: 'waves', tone: 'flood', part: 'show.part3', title: 'show.part3Title', body: 'site.job3' },
]
const PERKS: TextKey[] = ['site.perk1', 'site.perk2', 'site.perk3', 'site.perk4']

const TRUST: { icon: IconName; title: TextKey; body: TextKey }[] = [
  { icon: 'check', title: 'show.rule1b', body: 'site.trust1' },
  { icon: 'shield', title: 'show.rule2b', body: 'site.trust2' },
  { icon: 'clock', title: 'site.trust3b', body: 'site.trust3' },
]

const AUDIENCES: { icon: IconName; title: TextKey; body: TextKey; cta: TextKey; href: string }[] = [
  { icon: 'plant', title: 'site.forFamilies', body: 'site.forFamiliesBody', cta: 'site.openApp', href: '/app' },
  { icon: 'shield', title: 'site.forPartners', body: 'site.forPartnersBody', cta: 'site.talkToUs', href: '/#team' },
  { icon: 'send', title: 'site.forDevelopers', body: 'site.forDevelopersBody', cta: 'site.seeTools', href: '/developers' },
]

// India's land (about 2.97 million km²) in 25 km forecast squares (625 km² each), rounded.
const INDIA_SQUARES = '~5,000'

const ROADMAP: [TextKey, TextKey][] = [['site.now', 'site.nowBody'], ['site.next', 'site.nextBody'], ['site.later', 'site.laterBody']]

export function Landing() {
  const { t, language, policy } = useLanguage()
  const pos =(v: number) => `${((v - GAP.low) / (GAP.high - GAP.low)) * 100}%`

  return (
    <>
      <section className="l-hero">
        <div className="wrap l-hero-grid">
          <div className="l-hero-copy">
            <span className="eyebrow">{t('show.kicker')}</span>
            <h1>{t('show.headline')}</h1>
            <p className="l-lede">{t('site.lede')}</p>
            <div className="l-ctas">
              <Link href="/app" className="btn big">{t('site.openApp')}</Link>
              <Link href="/proof" className="btn big secondary">{t('site.seeProof')}</Link>
            </div>
            <dl className="l-stats">
              <div><dt>{t('site.statLeadValue', BEST_LEAD.days ?? 0)}</dt><dd>{t('site.statLead', BEST_LEAD.titles[language])}</dd></div>
              <div><dt>{SCORECARD.length}</dt><dd>{t('site.statReplays')}</dd></div>
              <div><dt>0</dt><dd>{t('site.statNumbers')}</dd></div>
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

      <section className="l-section l-band" id="proof">
        <div className="wrap">
          <SectionTitle kicker={t('site.proofKicker')} title={t('site.proofTitle', SCORECARD.length)} lede={t('show.replayLede')} />
          <Scorecard />
          <Link href="/proof" className="more">{t('site.replayDayByDay')} <Icon name="send" size={18} /></Link>
        </div>
      </section>

      <section className="l-section">
        <div className="wrap">
          <SectionTitle kicker={t('site.trustKicker')} title={t('site.trustTitle')} lede={t('show.builtLede')} />
          <div className="trust">
            {TRUST.map((x) => (
              <article key={x.title}>
                <span className="trust-icon"><Icon name={x.icon} size={24} /></span>
                <h3>{t(x.title)}</h3>
                <p>{t(x.body)}</p>
              </article>
            ))}
          </div>
          <div className="safety">
            <div><b>{SAFETY.mistakesCaught.join(' / ')}</b><span>{t('site.safety1')}</span></div>
            <div><b>{SAFETY.goodDraftsPassed.join(' / ')}</b><span>{t('site.safety2')}</span></div>
            <div><b>{SAFETY.unsafeNeverSent.join(' / ')}</b><span>{t('site.safety3')}</span></div>
            <p>{t('site.safetyNote')}</p>
          </div>
          <Link href="/how-it-works" className="more">{t('site.howDecided')} <Icon name="send" size={18} /></Link>
        </div>
      </section>

      <section className="l-section l-band">
        <div className="wrap">
          <SectionTitle kicker={t('site.whoKicker')} title={t('site.whoTitle')} />
          <div className="audiences">
            {AUDIENCES.map((a) => (
              <article key={a.title}>
                <span className="trust-icon"><Icon name={a.icon} size={24} /></span>
                <h3>{t(a.title)}</h3>
                <p>{t(a.body)}</p>
                <Link href={a.href} className="more">{t(a.cta)} <Icon name="send" size={18} /></Link>
              </article>
            ))}
          </div>
          <div className="scale">
            <div className="scale-number"><b>{INDIA_SQUARES}</b><span>{t('site.scaleUnit')}</span></div>
            <p>{t('site.scaleBody')}</p>
          </div>
          <ol className="roadmap">
            {ROADMAP.map(([when, what], i) => (
              <li key={when} className={i === 0 ? 'now' : ''}><b>{t(when)}</b><span>{t(what)}</span></li>
            ))}
          </ol>
        </div>
      </section>

      <section className="l-section" id="team">
        <div className="wrap">
          <SectionTitle kicker={t('site.navTeam')} title={t('site.teamTitle')} lede={t('site.teamLede')} />
          <div className="team">{TEAM.map((m) => <Person key={m.name} m={m} />)}</div>
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

function Person({ m }: { m: Member }) {
  const { t } = useLanguage()
  return (
    <article className="person">
      {m.photo
        ? <img className="person-photo" src={m.photo} width={112} height={112} alt={m.name} />
        : <span className="person-photo initials" aria-hidden="true">{m.initials}</span>}
      <div>
        <h3>{m.name}</h3>
        <p className="person-role">{t(m.role)}</p>
        <p>{t(m.bio)}</p>
        <p className="person-links">
          {m.links.map((l) => <a key={l.href} href={l.href} target="_blank" rel="noreferrer" lang="en">{l.label} ↗</a>)}
        </p>
      </div>
    </article>
  )
}
