import { useCallback, useEffect, useMemo, useState } from 'react'
import { api } from './api'
import { AppHeader, TabBar } from './components/Shell'
import { useAsync } from './components/useAsync'
import { useInstallPrompt } from './components/useInstallPrompt'
import { useOnline } from './components/useOnline'
import { GROUPS, groupOf, sortDetections, type HazardGroup } from './hazards'
import { navigate, usePath } from './router'
import { Ask } from './screens/Ask'
import { HazardPage } from './screens/Hazard'
import { Home } from './screens/Home'
import { Showcase } from './screens/Showcase'
import { Help } from './screens/Help'
import { NotCovered } from './screens/NotCovered'
import { Welcome } from './screens/Welcome'
import { saved } from './storage'
import { LanguageProvider, textFor } from './text'
import type { Language, PlaceAndOutlook, SavedPlace } from './types'

function firstLanguage(): Language {
  const stored = saved.language()
  if (stored) return stored
  const browser = navigator.language.toLowerCase()
  return browser.startsWith('mr') ? 'mr' : browser.startsWith('hi') ? 'hi' : 'en'
}

/** A link can carry the place (?lat=..&lon=..&name=..), so a warning message opens straight to
 *  that place's warning. Rounded to ~1 km, as "use my location" is. */
function placeFromLink(): SavedPlace | null {
  const q = new URLSearchParams(window.location.search)
  const lat = Number(q.get('lat'))
  const lon = Number(q.get('lon'))
  if (!q.has('lat') || !q.has('lon') || !Number.isFinite(lat) || !Number.isFinite(lon) || Math.abs(lat) > 90 || Math.abs(lon) > 180) return null
  const round = (x: number) => Math.round(x * 100) / 100
  return { name: (q.get('name') ?? '').slice(0, 80), label: '', lat: round(lat), lon: round(lon) }
}

/** Where an old link (the earlier warning, safe-place and flood-guide screens) now lives. */
function newPathFor(path: string, data: PlaceAndOutlook | null): string | null {
  if (path === '/app/shelter') return new URLSearchParams(window.location.search).get('kind') === 'flood' ? '/app/flood' : '/app/heat'
  const old = path.match(/^\/app\/(?:todo|warning)\/(\d+)$/)
  if (old) {
    if (!data) return null // wait for the forecast to know which warning it was
    const d = sortDetections(data.outlook.detections)[Number(old[1])]
    return d ? `/app/${groupOf(d.hazard)}` : '/app'
  }
  return null
}

export default function App() {
  const path = usePath()
  const [language, setLanguageState] = useState<Language>(firstLanguage)
  const [place, setPlaceState] = useState<SavedPlace | null>(() => {
    const linked = placeFromLink()
    if (linked) saved.setPlace(linked)
    return linked ?? saved.place()
  })
  const online = useOnline()
  const install = useInstallPrompt()
  const [visits] = useState(() => { const n = saved.visits() + 1; saved.setVisits(n); return n })
  const [installDismissed, setInstallDismissed] = useState(saved.installDismissed)
  const dismissInstall = useCallback(() => { saved.setInstallDismissed(); setInstallDismissed(true) }, [])

  const setLanguage = useCallback((l: Language) => { saved.setLanguage(l); setLanguageState(l) }, [])
  const setPlace = useCallback((p: SavedPlace) => { saved.setPlace(p); setPlaceState(p) }, [])
  useEffect(() => { document.documentElement.lang = language }, [language])

  const policy = useAsync(() => api.policy(), 'policy')
  const status = useAsync(() => api.status(), 'status')
  // One fetch per place, shared by Today and the danger pages.
  const placeData = useAsync(place ? () => api.place(place.lat, place.lon) : null, place ? `${place.lat},${place.lon}` : '')
  // Asked separately so official warnings show even when our forecast is slow or down.
  const official = useAsync(place ? () => api.official(place.lat, place.lon) : null, place ? `${place.lat},${place.lon}` : '')

  // A place from a link or "use my location" is a bare point: name it once it is resolved.
  const facts = placeData.data?.place
  useEffect(() => {
    if (facts && place && !place.label) {
      setPlace({ ...place, name: facts.name || place.name, label: [facts.admin.district, facts.admin.state].filter(Boolean).join(', ') })
    }
  }, [facts, place, setPlace])

  // The place has been read from the link: drop it from the address bar.
  useEffect(() => {
    const q = new URLSearchParams(window.location.search)
    if (q.has('lat') || q.has('lon')) {
      for (const k of ['lat', 'lon', 'name']) q.delete(k)
      const rest = q.toString()
      navigate(window.location.pathname + (rest ? `?${rest}` : ''), { replace: true })
    }
  }, [])

  const oldLink = /^\/app\/(?:todo|warning)\/\d+$/.test(path) || path === '/app/shelter'
  const moved = oldLink ? newPathFor(path, placeData.data) : null
  useEffect(() => { if (moved) navigate(moved, { replace: true }) }, [moved])

  const t = useMemo(() => textFor(language), [language])
  const context = { language, setLanguage, t, policy: policy.data }

  if (!path.startsWith('/app')) {
    return <LanguageProvider {...context}><Showcase /></LanguageProvider>
  }

  if (!place || path === '/app/place') {
    return (
      <LanguageProvider {...context}>
        <div className="app"><Welcome onPlace={setPlace} current={place} /></div>
      </LanguageProvider>
    )
  }

  if (placeData.error?.kind === 'not_covered') {
    return <LanguageProvider {...context}><div className="app"><NotCovered /></div></LanguageProvider>
  }

  const group = GROUPS.find((g) => path === `/app/${g}`) as HazardGroup | undefined
  const flood = !!placeData.data?.outlook.flood_guide.mode
  let screen
  let header = true
  if (group) {
    screen = <HazardPage key={group} group={group} place={place} data={placeData} />
    header = false
  } else if (path === '/app/help') {
    screen = <Help place={place} flood={flood} />
  } else if (path === '/app/ask') {
    screen = <Ask place={place} status={status.data} />
    header = false
  } else {
    if (path !== '/app' && !oldLink) window.history.replaceState(null, '', '/app') // unknown app path: show Today
    screen = <Home place={place} data={placeData} official={official} offline={!online}
      install={visits >= 2 && !installDismissed ? install : null} onDismissInstall={dismissInstall} />
  }

  return (
    <LanguageProvider {...context}>
      <div className="app">
        {header && <AppHeader place={place} checked={placeData.data?.outlook.issue_date} />}
        {screen}
        <TabBar />
      </div>
    </LanguageProvider>
  )
}
