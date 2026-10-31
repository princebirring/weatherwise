import { useCallback, useEffect, useMemo, useState } from 'react'
import { api } from './api'
import { AppHeader, TabBar } from './components/Shell'
import { useAsync } from './components/useAsync'
import { usePath } from './router'
import { Ask } from './screens/Ask'
import { FloodGuide } from './screens/FloodGuide'
import { Home } from './screens/Home'
import { Shelter } from './screens/Shelter'
import { Showcase } from './screens/Showcase'
import { Help } from './screens/Help'
import { NotCovered } from './screens/NotCovered'
import { Todo } from './screens/Todo'
import { Welcome } from './screens/Welcome'
import { saved } from './storage'
import { LanguageProvider, textFor } from './text'
import type { Language, SavedPlace } from './types'

function firstLanguage(): Language {
  const stored = saved.language()
  if (stored) return stored
  const browser = navigator.language.toLowerCase()
  return browser.startsWith('mr') ? 'mr' : browser.startsWith('hi') ? 'hi' : 'en'
}

export default function App() {
  const path = usePath()
  const [language, setLanguageState] = useState<Language>(firstLanguage)
  const [place, setPlaceState] = useState<SavedPlace | null>(saved.place)

  const setLanguage = useCallback((l: Language) => { saved.setLanguage(l); setLanguageState(l) }, [])
  const setPlace = useCallback((p: SavedPlace) => { saved.setPlace(p); setPlaceState(p) }, [])
  useEffect(() => { document.documentElement.lang = language }, [language])

  const policy = useAsync(() => api.policy(), 'policy')
  const status = useAsync(() => api.status(), 'status')
  // One fetch per place, shared by Home, warnings and the flood guide.
  const placeData = useAsync(place ? () => api.place(place.lat, place.lon) : null, place ? `${place.lat},${place.lon}` : '')

  const t = useMemo(() => textFor(language), [language])
  const context = { language, setLanguage, t, policy: policy.data }

  if (!path.startsWith('/app')) {
    return <LanguageProvider {...context}><Showcase /></LanguageProvider>
  }

  if (!place || path === '/app/place') {
    return (
      <LanguageProvider {...context}>
        <div className="app"><Welcome onPlace={setPlace} /></div>
      </LanguageProvider>
    )
  }

  if (placeData.error?.kind === 'not_covered') {
    return <LanguageProvider {...context}><div className="app"><NotCovered /></div></LanguageProvider>
  }

  const todo = path.match(/^\/app\/(?:todo|warning)\/(\d+)$/)
  const flood = !!placeData.data?.outlook.flood_guide.mode
  let screen
  let header = true
  if (todo) {
    screen = <Todo key={`${todo[1]}-${language}`} index={Number(todo[1])} data={placeData} />
    header = false
  } else if (path === '/app/shelter') {
    const kind = new URLSearchParams(window.location.search).get('kind') === 'flood' ? 'flood' : 'heat'
    screen = <Shelter key={kind} place={place} initialKind={kind} />
  } else if (path === '/app/help') {
    screen = <Help place={place} flood={flood} />
  } else if (path === '/app/flood') {
    screen = <FloodGuide place={place} data={placeData} />
  } else if (path === '/app/ask') {
    screen = <Ask place={place} status={status.data} />
    header = false
  } else {
    if (path !== '/app') window.history.replaceState(null, '', '/app') // unknown app path: show Today
    screen = <Home place={place} data={placeData} status={status.data} onPlace={setPlace} />
  }

  return (
    <LanguageProvider {...context}>
      <div className="app">
        {header && <AppHeader place={place} />}
        {screen}
        <TabBar />
      </div>
    </LanguageProvider>
  )
}
