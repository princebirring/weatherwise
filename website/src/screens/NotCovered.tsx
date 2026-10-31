import { Icon } from '../components/Icon'
import { LanguagePicker } from '../components/Shell'
import { Link } from '../router'
import { useLanguage } from '../text'

/** A place outside every country we have rules for. No helpline numbers: ours would be wrong there. */
export function NotCovered() {
  const { t } = useLanguage()
  return (
    <main className="app-main start">
      <div className="row" style={{ justifyContent: 'flex-end' }}><LanguagePicker /></div>
      <section className="hero-card lv-missing" role="status">
        <div className="hero-icon"><Icon name="pin" size={56} /></div>
        <h1>{t('notCovered.title')}</h1>
        <p>{t('notCovered.body')}</p>
      </section>
      <Link href="/app/place" className="btn big">{t('notCovered.another')}</Link>
    </main>
  )
}
