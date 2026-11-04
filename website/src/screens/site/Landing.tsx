import { Icon, type IconName } from '../../components/Icon'
import { Link } from '../../router'
import { useLanguage } from '../../text'
import type { TextKey } from '../../text/en'
import { PhoneDemo } from '../showcase/PhoneDemo'
import { Person } from './People'
import { BEST_LEAD, SAFETY, SCORECARD } from './results'
import { REPO, TEAM, VIDEO_COVER, VIDEO_SRC } from './team'

// One idea per screen, in the order a first-time visitor needs it: what it is (and the app
// itself), where it works, why it is needed, whether it works, what it does, what it is built
// on, and who is behind it. The detail lives on the inner pages.

// Akola, April 2026 (show.gap1): the weather station against its 25 km forecast square.
const GAP = { low: 38, high: 50, line: 45, station: 46.9, forecast: 43.6 }

// India's land (about 2.97 million km²) in 25 km forecast squares (625 km² each), rounded.
const INDIA_SQUARES = '~5,000'

// The other disasters it warned about ahead of time (the longest warning is the big number).
// All ten, misses included, are on /impact.
const AHEAD = SCORECARD.filter((r) => r.outcome === 'ahead' && r.id !== BEST_LEAD.id).sort((a, b) => (b.days ?? 0) - (a.days ?? 0))
const MAX_DAYS = BEST_LEAD.days ?? 9

const JOBS: { icon: IconName; tone: string; title: TextKey; body: TextKey }[] = [
  { icon: 'heat', tone: 'heat', title: 'show.part1Title', body: 'site.job1s' },
  { icon: 'home', tone: 'action', title: 'show.part2Title', body: 'site.job2s' },
  { icon: 'waves', tone: 'flood', title: 'show.part3Title', body: 'site.job3s' },
]

// How a question becomes an answer, left to right (AWS parts marked).
const FLOW: { icon: IconName; title?: TextKey; name?: string; body: TextKey; aws?: boolean }[] = [
  { icon: 'phone', title: 'site.flowPhoneT', body: 'site.flowPhoneB' },
  { icon: 'home', name: 'Amazon ECS', body: 'site.flowApiB', aws: true },
  { icon: 'chat', name: 'Bedrock AgentCore', body: 'site.flowCoreB', aws: true },
  { icon: 'shield', name: 'Climate Risk MCP', body: 'site.flowMcpB', aws: true },
  { icon: 'sun', title: 'site.flowDataT', body: 'site.flowDataB' },
]

function Title({ kicker, title, lede }: { kicker: string; title: string; lede?: string }) {
  return (
    <div className="ap-title">
      <span className="eyebrow">{kicker}</span>
      <h2>{title}</h2>
      {lede && <p>{lede}</p>}
    </div>
  )
}

