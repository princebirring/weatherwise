import { useEffect, type ComponentType } from 'react'
import { usePath } from '../router'
import { useLanguage } from '../text'
import type { TextKey } from '../text/en'
import { Landing } from './site/Landing'
import { DevelopersPage, HowPage, ProofPage } from './site/Pages'
import { SiteLayout } from './site/SiteLayout'

// The public site for judges, partners and developers: a short landing page, and one page each
// for the proof, how it works, and the open tools. The farmer app lives under /app.
const PAGES: Record<string, { page: ComponentType; title?: TextKey }> = {
  '/': { page: Landing },
  '/proof': { page: ProofPage, title: 'site.navProof' },
  '/how-it-works': { page: HowPage, title: 'site.navHow' },
  '/developers': { page: DevelopersPage, title: 'site.navDevelopers' },
}

export function Showcase() {
  const { t } = useLanguage()
  const path = usePath()
  const known = PAGES[path]
  const { page: Page, title } = known ?? PAGES['/']

  useEffect(() => {
    if (!known) window.history.replaceState(null, '', '/') // unknown public path: the landing page
  }, [known])
  useEffect(() => {
    document.title = title ? `${t(title)} · ${t('brand.name')}` : `${t('brand.name')}: ${t('site.titleTail')}`
  }, [title, t])

  return <SiteLayout><Page /></SiteLayout>
}
