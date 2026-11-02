import type { ReactNode } from 'react'
import type { ApiError } from '../api'
import { shortDate } from '../hazards'
import { Link, usePath } from '../router'
import { LANGUAGE_NAMES, LANGUAGES, useLanguage } from '../text'
import type { Language, SavedPlace } from '../types'
import { Icon, type IconName } from './Icon'

/** 112 / 108 / 1077 as big call buttons. On every screen a person in danger can reach. */
export function Helplines({ big = false }: { big?: boolean }) {
  const { t, policy } = useLanguage()
  const h = policy?.helplines ?? { emergency: '112', ambulance: '108', disaster: '1077' }
  if (big) {
    return (
      <div className="stack" style={{ gap: 12 }}>
        <a href={`tel:${h.emergency}`} className="call call-main">
          <Icon name="phone" size={34} />
          <span><b>{h.emergency}</b>{t('help.emergency')}</span>
        </a>
        <div className="two">
          <a href={`tel:${h.ambulance}`} className="call"><b>{h.ambulance}</b>{t('help.ambulance')}</a>
          <a href={`tel:${h.disaster}`} className="call"><b>{h.disaster}</b>{t('help.disaster')}</a>
        </div>
      </div>
    )
  }
  const lines: [string, string][] = [[h.emergency, t('help.emergency')], [h.ambulance, t('help.ambulance')], [h.disaster, t('help.disaster')]]
  return (
    <div className="helplines">
      {lines.map(([n, label]) => <a key={n} href={`tel:${n}`}><b>{n}</b>{label}</a>)}
    </div>
  )
}

/** The one language switch. It changes every word on every screen, and is remembered. */
export function LanguagePicker() {
  const { language, setLanguage, t } = useLanguage()
  return (
    <label className="lang-pick">
      <span className="sr-only">{t('shell.language')}</span>
      <select value={language} onChange={(e) => setLanguage(e.target.value as Language)}>
        {LANGUAGES.map((l) => <option key={l} value={l} lang={l}>{LANGUAGE_NAMES[l]}</option>)}
      </select>
    </label>
  )
}

/** The place (tap to change it) and when its forecast was checked. */
export function AppHeader({ place, checked }: { place: SavedPlace; checked?: string }) {
  const { t, language } = useLanguage()
  return (
    <header className="app-header">
      <Link href="/app/place" className="place" aria-label={`${place.name}. ${t('today.changePlace')}`}>
        <b>{place.name}</b>
        <span>{checked ? t('today.checked', shortDate(checked, language)) : place.label || t('today.changePlace')}</span>
      </Link>
      <LanguagePicker />
    </header>
  )
}

/** A screen title with a back button and the language switch. */
export function ScreenHeader({ back, title }: { back: string; title: string }) {
  const { t } = useLanguage()
  return (
    <header className="app-header">
      <Link href={back} className="round-btn" aria-label={t('shell.back')}><Icon name="back" size={26} /></Link>
      <h1 className="screen-title">{title}</h1>
      <LanguagePicker />
    </header>
  )
}

// Three tabs: what is coming (and each danger's page under it), a question, and help now.
const TABS: { href: string; icon: IconName; key: 'tabs.today' | 'tabs.ask' | 'tabs.help'; help?: boolean }[] = [
  { href: '/app', icon: 'sun', key: 'tabs.today' },
  { href: '/app/ask', icon: 'chat', key: 'tabs.ask' },
  { href: '/app/help', icon: 'phone', key: 'tabs.help', help: true },
]

export function TabBar() {
  const { t } = useLanguage()
  const path = usePath()
  const today = path === '/app' || ['/app/heat', '/app/flood', '/app/dry'].includes(path)
  const active = (href: string) => (href === '/app' ? today : path.startsWith(href))
  return (
    <nav className="tabbar" aria-label={t('tabs.label')}>
      {TABS.map((tab) => (
        <Link key={tab.href} href={tab.href} className={tab.help ? 'tab-help' : undefined}
          aria-current={active(tab.href) ? 'page' : undefined}>
          <Icon name={tab.icon} size={28} />{t(tab.key)}
        </Link>
      ))}
    </nav>
  )
}

export function Loading({ label }: { label?: string }) {
  const { t } = useLanguage()
  return <div className="loading" role="status"><span className="spinner" />{label ?? t('state.loading')}</div>
}

/** Every failure ends with the helplines: a person in danger must never hit a dead end. */
export function ErrorBox({ error, retry, children }: { error: ApiError; retry?: () => void; children?: ReactNode }) {
  const { t } = useLanguage()
  return (
    <div className="card stack" role="alert">
      <p>{error.kind === 'offline' ? t('state.offline') : t('state.failed')}</p>
      {children}
      {retry && <button type="button" className="btn secondary" onClick={retry}>{t('state.retry')}</button>}
      <Helplines />
    </div>
  )
}
