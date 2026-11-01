import { useEffect, useState } from 'react'
import { weekday } from '../../hazards'
import { Icon, type IconName } from '../../components/Icon'
import { useGuidance, useLanguage } from '../../text'
import type { TextKey } from '../../text/en'

type Screen = 'heat' | 'advice' | 'flood' | 'urgent' | 'help'

// The tabs above the phone, and one line saying what each screen shows.
const TABS: { screen: Screen; tab: TextKey; caption: TextKey }[] = [
  { screen: 'heat', tab: 'show.tabHeat', caption: 'show.demo1' },
  { screen: 'advice', tab: 'show.tabAdvice', caption: 'show.demo2' },
  { screen: 'flood', tab: 'today.floodGuide', caption: 'show.demo3' },
  { screen: 'urgent', tab: 'show.zoneUrgent', caption: 'show.demo4' },
]
// The week strip on the heat screen: a hot spell building and easing (colours = warning levels).
const WEEK: [string, number][] = [['', 38], ['yellow', 41], ['orange', 44], ['orange', 45], ['yellow', 42], ['', 39], ['', 37]]
const HEAT_ICONS: IconName[] = ['clock', 'home', 'cow'] // as on the app's What to do screen
const NOTE_MS = 2600

const isoDay = (daysAhead: number) => new Date(Date.now() + daysAhead * 86_400_000).toISOString().slice(0, 10)

/** The farmer app in a phone, working like the app: a heat warning days ahead, what to do card by
 *  card, the flood guide step by step, "move now", and the helplines. Built from the app's own
 *  styles, words and safety advice (rules/languages), in the chosen language. Nothing here calls
 *  anyone: on a laptop, a call button says what it would do on a phone. */
