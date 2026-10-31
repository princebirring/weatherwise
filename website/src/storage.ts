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
  floodStep: (key: string) => read<number>(`flood_step.${key}`, 0),
  setFloodStep: (key: string, step: number) => write(`flood_step.${key}`, step),
  chatSession: () => {
    let id = read<string | null>('chat_session', null)
    if (!id) {
      id = `${crypto.randomUUID()}-${Date.now().toString(36)}`
      write('chat_session', id)
    }
    return id
  },
}
