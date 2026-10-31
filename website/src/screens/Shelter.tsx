import { useState } from 'react'
import { api } from '../api'
import { shortDate } from '../hazards'
import { Icon } from '../components/Icon'
import { ErrorBox, Helplines, Loading } from '../components/Shell'
import { useAsync } from '../components/useAsync'
import { useGuidance, useLanguage } from '../text'
import type { SavedPlace } from '../types'

type Kind = 'heat' | 'flood'

/** Part 2: nearest verified cooling place (heat) or shelter (flood). Flood: names only, no routes.
 *  Sentences come from the language files; the server's facts (search_km, health_status) fill them. */
export function Shelter({ place, initialKind }: { place: SavedPlace; initialKind: Kind }) {
  const { t, language } = useLanguage()
  const guidance = useGuidance()
  const [kind, setKind] = useState<Kind>(initialKind)
  const result = useAsync(() => api.shelters(place.lat, place.lon, kind), `${place.lat},${place.lon},${kind}`)
  const r = result.data
  const disaster = r?.helpline.disaster ?? '1077'

  return (
    <main className="app-main">
      <h1 className="h-big" style={{ fontSize: 28 }}>{t('shelter.title')}</h1>
      <div className="segmented" role="group" aria-label={t('shelter.kind')}>
        <button type="button" aria-pressed={kind === 'heat'} onClick={() => setKind('heat')}><Icon name="heat" size={24} />{t('shelter.heat')}</button>
        <button type="button" aria-pressed={kind === 'flood'} onClick={() => setKind('flood')}><Icon name="waves" size={24} />{t('shelter.flood')}</button>
      </div>

      {kind === 'flood' && guidance && <p className="alert-box blue big-note"><b>{guidance.flood_safety_line}</b></p>}

      {result.loading && <Loading label={t('state.loadingShelters')} />}
      {result.error && <ErrorBox error={result.error} retry={result.retry} />}
      {r && (
        <div className="stack" style={{ gap: 12 }}>
          {r.places.map((p) => (
            <article key={p.name} className="place-card">
              <div className="row">
                <span className="place-icon"><Icon name="home" size={30} /></span>
                <span className="stack" style={{ gap: 0 }}>
                  <b>{p.name}</b>
                  <span>{t('shelter.km', p.km)} · {t('shelter.checkedOn', shortDate(p.checked_on, language))}</span>
                </span>
              </div>
              <div className="pair">
                <a href={`tel:${p.contact || disaster}`} className="btn">{t('shelter.callFirst')}</a>
                {/* The server never sends a route for floods; this guard keeps it that way here too. */}
                {kind === 'heat' && p.directions_link && (
                  <a href={p.directions_link} target="_blank" rel="noopener noreferrer" className="btn secondary">{t('shelter.showWay')}</a>
                )}
              </div>
            </article>
          ))}

          {r.places.length === 0 && (
            <p className="card big-note">{t(kind === 'heat' ? 'shelter.noneNearHeat' : 'shelter.noneNearFlood', Math.round(r.search_km))}</p>
          )}
          {kind === 'flood' && <p className="big-note">{t('shelter.noRoute')}</p>}
          {r.stale_nearby > 0 && <p className="small">{t('shelter.stale', r.stale_nearby)}</p>}

          {r.health_facilities && r.health_facilities.length > 0 && (
            <section className="card stack" style={{ gap: 8 }}>
              <h2 className="h-mid">{t('shelter.healthTitle')}</h2>
              {r.health_facilities.map((h) => (
                <div key={h.name} className="row" style={{ justifyContent: 'space-between', fontSize: 17 }}>
                  <span>{h.name}</span><b style={{ flex: 'none' }}>{t('shelter.km', h.km)}</b>
                </div>
              ))}
              <span className="fine">{t('shelter.healthNote')}</span>
            </section>
          )}
          {r.health_status === 'unavailable' && <p className="card big-note">{t('shelter.healthUnavailable')}</p>}
        </div>
      )}

      <div style={{ marginTop: 'auto' }}><Helplines /></div>
    </main>
  )
}