export function PhoneDemo() {
  const { t, language } = useLanguage()
  const g = useGuidance()
  const [screen, setScreen] = useState<Screen>('heat')
  const [card, setCard] = useState(0)
  const [step, setStep] = useState(0)
  const [note, setNote] = useState<string | null>(null)

  useEffect(() => {
    if (!note) return
    const timer = setTimeout(() => setNote(null), NOTE_MS)
    return () => clearTimeout(timer)
  }, [note])

  if (!g) return null
  const go = (s: Screen) => { setScreen(s); setCard(0); setStep(0); setNote(null) }
  const call = (number: string) => setNote(t('show.demoCall', number))

  // What to do: the same cards, in the same order, as the app's work-heat "danger" advice.
  const cards: { icon: IconName; label?: string; text: string; call108?: boolean }[] = [
    { icon: 'heat', text: g.work_heat.danger },
    ...g.heat.map((a, i) => ({ icon: HEAT_ICONS[i] ?? 'check', label: a.who, text: a.what })),
    { icon: 'alert', text: g.heatstroke, call108: true },
  ]
  const steps = g.flood_village
  const finished = step >= steps.length
  const caption = TABS.find((x) => x.screen === screen)?.caption

  return (
    <figure className="phone-demo">
      <div className="phone-tabs" role="tablist" aria-label={t('show.demoLabel')}>
        {TABS.map((x) => (
          <button key={x.tab} type="button" role="tab" aria-selected={x.screen === screen} onClick={() => go(x.screen)}>{t(x.tab)}</button>
        ))}
      </div>
      <div className="phone" role="region" aria-label={t('show.demoLabel')}>
        <div className="phone-screen">
          <div className="phone-status"><span>9:41</span><span className="phone-notch" /><span>4G</span></div>
          <div className="app-header"><span className="place"><b>{t('start.myLocation')}</b></span></div>
          <main className="app-main" key={`${screen}-${card}-${step}`}>
            {screen === 'heat' && (
              <>
                <section className="hero-card lv-orange">
                  <div className="hero-icon"><Icon name="heat" size={56} /></div>
                  <h1>{t('hazard.work_heat:danger')}</h1>
                  <p className="when">{`${weekday(isoDay(2), language)} – ${weekday(isoDay(3), language)}`}</p>
                  <div className="chips"><span>{t('chip.feelsLike', 46)}</span><span>{t('likely.high')}</span></div>
                </section>
                <button type="button" className="btn big" onClick={() => go('advice')}>{t('today.whatToDo')}</button>
                <ol className="week" aria-hidden="true">
                  {WEEK.map(([level, temp], i) => (
                    <li key={i} className={level}><span className="wd">{weekday(isoDay(i), language)}</span><Icon name="sun" size={26} /><b>{temp}°</b></li>
                  ))}
                </ol>
              </>
            )}

            {screen === 'advice' && (
              <>
                <div className="dots" aria-hidden="true">{cards.map((c, i) => <i key={c.text} className={i <= card ? 'on' : ''} />)}</div>
                <section className="todo-card" style={{ minHeight: 0 }}>
                  <div className={`todo-icon ${cards[card].call108 ? 'warn' : ''}`}><Icon name={cards[card].icon} size={64} /></div>
                  {cards[card].label && <p className="todo-label">{cards[card].label}</p>}
                  <p className="todo-text">{cards[card].text}</p>
                  {cards[card].call108 && <button type="button" className="btn big danger" onClick={() => call('108')}>{t('todo.call108')}</button>}
                </section>
                <div className="pair">
                  <button type="button" className="btn big secondary" disabled={card === 0} onClick={() => setCard(card - 1)}>{t('shell.back')}</button>
                  <button type="button" className="btn big" onClick={() => (card === cards.length - 1 ? go('heat') : setCard(card + 1))}>
                    {card === cards.length - 1 ? t('todo.done') : t('todo.next')}
                  </button>
                </div>
              </>
            )}

            {screen === 'flood' && (
              <>
                <section className="hero-card lv-flood" style={{ padding: 18 }}>
                  <h1 style={{ fontSize: 24 }}>{t('flood.prepareTitle')}</h1>
                  <p>{t('flood.prepareBody')}</p>
                </section>
                <div className="dots" aria-hidden="true">{steps.map((s, i) => <i key={s} className={i < step || finished ? 'on' : i === step ? 'now' : ''} />)}</div>
                <section className="todo-card" style={{ minHeight: 0 }}>
                  <div className="todo-icon"><Icon name={finished ? 'check' : 'waves'} size={64} /></div>
                  <p className="todo-text">{finished ? t('flood.allDone') : steps[step]}</p>
                </section>
                {finished
                  ? <button type="button" className="btn big secondary" onClick={() => setStep(0)}>{t('flood.startAgain')}</button>
                  : (
                    <div className="pair">
                      <button type="button" className="btn big secondary" disabled={step === 0} onClick={() => setStep(step - 1)}>{t('shell.back')}</button>
                      <button type="button" className="btn big" onClick={() => setStep(step + 1)}>{step === steps.length - 1 ? t('todo.done') : t('todo.next')}</button>
                    </div>
                  )}
              </>
            )}

            {screen === 'urgent' && (
              <section className="urgent">
                <span className="kicker">{t('flood.urgentTag')}</span>
                <p className="big">{g.flood_urgent}</p>
                <button type="button" className="btn big" onClick={() => call('112')}>{t('flood.call112')}</button>
                <button type="button" className="btn big outline" onClick={() => call('1077')}>{t('flood.call1077')}</button>
              </section>
            )}

            {screen === 'help' && (
              <>
                <h1 className="h-big" style={{ fontSize: 30 }}>{t('help.title')}</h1>
                <button type="button" className="call call-main" onClick={() => call('112')}>
                  <Icon name="phone" size={34} /><span><b>112</b>{t('help.emergency')}</span>
                </button>
                <div className="two">
                  <button type="button" className="call" onClick={() => call('108')}><b>108</b>{t('help.ambulance')}</button>
                  <button type="button" className="call" onClick={() => call('1077')}><b>1077</b>{t('help.disaster')}</button>
                </div>
              </>
            )}
          </main>
          {note && <p className="phone-note" role="status">{note}</p>}
          <nav className="tabbar">
            <button type="button" className={screen === 'heat' || screen === 'advice' ? 'on' : ''} onClick={() => go('heat')}><Icon name="sun" size={26} />{t('tabs.today')}</button>
            <button type="button" onClick={() => setNote(t('show.demoSafe'))}><Icon name="home" size={26} />{t('tabs.safePlace')}</button>
            <button type="button" className={`tab-help ${screen === 'help' ? 'on' : ''}`} onClick={() => go('help')}><Icon name="phone" size={26} />{t('tabs.help')}</button>
          </nav>
        </div>
      </div>
      <figcaption className="phone-caption">{caption ? t(caption) : t('show.demoHelp')}</figcaption>
    </figure>
  )
}
