import { useEffect, type ComponentType } from 'react'
import { usePath } from '../router'
import { useLanguage } from '../text'
import type { TextKey } from '../text/en'
import { Landing } from './site/Landing'
import { AboutPage, DevelopersPage, HowPage, ImpactPage } from './site/Pages'
import { SiteLayout } from './site/SiteLayout'

// The public site for judges, partners and developers: a short landing page, and one page each
// for how it works, the impact, the open tools and the team. The farmer app lives under /app.
const PAGES: Record<string, { page: ComponentType; title?: TextKey }> = {
  '/': { page: Landing },
  '/how-it-works': { page: HowPage, title: 'site.navHow' },
  '/impact': { page: ImpactPage, title: 'site.navImpact' },
  '/developers': { page: DevelopersPage, title: 'site.navDevelopers' },
  '/about': { page: AboutPage, title: 'site.navAbout' },
}
// Pages that moved: links already shared still land in the right place.
const MOVED: Record<string, string> = { '/proof': '/impact', '/team': '/about' }

export function Showcase() {
  const { t } = useLanguage()
  const path = usePath()
  const target = MOVED[path] ?? path
  const known = PAGES[target]
  const { page: Page, title } = known ?? PAGES['/']

  useEffect(() => {
    // A moved page goes to its new address; an unknown one to the landing page.
    if (target !== path || !known) window.history.replaceState(null, '', known ? target + window.location.search + window.location.hash : '/')
  }, [path, target, known])
  useEffect(() => {
    document.title = title ? `${t(title)} · ${t('brand.name')}` : `${t('brand.name')}: ${t('site.titleTail')}`
  }, [title, t])

  return <SiteLayout><Page /></SiteLayout>
}
