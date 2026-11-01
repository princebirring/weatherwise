import { useEffect, useState } from 'react'
import { weekday } from '../../hazards'
import { Icon } from '../../components/Icon'
import { useGuidance, useLanguage } from '../../text'
import type { TextKey } from '../../text/en'

const SHOW_MS = 4800
// One line under the phone for each screen: the story a judge should take away.
const CAPTIONS: TextKey[] = ['show.demo1', 'show.demo2', 'show.demo3', 'show.demo4']
// The week strip on the first screen: a hot spell building and easing (colours = warning levels).
const WEEK: [string, number][] = [['', 38], ['yellow', 41], ['orange', 44], ['orange', 45], ['yellow', 42], ['', 39], ['', 37]]

const isoDay = (daysAhead: number) => new Date(Date.now() + daysAhead * 86_400_000).toISOString().slice(0, 10)
const prefersReducedMotion = () =>
  typeof window !== 'undefined' && !!window.matchMedia?.('(prefers-reduced-motion: reduce)').matches

/** The farmer app in a phone: a heat warning days ahead, what to do, the flood guide, and "move now".
 *  Built from the app's own styles, words and safety advice (rules/languages), in the chosen
 *  language, so it shows exactly what the app says. A picture, not a control: inert. */
export function PhoneDemo() {
  const { t, language } = useLanguage()
  const g = useGuidance()
  const [screen, setScreen] = useState(0)
  const [paused, setPaused] = useState(prefersReducedMotion)

  useEffect(() => {
    if (paused) return
    const timer = setInterval(() => setScreen((s) => (s + 1) % CAPTIONS.length), SHOW_MS)
    return () => clearInterval(timer)
  }, [paused])

  if (!g) return null
  const when = `${weekday(isoDay(2), language)} – ${weekday(isoDay(3), language)}`

  return (
    <figure className="phone-demo" onMouseEnter={() => setPaused(true)} onMouseLeave={() => setPaused(prefersReducedMotion())}>
      <div className="phone" aria-hidden="true">
        <div className="phone-screen" inert>
          <div className="phone-status"><span>9:41</span><span className="phone-notch" /><span>4G</span></div>
          <div className="app-header"><span className="place"><b>{t('start.myLocation')}</b></span></div>
          <main className="app-main" key={screen}>
            {screen === 0 && (
              <>
                <section className="hero-card lv-orange">
                  <div className="hero-icon"><Icon name="heat" size={56} /></div>
                  <h1>{t('hazard.work_heat:danger')}</h1>
                  <p className="when">{when}</p>
                  <div className="chips"><span>{t('chip.feelsLike', 46)}</span><span>{t('likely.high')}</span></div>
                </section>
                <span className="btn big">{t('today.whatToDo')}</span>
                <ol className="week">
                  {WEEK.map(([level, temp], i) => (
                    <li key={i} className={level}><span className="wd">{weekday(isoDay(i), language)}</span><Icon name="sun" size={26} /><b>{temp}°</b></li>
                  ))}
                </ol>
              </>
            )}
            {screen === 1 && (
              <section className="todo-card">
                <div className="todo-icon warn"><Icon name="clock" size={72} /></div>
                <p className="todo-text">{g.work_heat.danger}</p>
                <span className="btn big danger">{t('todo.call108')}</span>
              </section>
            )}
            {screen === 2 && (
              <>
                <section className="hero-card lv-flood" style={{ padding: 18 }}>
                  <h1 style={{ fontSize: 24 }}>{t('flood.prepareTitle')}</h1>
                  <p>{t('flood.prepareBody')}</p>
                </section>
                <div className="dots">{g.flood_village.map((s, i) => <i key={s} className={i < 1 ? 'on' : i === 1 ? 'now' : ''} />)}</div>
                <section className="todo-card" style={{ minHeight: 0 }}>
                  <div className="todo-icon"><Icon name="waves" size={64} /></div>
                  <p className="todo-text">{g.flood_village[1]}</p>
                </section>
              </>
            )}
            {screen === 3 && (
              <section className="urgent">
                <span className="kicker">{t('flood.urgentTag')}</span>
                <p className="big">{g.flood_urgent}</p>
                <span className="btn big">{t('flood.call112')}</span>
                <span className="btn big outline">{t('flood.call1077')}</span>
              </section>
            )}
          </main>
          <nav className="tabbar">
            <span className={screen < 2 ? 'on' : ''}><Icon name="sun" size={26} />{t('tabs.today')}</span>
            <span><Icon name="home" size={26} />{t('tabs.safePlace')}</span>
            <span className="tab-help"><Icon name="phone" size={26} />{t('tabs.help')}</span>
          </nav>
        </div>
      </div>
      <figcaption>
        <span className="sr-only">{t('show.demoLabel')}: {CAPTIONS.map((k) => t(k)).join('; ')}</span>
        <span className="phone-caption" aria-hidden="true"><b>{screen + 1} / {CAPTIONS.length}</b> {t(CAPTIONS[screen])}</span>
        <span className="phone-dots" aria-hidden="true">
          {CAPTIONS.map((k, i) => (
            <button key={k} type="button" tabIndex={-1} className={i === screen ? 'on' : ''} aria-label={t(k)}
              onClick={() => { setScreen(i); setPaused(true) }} />
          ))}
        </span>
      </figcaption>
    </figure>
  )
}
