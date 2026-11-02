import { api } from '../../api'
import { Icon, type IconName } from '../../components/Icon'
import { ErrorBox, Loading } from '../../components/Shell'
import { useAsync } from '../../components/useAsync'
import { Link } from '../../router'
import { useLanguage } from '../../text'
import type { TextKey } from '../../text/en'
import { FlowDiagram } from '../showcase/FlowDiagram'
import { Replays } from '../showcase/Replays'
import { RulesDiagram } from '../showcase/RulesDiagram'
import { Scorecard } from './Scorecard'
import { SAFETY, SCORECARD } from './results'
import { PageHead, SectionTitle } from './SiteLayout'
import { Person } from './People'
import { REPO, TEAM } from './team'

const LIMITS: TextKey[] = ['show.limit1', 'show.limit2', 'show.limit3', 'show.limit4']

/** /impact: the whole scorecard, the day-by-day replays, the safety evals, and what it misses. */
export function ImpactPage() {
  const { t } = useLanguage()
  const events = useAsync(() => api.replays(), 'replays')
  return (
    <>
      <PageHead kicker={t('site.navImpact')} title={t('site.proofTitle', SCORECARD.length)} lede={t('show.replayLede')} />
      <section className="l-section">
        <div className="wrap"><Scorecard /></div>
      </section>
      <section className="l-section l-band" id="replay">
        <div className="wrap stack" style={{ gap: 18 }}>
          <SectionTitle kicker={t('site.dayByDay')} title={t('show.replayTitle')} lede={t('site.dayByDayLede')} />
          {events.loading && <Loading />}
          {events.error && <ErrorBox error={events.error} retry={events.retry} />}
          {events.data && <Replays events={events.data} />}
        </div>
      </section>
      <section className="l-section">
        <div className="wrap">
          <SectionTitle kicker={t('site.trustKicker')} title={t('site.safetyTitle')} lede={t('site.safetyNote')} />
          <div className="safety">
            <div><b>{SAFETY.mistakesCaught.join(' / ')}</b><span>{t('site.safety1')}</span></div>
            <div><b>{SAFETY.goodDraftsPassed.join(' / ')}</b><span>{t('site.safety2')}</span></div>
            <div><b>{SAFETY.unsafeNeverSent.join(' / ')}</b><span>{t('site.safety3')}</span></div>
          </div>
        </div>
      </section>
      <section className="l-section l-band">
        <div className="wrap">
          <SectionTitle kicker={t('site.honest')} title={t('show.limitsTitle')} />
          <ul className="limits">{LIMITS.map((k) => <li key={k}>{t(k)}</li>)}</ul>
        </div>
      </section>
    </>
  )
}

// Strands features as they are used in weatherwise/agents (names are the SDK's, kept in English).
const FEATURES: [string, TextKey][] = [
  ['MCP tools', 'show.featMcp'], ['Agents as tools', 'show.featAgents'], ['Skills', 'show.featSkills'],
  ['Hooks', 'show.featHooks'], ['Steering', 'show.featSteering'], ['Graph', 'show.featGraph'],
  ['Evals', 'show.featEvals'], ['AgentCore Runtime', 'show.featRuntime'],
]

/** /how-it-works: how a warning is decided (live from rules/), then how the system is built. */
export function HowPage() {
  const { t } = useLanguage()
  return (
    <>
      <PageHead kicker={t('site.navHow')} title={t('site.howTitle')} lede={t('site.howLede')} />
      <section className="l-section" id="decide">
        <div className="wrap">
          <SectionTitle kicker={t('site.decideKicker')} title={t('show.decideTitle')} lede={t('show.decideLede')} />
          <RulesDiagram />
        </div>
      </section>
      <section className="l-section l-band" id="built">
        <div className="wrap stack" style={{ gap: 22 }}>
          <SectionTitle kicker={t('site.awsKicker')} title={t('show.builtTitle')} lede={t('show.builtLede')} />
          <FlowDiagram />
          <div className="stack" style={{ gap: 10 }}>
            <h3 className="h-mid">{t('show.strandsTitle')}</h3>
            <ul className="features">
              {FEATURES.map(([name, desc]) => <li key={name}><b className="mono" lang="en">{name}</b><span>{t(desc)}</span></li>)}
            </ul>
          </div>
          <p className="rule-tile"><b>{t('show.rule1b')}</b> {t('show.rule1t')}</p>
        </div>
      </section>
    </>
  )
}