export function Landing() {
  const { t, language, policy } = useLanguage()
  const pos = (v: number) => `${((v - GAP.low) / (GAP.high - GAP.low)) * 100}%`

  return (
    <>
      <section className="ap-hero">
        {/* A morning sky: soft light behind the phone and a few slow clouds. Decoration only. */}
        <div className="ap-sky" aria-hidden="true"><i /><i /><i /></div>
        <div className="wrap ap-hero-grid">
          <div className="ap-hero-copy">
            <a href={REPO} target="_blank" rel="noreferrer" className="ap-badge"><Icon name="github" size={16} /> {t('site.openNote')}</a>
            <h1>{t('site.headline')}</h1>
            <p className="ap-sub">{t('site.lede')}</p>
            <div className="ap-ctas">
              <Link href="/app" className="btn big">{t('site.openApp')}</Link>
              <Link href="/how-it-works" className="ap-link">{t('site.navHow')} <Icon name="send" size={18} /></Link>
              <a href={REPO} target="_blank" rel="noreferrer" className="ap-link"><Icon name="github" size={18} /> {t('site.githubRepo')}</a>
            </div>
          </div>
          {/* The real app, tappable. It needs the safety advice from the API; until then an empty phone keeps the shape. */}
          {policy ? <PhoneDemo /> : <figure className="phone-demo" aria-hidden="true"><div className="phone" /><div className="phone-tabs" /></figure>}
        </div>
      </section>

      <section className="ap-section ap-video" id="video">
        <div className="wrap">
          <Title kicker={t('site.videoKicker')} title={t('site.videoTitle')} />
          <div className="video-frame">
            <video src={VIDEO_SRC} poster={VIDEO_COVER} title={t('site.videoTitle')} controls playsInline preload="metadata" />
          </div>
        </div>
      </section>

      <section className="ap-section" id="coverage">
        <div className="wrap">
          <Title kicker={t('site.coverKicker')} title={t('site.coverTitle')} />
          <figure className="globe">
            <img src="/coverage-globe.svg" width={680} height={680} alt={t('site.globeAlt')} />
            <figcaption>
              <span className="now"><i />{t('site.legendIndia')}</span>
              <span className="next"><i />{t('site.legendAfrica')}</span>
            </figcaption>
          </figure>
          <dl className="ap-stats">
            <div><dt>{INDIA_SQUARES}</dt><dd>{t('site.scaleUnit')}</dd></div>
            <div><dt>3</dt><dd>{t('site.statLanguages')}</dd></div>
            <div><dt>1</dt><dd>{t('site.gRules')}</dd></div>
          </dl>
        </div>
      </section>

      <section className="ap-section ap-dark">
        <div className="wrap">
          <Title kicker={t('site.problemKicker')} title={t('site.problemTitle')} />
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
          </figure>
          <p className="ap-note">{t('site.problemThen')}</p>
        </div>
      </section>

      <section className="ap-section" id="impact">
        <div className="wrap">
          <Title kicker={t('site.navImpact')} title={t('site.impactTitle')} />
          <div className="ap-impact">
            <div className="ap-card ap-feature">
              <span className="ap-feature-icon"><Icon name={BEST_LEAD.kind === 'flood' ? 'waves' : 'heat'} size={30} /></span>
              <p className="ap-huge">{t('site.statLeadValue', BEST_LEAD.days ?? 0)}</p>
              <p className="ap-huge-sub">{t('site.statLead', BEST_LEAD.titles[language])}</p>
            </div>
            <ol className="ap-card ap-leads">
              {AHEAD.map((r) => (
                <li key={r.id} className={`t-${r.kind}`}>
                  <b><Icon name={r.kind === 'flood' ? 'waves' : 'heat'} size={20} />{t('site.impactDays', r.days ?? 0)}</b>
                  <span className="lead-bar" aria-hidden="true"><i style={{ width: `${((r.days ?? 0) / MAX_DAYS) * 100}%` }} /></span>
                  <span>{r.titles[language]}</span>
                </li>
              ))}
            </ol>
          </div>
          <Link href="/impact" className="ap-link">{t('site.impactAll', SCORECARD.length)} <Icon name="send" size={18} /></Link>
        </div>
      </section>

      <section className="ap-section ap-soft">
        <div className="wrap">
          <Title kicker={t('site.jobsKicker')} title={t('site.jobsTitle')} />
          <div className="ap-jobs">
            {JOBS.map((j) => (
              <article key={j.title} className={`t-${j.tone}`}>
                <span className="ap-job-icon"><Icon name={j.icon} size={34} /></span>
                <h3>{t(j.title)}</h3>
                <p>{t(j.body)}</p>
              </article>
            ))}
          </div>
        </div>
      </section>

      <section className="ap-section ap-dark" id="built">
        <div className="wrap">
          <Title kicker={t('site.awsKicker')} title={t('site.awsTitle')} />
          <ol className="stack-flow">
            {FLOW.map((n) => (
              <li key={n.body} className={n.aws ? 'aws' : ''}>
                <span className="sf-icon"><Icon name={n.icon} size={22} /></span>
                <b lang={n.name ? 'en' : undefined}>{n.name ?? t(n.title!)}</b>
                <span>{t(n.body)}</span>
              </li>
            ))}
          </ol>
          <p className="ap-note ap-pill"><Icon name="shield" size={20} /> {t('site.awsSafety', SAFETY.mistakesCaught.join(' / '))}</p>
          <p className="ap-note ap-pill"><Icon name="check" size={20} /> {t('site.awsProd')}</p>
          <div className="ap-ctas">
            <Link href="/how-it-works" className="ap-link">{t('site.howDecided')} <Icon name="send" size={18} /></Link>
            <Link href="/developers" className="ap-link">{t('site.plugIn')} <Icon name="send" size={18} /></Link>
            <a href={REPO} target="_blank" rel="noreferrer" className="ap-link"><Icon name="github" size={18} /> {t('site.githubRepo')}</a>
          </div>
        </div>
      </section>

      <section className="ap-section" id="team">
        <div className="wrap">
          <Title kicker={t('site.teamKicker')} title={t('site.teamTitle')} />
          <div className="team">{TEAM.map((m) => <Person key={m.name} m={m} short />)}</div>
          <Link href="/about" className="ap-link">{t('site.aboutMore')} <Icon name="send" size={18} /></Link>
        </div>
      </section>

      <section className="l-final">
        <div className="wrap l-final-grid">
          <div>
            <h2>{t('site.finalTitle')}</h2>
            <p>{t('site.finalBody')}</p>
            <div className="l-ctas">
              <Link href="/app" className="btn big">{t('site.openApp')}</Link>
              <a href={REPO} target="_blank" rel="noreferrer" className="btn big outline"><Icon name="github" size={24} /> {t('site.openSourceGithub')}</a>
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
