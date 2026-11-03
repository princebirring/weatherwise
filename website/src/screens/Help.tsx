import { api } from '../api'
import { Icon } from '../components/Icon'
import { Helplines } from '../components/Shell'
import { useAsync } from '../components/useAsync'
import { Link } from '../router'
import { useLanguage } from '../text'
import type { SavedPlace } from '../types'

/** Help: one tap to every helpline, the nearest safe place, and "send my location to family". */
export function Help({ place, flood }: { place: SavedPlace; flood: boolean }) {
  const { t } = useLanguage()
  const kind = flood ? 'flood' : 'heat'
  const shelters = useAsync(() => api.shelters(place.lat, place.lon, kind), `${place.lat},${place.lon},${kind}`)
  const nearest = shelters.data?.places[0]

  const sendLocation = () => {
    const text = t('help.locationText', `${place.name} https://maps.google.com/?q=${place.lat},${place.lon}`)
    if (navigator.share) void navigator.share({ text }).catch(() => {})
    else window.open(`https://wa.me/?text=${encodeURIComponent(text)}`, '_blank', 'noopener')
  }

  return (
    <main className="app-main">
      <h1 className="h-big" style={{ fontSize: 30 }}>{t('help.title')}</h1>
      <Helplines big />

      <section className="stack" style={{ gap: 10 }}>
        {nearest && <h2 className="h-mid">{t('help.nearest')}</h2>}
        {nearest && (
          <article className="place-card">
            <div className="row">
              <span className="place-icon"><Icon name="home" size={30} /></span>
              <span className="stack" style={{ gap: 0 }}><b>{nearest.name}</b><span>{t('shelter.km', nearest.km)}</span></span>
            </div>
            <a href={`tel:${nearest.contact || shelters.data?.helpline.disaster || '1077'}`} className="btn">{t('shelter.callFirst')}</a>
          </article>
        )}
        <Link href={`/app/${kind}`} className="btn big secondary"><Icon name="home" size={26} />{t('help.seeSafePlaces')}</Link>
      </section>

      <button type="button" className="btn big share" onClick={sendLocation}><Icon name="pin" size={26} />{t('help.sendLocation')}</button>
      <Link href="/app/flood" className="btn big secondary"><Icon name="waves" size={26} />{t('help.prepareFlood')}</Link>
      <p className="small" style={{ textAlign: 'center' }}>{t('shell.notOfficial')}</p>
    </main>
  )
}
