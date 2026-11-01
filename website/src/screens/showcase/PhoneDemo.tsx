import { useEffect, useState } from 'react'
import { weekday } from '../../hazards'
import { Icon } from '../../components/Icon'
import { Helplines } from '../../components/Shell'
import { useGuidance, useLanguage } from '../../text'

const SCREENS = 3
const SHOW_MS = 4500

const isoDay = (daysAhead: number) => new Date(Date.now() + daysAhead * 86_400_000).toISOString().slice(0, 10)
const prefersReducedMotion = () =>
  typeof window !== 'undefined' && !!window.matchMedia?.('(prefers-reduced-motion: reduce)').matches

/** The farmer app in a phone, cycling Today → What to do → Help. Built from the app's own styles,
 *  words and safety advice (rules/languages), so it shows what the app says, in the chosen language.
 *  A picture, not a control: inert, with a caption for screen readers. */
export function PhoneDemo() {
  const { t, language } = useLanguage()
  const guidance = useGuidance()
  const [screen, setScreen] = useState(0)
  const [paused, setPaused] = useState(prefersReducedMotion)

  useEffect(() => {
    if (paused) return
    const timer = setInterval(() => setScreen((s) => (s + 1) % SCREENS), SHOW_MS)
    return () => clearInterval(timer)
  }, [paused])

  const firstAdvice = guidance?.heat[0]
  const when = `${weekday(isoDay(2), language)} – ${weekday(isoDay(4), language)}`
  const names = [t('tabs.today'), t('today.whatToDo'), t('tabs.help')]

  return (
    <figure className="phone-demo" onMouseEnter={() => setPaused(true)} onMouseLeave={() => setPaused(prefersReducedMotion())}>
      <div className="phone" aria-hidden="true">
        <div className="phone-screen" inert>
          <div className="phone-status"><span>9:41</span><span className="phone-notch" /><span>4G</span></div>
          <div className="app-header">
            <span className="place"><b>{t('start.myLocation')}</b></span>
          </div>
          <main className="app-main">
            {screen === 0 && (
              <>
                <section className="hero-card lv-orange">
                  <div className="hero-icon"><Icon name="heat" size={56} /></div>
                  <h1>{t('hazard.heat_wave')}</h1>
                  <p className="when">{when}</p>
                  <div className="chips"><span>{t('chip.upTo', 45)}</span><span>{t('likely.high')}</span></div>
                </section>
                <span className="btn big">{t('today.whatToDo')}</span>
                <span className="btn big secondary"><Icon name="speaker" size={26} />{t('listen.play')}</span>
              </>
            )}
            {screen === 1 && firstAdvice && (
              <section className="todo-card">
                <div className="todo-icon"><Icon name="clock" size={72} /></div>
                <p className="todo-label">{firstAdvice.who}</p>
                <p className="todo-text">{firstAdvice.what}</p>
              </section>
            )}
            {screen === 2 && (
              <>
                <h1 className="h-big" style={{ fontSize: 30 }}>{t('help.title')}</h1>
                <Helplines big />
              </>
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
        <span className="sr-only">{t('show.demoLabel')}: {names.join(', ')}</span>
        <span aria-hidden="true">{t('show.demoLabel')}</span>
        <span className="phone-dots" aria-hidden="true">
          {names.map((n, i) => (
            <button key={n} type="button" tabIndex={-1} className={i === screen ? 'on' : ''} onClick={() => { setScreen(i); setPaused(true) }}>{n}</button>
          ))}
        </span>
      </figcaption>
    </figure>
  )
}
