import { useState } from 'react'
import { weekday } from '../../hazards'
import { Icon } from '../../components/Icon'
import { useGuidance, useLanguage } from '../../text'
import type { TextKey } from '../../text/en'

// The four screens: the tab under the phone, and one line saying what the screen shows.
const SCREENS: { tab: TextKey; caption: TextKey }[] = [
  { tab: 'show.tabHeat', caption: 'show.demo1' },
  { tab: 'show.tabAdvice', caption: 'show.demo2' },
  { tab: 'today.floodGuide', caption: 'show.demo3' },
  { tab: 'show.zoneUrgent', caption: 'show.demo4' },
]
// The week strip on the first screen: a hot spell building and easing (colours = warning levels).
const WEEK: [string, number][] = [['', 38], ['yellow', 41], ['orange', 44], ['orange', 45], ['yellow', 42], ['', 39], ['', 37]]

const isoDay = (daysAhead: number) => new Date(Date.now() + daysAhead * 86_400_000).toISOString().slice(0, 10)

/** The farmer app in a phone: a heat warning days ahead, what to do, the flood guide, and "move now".
 *  Built from the app's own styles, words and safety advice (rules/languages), in the chosen
 *  language, so it shows exactly what the app says. The tabs under it switch screens. */
export function PhoneDemo() {
  const { t, language } = useLanguage()
  const g = useGuidance()
  const [screen, setScreen] = useState(0)

  if (!g) return null
  const when = `${weekday(isoDay(2), language)} – ${weekday(isoDay(3), language)}`

  return (
    <figure className="phone-demo">
      <div className="phone-tabs" role="tablist" aria-label={t('show.demoLabel')}>
        {SCREENS.map((sc, i) => (
          <button key={sc.tab} type="button" role="tab" aria-selected={i === screen} onClick={() => setScreen(i)}>{t(sc.tab)}</button>
        ))}
      </div>
      <div className="phone" role="tabpanel" aria-label={t(SCREENS[screen].caption)}>
        <div className="phone-screen">
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
                <button type="button" className="btn big" onClick={() => setScreen(1)}>{t('today.whatToDo')}</button>
                <ol className="week" aria-hidden="true">
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
      <figcaption className="phone-caption">{t(SCREENS[screen].caption)}</figcaption>
    </figure>
  )
}
