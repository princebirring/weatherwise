import { useEffect, useState, type MouseEvent } from 'react'
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

  useEffect(() => {
    if (!note) return
    const timer = setTimeout(() => setNote(null), NOTE_MS)
    return () => clearTimeout(timer)
  }, [note])

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
    <figure className="phone-demo">
      <div className="phone" role="region" aria-label={t('show.demoLabel')}>
        <EmbeddedRouter value={{ path, go }}>
          <div className="phone-screen" onClickCapture={intercept}>
            <div className="phone-status"><span>9:41</span><span className="phone-notch" /><span>4G</span></div>
            <div className="phone-scroll" key={`${tab}-${path}`}>
              {!group && <AppHeader place={place} checked={data.data?.outlook.issue_date} />}
              {screen}
            </div>
            {note && <p className="phone-note" role="status">{note}</p>}
            <TabBar />
          </div>
        </EmbeddedRouter>
      </div>
      <div className="phone-tabs" role="tablist" aria-label={t('show.demoLabel')}>
        {TABS.map((x, i) => (
          <button key={x.tab} type="button" role="tab" aria-selected={i === tab} onClick={() => pick(i)}>{t(x.tab)}</button>
        ))}
      </div>
    </figure>
  )
}
