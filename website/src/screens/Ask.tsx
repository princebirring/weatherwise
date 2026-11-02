import { useRef, useState, type FormEvent } from 'react'
import { api, ApiError } from '../api'
import { Icon } from '../components/Icon'
import { ErrorBox, Helplines, ScreenHeader } from '../components/Shell'
import { Link } from '../router'
import { saved } from '../storage'
import { useLanguage } from '../text'
import type { ChatReply, SavedPlace, Status } from '../types'

interface Turn {
  question: string
  reply?: ChatReply
  error?: ApiError
}

/** Chat with the same agent team as WhatsApp. Each reply can show how it was made. */
export function Ask({ place, status }: { place: SavedPlace; status: Status | null }) {
  const { t, language } = useLanguage()
  const [turns, setTurns] = useState<Turn[]>([])
  const [draft, setDraft] = useState('')
  const [busy, setBusy] = useState(false)
  const [open, setOpen] = useState<number | null>(null)
  const input = useRef<HTMLInputElement>(null)
  const max = status?.limits.max_message_chars ?? 500
  const offline = status !== null && !status.agents_ready

  const send = async (question: string) => {
    const q = question.trim()
    if (!q || busy || offline) return
    setDraft('')
    setBusy(true)
    const index = turns.length
    setTurns((ts) => [...ts, { question: q }])
    try {
      const reply = await api.chat(saved.chatSession(), q, language, place)
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
              {!turn.reply && !turn.error && <div className="loading" role="status"><span className="spinner" />{t('ask.thinking')}</div>}
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
