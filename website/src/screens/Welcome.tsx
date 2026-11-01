import { useEffect, useState } from 'react'
import { api, ApiError } from '../api'
import { Icon, Logo } from '../components/Icon'
import { ErrorBox } from '../components/Shell'
import { navigate } from '../router'
import { LANGUAGE_NAMES, LANGUAGES, useLanguage } from '../text'
import type { PlaceCandidate, SavedPlace } from '../types'

const SEARCH_DELAY_MS = 400 // wait for a pause in typing before asking the server

/** Start: choose a language, then search the village (matches appear as you type) or use location. */
export function Welcome({ onPlace }: { onPlace: (p: SavedPlace) => void }) {
  const { t, language, setLanguage } = useLanguage()
  const [query, setQuery] = useState('')
  const [results, setResults] = useState<{ query: string; candidates: PlaceCandidate[] } | null>(null)
  const [error, setError] = useState<ApiError | null>(null)
  const [locating, setLocating] = useState(false)
  const [note, setNote] = useState<string | null>(null)
  const q = query.trim()

  useEffect(() => {
    if (q.length < 2) return
    let live = true
    const timer = setTimeout(() => {
      api.findPlace(q, language).then(
        (r) => live && (setResults({ query: q, candidates: r.candidates }), setError(null)),
        (e) => live && setError(e as ApiError),
      )
    }, SEARCH_DELAY_MS)
    return () => { live = false; clearTimeout(timer) }
  }, [q, language])

  const choose = (p: SavedPlace) => {
    onPlace(p)
    navigate('/app')
  }

  const locate = () => {
    if (!navigator.geolocation) { setNote(t('start.locationDenied')); return }
    setLocating(true); setNote(null)
    navigator.geolocation.getCurrentPosition(
      (pos) => {
        setLocating(false)
        // Rounded to ~1 km: enough for the forecast, less precise than the person's house.
        const round = (x: number) => Math.round(x * 100) / 100
        choose({ name: t('start.myLocation'), label: '', lat: round(pos.coords.latitude), lon: round(pos.coords.longitude) })
      },
      () => { setLocating(false); setNote(t('start.locationDenied')) },
      { timeout: 15000, maximumAge: 600000 },
    )
  }

  const searching = q.length >= 2 && results?.query !== q && !error
  const shown = q.length >= 2 && results?.query === q ? results.candidates : []

  return (
    <main className="app-main start">
      <div className="row"><Logo size={44} /><b style={{ fontSize: 28, fontWeight: 800 }}>{t('brand.name')}</b></div>

      <section className="stack" aria-labelledby="lang-heading">
        <h2 id="lang-heading" className="h-big">{t('start.chooseLanguage')}</h2>
        <div className="lang-grid">
          {LANGUAGES.map((l) => (
            <button key={l} type="button" lang={l} aria-pressed={language === l} onClick={() => setLanguage(l)}>
              {LANGUAGE_NAMES[l]}
            </button>
          ))}
        </div>
      </section>

      <section className="stack">
        <label htmlFor="place" className="h-big">{t('start.searchVillage')}</label>
        <div className="search">
          <Icon name="search" size={26} />
          <input id="place" type="search" value={query} onChange={(e) => setQuery(e.target.value)} maxLength={80}
            placeholder={t('start.searchPlaceholder')} autoComplete="off" enterKeyHint="search" />
        </div>

        <div aria-live="polite" className="stack">
          {searching && <div className="loading" role="status"><span className="spinner" />{t('start.searching')}</div>}
          {error && <ErrorBox error={error} />}
          {q.length >= 2 && results?.query === q && shown.length === 0 && <p className="big-note">{t('start.noMatches')}</p>}
          {shown.slice(0, 5).map((c) => {
            const [name, ...rest] = c.label.split(', ')
            return (
              <button key={`${c.lat},${c.lon}`} type="button" className="result"
                onClick={() => choose({ name, label: rest.join(', '), lat: c.lat, lon: c.lon })}>
                <Icon name="pin" size={26} />
                <span><b>{name}</b><span>{rest.join(', ')}</span></span>
              </button>
            )
          })}
        </div>

        <div className="or"><span />{t('start.or')}<span /></div>
        <button type="button" className="btn big" onClick={locate} disabled={locating}>
          <Icon name="pin" size={28} />{locating ? t('start.locating') : t('start.useLocation')}
        </button>
        {note && <p role="status" className="big-note">{note}</p>}
      </section>

      <p className="small" style={{ marginTop: 'auto', textAlign: 'center', fontSize: 16 }}>{t('start.privacy')}</p>
    </main>
  )
}
