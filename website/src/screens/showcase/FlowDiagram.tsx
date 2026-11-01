import { useEffect, useState } from 'react'
import { useLanguage } from '../../text'
import type { TextKey } from '../../text/en'

// The deployed system (docs/deployment-todo.md, "The stack"), drawn once, with two journeys
// through it. Coordinates are in the SVG's own 1000 x 470 space.

type NodeId = 'phone' | 'ecs' | 'logs' | 'orch' | 'spec' | 'eval' | 'bedrock' | 'mcp' | 'rules' | 'data'

interface Box { x: number; y: number; w: number; h: number; title: string; sub?: TextKey | string; kind?: string }

const NODES: Record<NodeId, Box> = {
  phone: { x: 16, y: 200, w: 132, h: 80, title: 'show.nodePhone', kind: 'person' },
  ecs: { x: 200, y: 200, w: 150, h: 80, title: 'Amazon ECS', sub: 'show.nodeApi', kind: 'aws' },
  logs: { x: 200, y: 362, w: 150, h: 72, title: 'Amazon CloudWatch', sub: 'show.nodeLogs', kind: 'aws' },
  orch: { x: 396, y: 84, w: 170, h: 64, title: 'Strands', sub: 'show.nodeOrch', kind: 'agent' },
  spec: { x: 590, y: 84, w: 170, h: 64, title: 'Strands', sub: 'show.nodeSpec', kind: 'agent' },
  eval: { x: 396, y: 164, w: 170, h: 64, title: 'Strands', sub: 'show.nodeEval', kind: 'agent' },
  bedrock: { x: 590, y: 268, w: 170, h: 64, title: 'Amazon Bedrock', sub: 'Claude', kind: 'aws' },
  mcp: { x: 380, y: 362, w: 190, h: 76, title: 'MCP server', sub: 'show.nodeTools', kind: 'code' },
  rules: { x: 590, y: 368, w: 170, h: 64, title: 'rules/', sub: 'show.nodeRules', kind: 'code' },
  data: { x: 824, y: 196, w: 160, h: 128, title: 'show.nodeData', sub: 'Open-Meteo · NDMA SACHET · OpenStreetMap', kind: 'data' },
}

interface Step { path: string; nodes: NodeId[]; text: TextKey }

const FLOWS: Record<'today' | 'ask', Step[]> = {
  today: [
    { path: 'M148 240 L200 240', nodes: ['phone', 'ecs'], text: 'show.today1' },
    { path: 'M350 240 L365 240 L365 400 L380 400', nodes: ['ecs', 'mcp'], text: 'show.today2' },
    { path: 'M560 362 L560 350 L805 350 L805 260 L824 260', nodes: ['mcp', 'data'], text: 'show.today3' },
    { path: 'M570 400 L590 400', nodes: ['mcp', 'rules'], text: 'show.today4' },
    { path: 'M380 400 L365 400 L365 240 L148 240', nodes: ['mcp', 'ecs', 'phone'], text: 'show.today5' },
  ],
  ask: [
    { path: 'M148 240 L200 240', nodes: ['phone', 'ecs'], text: 'show.ask1' },
    { path: 'M350 240 L372 240 L372 116 L396 116', nodes: ['ecs', 'orch'], text: 'show.ask2' },
    { path: 'M566 116 L590 116', nodes: ['orch', 'spec'], text: 'show.ask3' },
    { path: 'M640 148 L640 250 L540 250 L540 350 L805 350 L805 260 L824 260', nodes: ['spec', 'mcp', 'data'], text: 'show.ask4' },
    { path: 'M700 148 L700 268', nodes: ['spec', 'bedrock'], text: 'show.ask5' },
    { path: 'M590 132 L578 132 L578 196 L566 196', nodes: ['spec', 'eval'], text: 'show.ask6' },
    { path: 'M396 196 L384 196 L384 240 L148 240', nodes: ['eval', 'ecs', 'phone'], text: 'show.ask7' },
  ],
}
const LOG_PATH = 'M275 280 L275 362'
const ALL_PATHS = [...new Set([...FLOWS.today, ...FLOWS.ask].map((s) => s.path))]
const STEP_MS = 2600

