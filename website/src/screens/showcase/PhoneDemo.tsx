import { useEffect, useRef, useState, type MouseEvent } from 'react'
import { AppHeader, TabBar } from '../../components/Shell'
import type { Async } from '../../components/useAsync'
import { GROUPS, type HazardGroup } from '../../hazards'
import { EmbeddedRouter } from '../../router'
import { useGuidance, useLanguage } from '../../text'
import type { TextKey } from '../../text/en'
import { HazardPage } from '../Hazard'
import { Help } from '../Help'
import { Home } from '../Home'
import { demoData, demoPlace, NO_OFFICIAL, type Story } from './demo'

// The stories under the phone, each with the app screen it opens on.
const TABS: { story: Story; path: string; tab: TextKey }[] = [
  { story: 'heat', path: '/app', tab: 'show.tabHeat' },
  { story: 'heat', path: '/app/heat', tab: 'show.tabAdvice' },
  { story: 'flood', path: '/app/flood', tab: 'today.floodGuide' },
  { story: 'urgent', path: '/app', tab: 'show.zoneUrgent' },
]
const NOTE_MS = 2600
// It plays the stories on its own (and scrolls each a little) until someone touches it, then
// picks up again after a quiet spell. Never for people who ask their device for less motion.
const STORY_MS = 5500
const SCROLL_AFTER_MS = 2000
const RESUME_MS = 20_000
const allowsMotion = () => typeof window.matchMedia === 'function' && !window.matchMedia('(prefers-reduced-motion: reduce)').matches

const loaded = <T,>(data: T): Async<T> => ({ data, error: null, loading: false, retry: () => {} })

/** The real app screens (Today, each danger's page, Help) in a phone, run on a sample forecast,
 *  so the landing page always shows the app as it is. Taps move the phone, not the page; nothing
 *  here calls or shares: on a laptop, those buttons say what they would do on a phone. */
export function PhoneDemo() {
  const { t } = useLanguage()
  const guidance = useGuidance()
  const [tab, setTab] = useState(0)
  const [path, setPath] = useState(TABS[0].path)
  const [note, setNote] = useState<string | null>(null)
  const [playing, setPlaying] = useState(allowsMotion)
  const [touched, setTouched] = useState(0) // bumps on every touch, to restart the quiet spell
  const figure = useRef<HTMLElement>(null)
  const scroller = useRef<HTMLDivElement>(null)

  useEffect(() => {
    if (!note) return
    const timer = setTimeout(() => setNote(null), NOTE_MS)
    return () => clearTimeout(timer)
  }, [note])

  // Next story every few seconds, a gentle scroll inside each; only while the phone is on screen.
  useEffect(() => {
    if (!playing) return
    const onScreen = () => {
      const r = figure.current?.getBoundingClientRect()
      const inView = !r || r.height === 0 || (r.bottom > 0 && r.top < window.innerHeight) // no layout (tests): treat as shown
      return inView && document.visibilityState === 'visible'
    }
    const scroll = setTimeout(() => { if (onScreen()) scroller.current?.scrollTo?.({ top: 240, behavior: 'smooth' }) }, SCROLL_AFTER_MS)
    const next = setTimeout(() => {
      if (!onScreen()) { setTouched((n) => n + 1); return } // wait, and try again
      const i = (tab + 1) % TABS.length
      setTab(i); setPath(TABS[i].path); setNote(null)
    }, STORY_MS)
    return () => { clearTimeout(scroll); clearTimeout(next) }
  }, [playing, tab, path, touched])

  // After a touch, hand back control for a while, then play again.
  useEffect(() => {
    if (playing || !allowsMotion()) return
    const resume = setTimeout(() => setPlaying(true), RESUME_MS)
    return () => clearTimeout(resume)
  }, [playing, touched])
  const hold = () => { setPlaying(false); setTouched((n) => n + 1) }

  if (!guidance) return null
  const { story } = TABS[tab]
  const place = demoPlace(story)
  const data = loaded(demoData(story))

  const pick = (i: number) => { setTab(i); setPath(TABS[i].path); setNote(null) }
  const go = (href: string) => {
    const to = href.split(/[?#]/)[0]
    if (to === '/app/ask') setNote(t('show.demoAsk'))
    else if (to.startsWith('/app') && to !== '/app/place') { setPath(to); setNote(null) }
  }
  // Calls and shares stay on the page: say what they would do instead.
  const intercept = (e: MouseEvent) => {
    const target = e.target as HTMLElement
    const tel = target.closest<HTMLAnchorElement>('a[href^="tel:"]')
    const share = target.closest('.share')
    if (!tel && !share) return
    e.preventDefault()
    e.stopPropagation()
    setNote(tel ? t('show.demoCall', tel.getAttribute('href')!.slice(4)) : t('site.demoShare'))
  }

  const group = GROUPS.find((g) => path === `/app/${g}`) as HazardGroup | undefined
  let screen
  if (group) screen = <HazardPage key={group} group={group} place={place} data={data} />
  else if (path === '/app/help') screen = <Help place={place} flood={story !== 'heat'} />
  else screen = <Home place={place} data={data} official={loaded(NO_OFFICIAL)} offline={false} install={null} />

  return (
    <figure className="phone-demo" ref={figure} onPointerDown={hold} onKeyDown={hold} onWheel={hold}>
      <div className="phone" role="region" aria-label={t('show.demoLabel')}>
        <EmbeddedRouter value={{ path, go }}>
          <div className="phone-screen" onClickCapture={intercept}>
            <div className="phone-status"><span>9:41</span><span className="phone-notch" /><span>4G</span></div>
            <div className="phone-scroll" key={`${tab}-${path}`} ref={scroller}>
              {!group && <AppHeader place={place} checked={data.data?.outlook.issue_date} />}
              {screen}
            </div>
            {note && <p className="phone-note" role="status">{note}</p>}
            <TabBar />
          </div>
        </EmbeddedRouter>
      </div>
      <div className={`phone-tabs ${playing ? 'playing' : ''}`} role="tablist" aria-label={t('show.demoLabel')}>
        {TABS.map((x, i) => (
          <button key={x.tab} type="button" role="tab" aria-selected={i === tab} onClick={() => pick(i)}>{t(x.tab)}</button>
        ))}
      </div>
    </figure>
  )
}
