// What stays on this phone: the chosen language, the place, flood-guide progress and a chat id.
// Nothing here is sent anywhere except the place (to get its forecast). Storage can be blocked
// (private mode), so every read and write is guarded and the app works without it.
import type { Language, SavedPlace } from './types'

const PREFIX = 'weatherwise.'

function read<T>(key: string, fallback: T): T {
  try {
    const raw = localStorage.getItem(PREFIX + key)
    return raw === null ? fallback : (JSON.parse(raw) as T)
  } catch {
    return fallback
  }
}

function write(key: string, value: unknown): void {
  try {
    if (value === null) localStorage.removeItem(PREFIX + key)
    else localStorage.setItem(PREFIX + key, JSON.stringify(value))
  } catch {
    // storage blocked: keep working for this visit
  }
}

export const saved = {
  language: () => read<Language | null>('language', null),
  setLanguage: (l: Language) => write('language', l),
  place: () => read<SavedPlace | null>('place', null),
  setPlace: (p: SavedPlace | null) => write('place', p),
  // "Add to home screen" is offered from the second visit, until the person says "not now".
  visits: () => read<number>('visits', 0),
  setVisits: (n: number) => write('visits', n),
  installDismissed: () => read<boolean>('install_dismissed', false),
  setInstallDismissed: () => write('install_dismissed', true),
  floodHome: () => read<'village' | 'city'>('flood_home', 'village'),
  setFloodHome: (home: 'village' | 'city') => write('flood_home', home),
  // Flood steps ticked, by place and home type: the household can stop and come back.
  floodDone: (key: string) => read<number[]>(`flood_done.${key}`, []),
  setFloodDone: (key: string, done: number[]) => write(`flood_done.${key}`, done),
  chatSession: () => {
    let id = read<string | null>('chat_session', null)
    if (!id) {
      id = `${crypto.randomUUID()}-${Date.now().toString(36)}`
      write('chat_session', id)
    }
    return id
  },
}
