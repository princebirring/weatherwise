import { useRef, useState, type FormEvent } from 'react'
import { api, ApiError } from '../api'
import { Icon } from '../components/Icon'
import { ErrorBox, Helplines, ScreenHeader } from '../components/Shell'
import { Link } from '../router'
import { saved } from '../storage'
import { useLanguage } from '../text'
import type { TextKey } from '../text/en'
import type { ChatProgress, ChatReply, SavedPlace, Status } from '../types'

interface Turn {
  question: string
  progress: ChatProgress[]
  reply?: ChatReply
  error?: ApiError
}

// What each tool means to the person waiting, in their words.
const STEP_TEXT: Record<string, TextKey> = {
  find_place: 'ask.step.place', resolve_place: 'ask.step.place',
  hazard_outlook: 'ask.step.forecast', official_alerts: 'ask.step.official', find_shelters: 'ask.step.shelters',
  warning_agent: 'ask.step.advice', flood_guide_agent: 'ask.step.advice',
}

// A question can arrive with the link, from "Ask about this" on a danger page: it is put in the
// box for the person to send (or change), never sent on its own.
const linkedQuestion = (max: number) => (new URLSearchParams(window.location.search).get('q') ?? '').slice(0, max)

/** Chat with the same agent team as WhatsApp. Each reply can show how it was made. */
export function Ask({ place, status }: { place: SavedPlace; status: Status | null }) {
  const { t, language } = useLanguage()
  const [turns, setTurns] = useState<Turn[]>([])
  const max = status?.limits.max_message_chars ?? 500
  const [draft, setDraft] = useState(() => linkedQuestion(max))
  const [busy, setBusy] = useState(false)
  const [open, setOpen] = useState<number | null>(null)
  const input = useRef<HTMLInputElement>(null)
  const offline = status !== null && !status.agents_ready

  const send = async (question: string) => {
    const q = question.trim()
    if (!q || busy || offline) return
    setDraft('')
    setBusy(true)
    const index = turns.length
    setTurns((ts) => [...ts, { question: q, progress: [] }])
    const onProgress = (step: ChatProgress) =>
      setTurns((ts) => ts.map((x, i) => (i === index ? { ...x, progress: [...x.progress, step] } : x)))
    try {
      const reply = await api.chat(saved.chatSession(), q, language, place, onProgress)
      setTurns((ts) => ts.map((x, i) => (i === index ? { ...x, reply } : x)))
    } catch (e) {
      setTurns((ts) => ts.map((x, i) => (i === index ? { ...x, error: e as ApiError } : x)))
    } finally {
      setBusy(false)
      input.current?.focus()
    }
  }
  const submit = (e: FormEvent) => { e.preventDefault(); void send(draft) }

  return (
    <>
      <ScreenHeader back="/app" title={t('ask.title')} />
      <main className="app-main">
        <p className="small">{t('ask.about', place.name)}</p>
        {offline && (
          <section className="card stack" role="status">
            <b style={{ fontSize: 17 }}>{t('ask.offlineTitle')}</b>
            <p style={{ fontSize: 15 }}>{t('ask.offlineBody')}</p>
            <div className="row" style={{ flexWrap: 'wrap' }}>
              <Link href="/app" className="pill">{t('tabs.today')}</Link>
              <Link href="/app/heat" className="pill">{t('group.heat')}</Link>
              <Link href="/app/flood" className="pill">{t('group.flood')}</Link>
              <Link href="/app/dry" className="pill">{t('group.dry')}</Link>
            </div>
          </section>
        )}

        {!offline && turns.length === 0 && (
          <div className="row" style={{ flexWrap: 'wrap', gap: 8 }}>
            {(['ask.chip.hot', 'ask.chip.sow', 'ask.chip.shelter', 'ask.chip.flood'] as const).map((k) => (
              <button key={k} type="button" className="pill" onClick={() => void send(t(k))}>{t(k)}</button>
            ))}
          </div>
        )}

        <div className="chat" aria-live="polite">
          {turns.map((turn, i) => (
            <div key={i} className="chat">
              <p className="bubble me">{turn.question}</p>
              {!turn.reply && !turn.error && <Progress steps={turn.progress} />}
              {turn.error && (turn.error.kind === 'demo_busy'
                ? <p className="bubble bot">{t('ask.busy')}</p>
                : <ErrorBox error={turn.error} />)}
              {turn.reply && (
                <>
                  <div className="bubble bot">
                    {turn.reply.text}
                    {turn.reply.used_fallback && <p className="fine" style={{ marginTop: 6 }}>{t('ask.fallback')}</p>}
                  </div>
                  <button type="button" className="text-link" style={{ alignSelf: 'flex-start' }} aria-expanded={open === i}
                    onClick={() => setOpen(open === i ? null : i)}>
                    {open === i ? t('ask.hideHow') : t('ask.how')}
                  </button>
                  {open === i && <Steps reply={turn.reply} />}
                </>
              )}
            </div>
          ))}
        </div>

        <form className="composer" onSubmit={submit} style={{ marginTop: 'auto' }}>
          <label htmlFor="msg" className="sr-only">{t('ask.label')}</label>
          <input id="msg" ref={input} value={draft} onChange={(e) => setDraft(e.target.value)} maxLength={max}
            placeholder={t('ask.placeholder')} disabled={offline} autoComplete="off" enterKeyHint="send" />
          <button type="submit" className="round" aria-label={t('ask.send')} disabled={busy || offline || !draft.trim()}>
            <span style={{ color: '#FFFFFF', display: 'flex' }}><Icon name="send" size={20} /></span>
          </button>
        </form>
        <p className="fine" style={{ textAlign: 'center' }}>{t('ask.limit', max)}</p>
        <p className="fine">{t('shell.notOfficial')}</p>
        <Helplines />
      </main>
    </>
  )
}