const reducedMotion = () => typeof window !== 'undefined' && !!window.matchMedia?.('(prefers-reduced-motion: reduce)').matches

export function FlowDiagram() {
  const { t } = useLanguage()
  const [flow, setFlow] = useState<'today' | 'ask'>('today')
  const [step, setStep] = useState(0)
  const [playing, setPlaying] = useState(() => !reducedMotion())
  const steps = FLOWS[flow]

  useEffect(() => {
    if (!playing) return
    const timer = setInterval(() => setStep((s) => (s + 1) % steps.length), STEP_MS)
    return () => clearInterval(timer)
  }, [playing, steps.length])

  const current = steps[step]
  const done = new Set(steps.slice(0, step).flatMap((s) => s.nodes))
  const active = new Set(current.nodes)
  const label = (k: string) => (k.startsWith('show.') ? t(k as TextKey) : k)
  const choose = (f: 'today' | 'ask') => { setFlow(f); setStep(0) }

  return (
    <div className="flow stack" style={{ gap: 14 }}>
      <div className="row" style={{ flexWrap: 'wrap', gap: 8 }}>
        <div className="tabs" role="tablist" aria-label={t('show.builtTitle')}>
          <button type="button" role="tab" aria-selected={flow === 'today'} onClick={() => choose('today')}>{t('show.flowToday')}</button>
          <button type="button" role="tab" aria-selected={flow === 'ask'} onClick={() => choose('ask')}>{t('show.flowAsk')}</button>
        </div>
        <button type="button" className="btn secondary flow-play" onClick={() => setPlaying(!playing)} aria-pressed={playing}>
          {playing ? t('show.pause') : t('show.play')}
        </button>
      </div>

      <div className="flow-canvas">
        <svg viewBox="0 0 1000 470" role="img" aria-label={steps.map((s, i) => `${i + 1}. ${t(s.text)}`).join(' ')}>
          <rect className="frame" x="176" y="16" width="620" height="440" rx="18" />
          <text className="frame-label" x="196" y="42">AWS · Mumbai (ap-south-1)</text>
          <rect className="frame inner" x="382" y="52" width="394" height="190" rx="14" />
          <text className="frame-label" x="398" y="74">Amazon Bedrock AgentCore Runtime</text>

          {ALL_PATHS.map((d) => <path key={d} d={d} className="edge" />)}
          <path d={LOG_PATH} className="edge logs" />
          <path key={`${flow}-${step}`} d={current.path} className="edge live" />

          {(Object.entries(NODES) as [NodeId, Box][]).map(([id, n]) => (
            <g key={id} className={`node ${n.kind ?? ''} ${active.has(id) ? 'active' : done.has(id) ? 'done' : ''}`}>
              <rect x={n.x} y={n.y} width={n.w} height={n.h} rx="12" />
              <foreignObject x={n.x} y={n.y} width={n.w} height={n.h}>
                <div className="node-text">
                  <b lang={n.title.startsWith('show.') ? undefined : 'en'}>{label(n.title)}</b>
                  {n.sub && <span lang={n.sub.startsWith('show.') ? undefined : 'en'}>{label(n.sub)}</span>}
                </div>
              </foreignObject>
            </g>
          ))}

          {!reducedMotion() && (
            <circle key={`dot-${flow}-${step}`} r="7" className="flow-dot">
              <animateMotion dur="1.4s" fill="freeze" path={current.path} />
            </circle>
          )}
        </svg>
      </div>

      <ol className="flow-steps">
        {steps.map((s, i) => (
          <li key={s.text}>
            <button type="button" className={i === step ? 'on' : i < step ? 'done' : ''} aria-current={i === step ? 'step' : undefined}
              onClick={() => { setStep(i); setPlaying(false) }}>
              <span className="n">{i + 1}</span>{t(s.text)}
            </button>
          </li>
        ))}
      </ol>
    </div>
  )
}