const TOOLS: [string, TextKey][] = [
  ['find_place', 'site.toolFindPlace'], ['resolve_place', 'site.toolResolvePlace'], ['hazard_outlook', 'site.toolOutlook'],
  ['official_alerts', 'site.toolOfficial'], ['find_shelters', 'site.toolShelters'], ['backtest', 'site.toolBacktest'],
  ['cap_alerts', 'site.toolCap'], ['message_policy', 'site.toolPolicy'],
]

const CLAUDE_CONFIG = `{
  "mcpServers": {
    "weatherwise": {
      "command": "uv",
      "args": ["run", "--directory", "/path/to/weatherwise",
               "python", "-m", "weatherwise.mcp_server.server"]
    }
  }
}`

/** /developers: the eight tools as an open MCP server, and how to plug them in. */
export function DevelopersPage() {
  const { t } = useLanguage()
  return (
    <>
      <PageHead kicker={t('site.navDevelopers')} title={t('show.devTitle')} lede={t('show.devBody')}>
        <div className="l-ctas">
          <a href={REPO} target="_blank" rel="noreferrer" className="btn big">{t('site.readCode')}</a>
          <Link href="/how-it-works" className="btn big secondary">{t('site.navHow')}</Link>
        </div>
      </PageHead>
      <section className="l-section">
        <div className="wrap">
          <SectionTitle kicker={t('site.toolsKicker')} title={t('site.toolsTitle')} />
          <ul className="tools">
            {TOOLS.map(([name, desc]) => <li key={name}><b className="mono" lang="en">{name}</b><span>{t(desc)}</span></li>)}
          </ul>
        </div>
      </section>
      <section className="l-dark">
        <div className="wrap dev-grid">
          <div className="stack" style={{ gap: 10 }}>
            <h3><Icon name="send" size={20} /> {t('site.runIt')}</h3>
            <pre className="code mono" lang="en">{`uv run python -m weatherwise.mcp_server.server
# or over HTTP
uv run python -m weatherwise.mcp_server.server --http`}</pre>
          </div>
          <div className="stack" style={{ gap: 10 }}>
            <h3><Icon name="chat" size={20} /> {t('site.connectClaude')}</h3>
            <pre className="code mono" lang="en">{CLAUDE_CONFIG}</pre>
          </div>
        </div>
      </section>
    </>
  )
}

// Who it is for, each with the way in.
const AUDIENCES: { icon: IconName; title: TextKey; body: TextKey; cta: TextKey; href: string }[] = [
  { icon: 'plant', title: 'site.forFamilies', body: 'site.forFamiliesBody', cta: 'site.openApp', href: '/app' },
  { icon: 'shield', title: 'site.forPartners', body: 'site.forPartnersBody', cta: 'site.talkToUs', href: TEAM[0].links[0].href },
  { icon: 'send', title: 'site.forDevelopers', body: 'site.forDevelopersBody', cta: 'site.seeTools', href: '/developers' },
]

const ROADMAP: [TextKey, TextKey][] = [['site.now', 'site.nowBody'], ['site.next', 'site.nextBody'], ['site.later', 'site.laterBody']]

/** /about: who is building it and why, where it goes next, and how to work with us. */
export function AboutPage() {
  const { t } = useLanguage()
  return (
    <>
      <PageHead kicker={t('site.navAbout')} title={t('site.aboutTitle')} lede={t('site.teamLede')} />
      <section className="l-section">
        <div className="wrap">
          <SectionTitle kicker={t('site.teamKicker')} title={t('site.teamTitle')} />
          <div className="team">{TEAM.map((m) => <Person key={m.name} m={m} />)}</div>
        </div>
      </section>
      <section className="l-section l-band">
        <div className="wrap">
          <SectionTitle kicker={t('site.roadmapKicker')} title={t('site.roadmapTitle')} />
          <ol className="roadmap">
            {ROADMAP.map(([when, what], i) => (
              <li key={when} className={i === 0 ? 'now' : ''}><b>{t(when)}</b><span>{t(what)}</span></li>
            ))}
          </ol>
        </div>
      </section>
      <section className="l-section">
        <div className="wrap">
          <SectionTitle kicker={t('site.workWithUs')} title={t('site.whoTitle')} />
          <div className="audiences">
            {AUDIENCES.map((a) => (
              <article key={a.title}>
                <span className="trust-icon"><Icon name={a.icon} size={24} /></span>
                <h3>{t(a.title)}</h3>
                <p>{t(a.body)}</p>
                {a.href.startsWith('/')
                  ? <Link href={a.href} className="more">{t(a.cta)} <Icon name="send" size={18} /></Link>
                  : <a href={a.href} target="_blank" rel="noreferrer" className="more">{t(a.cta)} <Icon name="send" size={18} /></a>}
              </article>
            ))}
          </div>
        </div>
      </section>
    </>
  )
}
