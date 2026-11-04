import { useEffect, useState } from 'react'
import { Icon, type IconName } from '../../components/Icon'
import { useLanguage } from '../../text'
import type { TextKey } from '../../text/en'

// Two journeys through the deployed system (infra/ARCHITECTURE.md), one step at a
// time. Plain HTML, so it reads the same in every browser and on a phone.

interface Stage { icon: IconName; name: string; role: TextKey; text: TextKey; ai?: boolean }

const JOURNEYS: Record<'today' | 'ask', Stage[]> = {
  today: [
    { icon: 'phone', name: 'show.nodePhone', role: 'show.rolePlace', text: 'show.today1' },
    { icon: 'home', name: 'Amazon ECS', role: 'show.nodeApi', text: 'show.today2' },
    { icon: 'waves', name: 'MCP server', role: 'show.nodeTools', text: 'show.today3' },
    { icon: 'check', name: 'rules/', role: 'show.nodeRules', text: 'show.today4' },
    { icon: 'chat', name: 'show.nodePhone', role: 'show.roleLanguage', text: 'show.today5' },
  ],
  ask: [
    { icon: 'chat', name: 'show.nodePhone', role: 'show.roleQuestion', text: 'show.ask1' },
    { icon: 'send', name: 'Bedrock AgentCore', role: 'show.nodeRuntime', text: 'show.ask2', ai: true },
    { icon: 'shield', name: 'Orchestrator', role: 'show.nodeSpec', text: 'show.ask3', ai: true },
    { icon: 'waves', name: 'MCP server', role: 'show.nodeTools', text: 'show.ask4' },
    { icon: 'sun', name: 'Amazon Bedrock', role: 'show.roleModel', text: 'show.ask5', ai: true },
    { icon: 'check', name: 'Evaluator', role: 'show.roleEval', text: 'show.ask6', ai: true },
    { icon: 'phone', name: 'show.nodePhone', role: 'show.roleChecked', text: 'show.ask7' },
  ],
}

// The six AWS services, each with its one job.
const STACK: [string, TextKey][] = [
  ['Amazon Bedrock', 'show.jobBedrock'], ['Amazon Bedrock AgentCore', 'show.jobAgentCore'], ['Amazon ECS + ECR', 'show.jobEcs'],
  ['Amazon EventBridge Scheduler', 'show.jobScheduler'], ['Amazon S3', 'show.jobS3'], ['Amazon CloudWatch', 'show.nodeLogs'],
]

const STEP_MS = 3200

export function FlowDiagram() {
  const { t } = useLanguage()
  const [journey, setJourney] = useState<'today' | 'ask'>('today')
  const [step, setStep] = useState(0)
  // Steps move on by themselves until the person clicks one; then it stays where they chose.
  const [playing, setPlaying] = useState(true)
  const stages = JOURNEYS[journey]

  useEffect(() => {
    if (!playing) return
    const timer = setInterval(() => setStep((s) => (s + 1) % stages.length), STEP_MS)
    return () => clearInterval(timer)
  }, [playing, stages.length])

  const label = (k: string) => (k.startsWith('show.') ? t(k as TextKey) : k)
  const choose = (j: 'today' | 'ask') => { setJourney(j); setStep(0); setPlaying(true) }

  return (
    <div className="journey stack" style={{ gap: 16 }}>
      <div className="row" style={{ flexWrap: 'wrap', gap: 8 }}>
        <div className="tabs" role="tablist" aria-label={t('show.builtTitle')}>
          <button type="button" role="tab" aria-selected={journey === 'today'} onClick={() => choose('today')}>{t('show.flowToday')}</button>
          <button type="button" role="tab" aria-selected={journey === 'ask'} onClick={() => choose('ask')}>{t('show.flowAsk')}</button>
        </div>
        {journey === 'ask' && <span className="ai-key"><i />{t('show.aiStep')}</span>}
      </div>

      <ol className="journey-track" style={{ ['--n' as string]: stages.length }}>
        {stages.map((s, i) => (
          <li key={`${journey}-${i}`}>
            <button type="button" className={`stage ${s.ai ? 'ai' : ''} ${i === step ? 'on' : i < step ? 'done' : ''}`}
              aria-current={i === step ? 'step' : undefined} onClick={() => { setStep(i); setPlaying(false) }}>
              <span className="stage-n">{i + 1}</span>
              <span className="stage-icon"><Icon name={s.icon} size={26} /></span>
              <b lang={s.name.startsWith('show.') ? undefined : 'en'}>{label(s.name)}</b>
              <span className="stage-role">{t(s.role)}</span>
            </button>
          </li>
        ))}
      </ol>

      <p className="journey-caption" aria-hidden="true"><b>{step + 1}.</b> {t(stages[step].text)}</p>
      <ol className="sr-only">{stages.map((s, i) => <li key={i}>{t(s.text)}</li>)}</ol>

      <div className="stack-strip">
        <b>{t('show.stackTitle')}</b>
        <ul>{STACK.map(([name, job]) => <li key={name}><b lang="en">{name}</b><span>{t(job)}</span></li>)}</ul>
      </div>
    </div>
  )
}