/** While the agents work: what is done, and what is happening now. Once every tool has finished,
 *  the agent is writing, and the checker reads the answer before it is shown. */
function Progress({ steps }: { steps: ChatProgress[] }) {
  const { t } = useLanguage()
  const order: TextKey[] = []
  const running = new Map<TextKey, number>() // tools started and not yet finished, per line
  for (const s of steps) {
    const key = STEP_TEXT[s.tool] ?? 'ask.step.work'
    if (!order.includes(key)) order.push(key)
    running.set(key, (running.get(key) ?? 0) + (s.done ? -1 : 1))
  }
  const now = order.find((k) => (running.get(k) ?? 0) > 0)
  return (
    <div className="progress" role="status">
      {order.filter((k) => k !== now && (running.get(k) ?? 0) <= 0).map((k) => (
        <p key={k} className="done"><Icon name="check" size={16} />{t(k)}</p>
      ))}
      <p className="loading"><span className="spinner" />
        {now ? t(now) : order.length ? t('ask.step.answer') : t('ask.thinking')}</p>
    </div>
  )
}

function Steps({ reply }: { reply: ChatReply }) {
  const { t } = useLanguage()
  return (
    <div className="steps">
      <div className="head"><b>{t('ask.how')}</b><span>{t('ask.total', reply.seconds)}</span></div>
      {reply.steps.map((s, i) => (
        <div key={i}>
          <span className={`dot ${s.status === 'success' ? '' : 'error'}`} />
          <span style={{ flex: 1, minWidth: 0 }}><b>{s.agent}</b> · <span className="mono">{s.tool}</span></span>
          <span className="small">{s.seconds} s</span>
        </div>
      ))}
      <div>
        <span className={`dot ${reply.violations.length ? 'error' : ''}`} />
        <span style={{ flex: 1 }}>
          <b>Evaluator</b> · {reply.violations.length ? reply.violations.join('; ') : t('ask.passed')}
        </span>
      </div>
      <div className="fine">{t('ask.noLog')}</div>
    </div>
  )
}
