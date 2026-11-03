import type { ReactNode } from 'react'
import { Icon, Logo } from '../../components/Icon'
import { LanguagePicker } from '../../components/Shell'
import { Link, usePath } from '../../router'
import { useLanguage } from '../../text'
import type { TextKey } from '../../text/en'
import { LICENSE_URL, REPO, TEAM } from './team'
import './site.css'

export const NAV: [string, TextKey][] = [
  ['/how-it-works', 'site.navHow'], ['/impact', 'site.navImpact'], ['/developers', 'site.navDevelopers'], ['/about', 'site.navAbout'],
]

/** The frame of every public page: one header with the pages, one footer with the people and sources. */
export function SiteLayout({ children }: { children: ReactNode }) {
  const { t } = useLanguage()
  const path = usePath()
  return (
    <div className="site">
      <header className="site-top">
        <div className="wrap site-top-row">
          <Link href="/" className="site-brand" aria-label={t('brand.name')}><Logo size={34} /><b>{t('brand.name')}</b></Link>
          <nav className="site-nav" aria-label={t('show.sections')}>
            {NAV.map(([href, key]) => (
              <Link key={href} href={href} aria-current={href === path ? 'page' : undefined}>{t(key)}</Link>
            ))}
            {/* The code is part of the entry, so it is one tap from every page. */}
            <a href={REPO} target="_blank" rel="noreferrer">GitHub</a>
          </nav>
          <div className="site-top-actions">
            <LanguagePicker />
            <a href={REPO} target="_blank" rel="noreferrer" className="site-gh" aria-label={t('site.githubAria')} title={t('site.githubAria')}>
              <Icon name="github" size={22} />
            </a>
            <Link href="/app" className="btn">{t('site.openApp')}</Link>
          </div>
        </div>
      </header>
      <main>{children}</main>
      <SiteFooter />
    </div>
  )
}

function SiteFooter() {
  const { t } = useLanguage()
  return (
    <footer className="site-foot">
      <div className="wrap site-foot-grid">
        <div className="site-foot-brand">
          <span className="site-brand"><Logo size={30} /><b>{t('brand.name')}</b></span>
          <p>{t('site.headline')}</p>
          <p className="site-foot-safety"><b>{t('show.footerNotOfficial')}</b> {t('show.footerFollow')}</p>
        </div>
        <nav aria-label={t('site.footProduct')}>
          <b>{t('site.footProduct')}</b>
          <Link href="/app">{t('site.openApp')}</Link>
          {NAV.slice(0, 3).map(([href, key]) => <Link key={href} href={href}>{t(key)}</Link>)}
        </nav>
        <nav aria-label={t('site.navAbout')}>
          <b>{t('site.navAbout')}</b>
          {TEAM.map((m) => <a key={m.name} href={m.links[0].href} target="_blank" rel="noreferrer">{m.name}</a>)}
          <a href={REPO} target="_blank" rel="noreferrer">{t('site.sourceCode')}</a>
          <a href={LICENSE_URL} target="_blank" rel="noreferrer">{t('site.license')}</a>
        </nav>
      </div>
      <div className="wrap site-foot-credits">{t('show.footerSources')}</div>
    </footer>
  )
}

/** The top of an inner page: where you are, in one line, and why it matters. */
export function PageHead({ kicker, title, lede, children }: { kicker: string; title: string; lede?: string; children?: ReactNode }) {
  return (
    <section className="page-head">
      <div className="wrap">
        <span className="eyebrow">{kicker}</span>
        <h1>{title}</h1>
        {lede && <p>{lede}</p>}
        {children}
      </div>
    </section>
  )
}

export function SectionTitle({ kicker, title, lede, id }: { kicker: string; title: string; lede?: string; id?: string }) {
  return (
    <div className="sec-title">
      <span className="eyebrow">{kicker}</span>
      <h2 id={id}>{title}</h2>
      {lede && <p>{lede}</p>}
    </div>
  )
}
