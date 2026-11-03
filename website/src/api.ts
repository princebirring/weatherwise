// The one way the website reaches data: the WeatherWise API (weatherwise/api/server.py).
import type {
  ChatProgress, ChatReply, Daily, Language, OfficialAlerts, PlaceAndOutlook, PlaceCandidate, Policy, Replay, ReplayEvent, Rules, SavedPlace, Shelters, Status,
} from './types'

export class ApiError extends Error {
  kind: string
  status: number
  constructor(kind: string, message: string, status: number) {
    super(message)
    this.kind = kind
    this.status = status
  }
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  let response: Response
  try {
    response = await fetch(path, { ...init, headers: { 'content-type': 'application/json', ...init?.headers } })
  } catch {
    throw new ApiError('offline', 'No internet connection.', 0)
  }
  const body = await response.json().catch(() => ({}))
  if (!response.ok) throw new ApiError(body.error ?? 'failed', body.message ?? 'Something went wrong.', response.status)
  return body as T
}

const query = (params: Record<string, string | number>) =>
  new URLSearchParams(Object.entries(params).map(([k, v]) => [k, String(v)])).toString()

export const api = {
  status: () => request<Status>('/api/status'),
  policy: () => request<Policy>('/api/policy'),
  // Names come back in the person's language where known (Marathi, Hindi), else English.
  findPlace: (q: string, lang: Language) => request<{ candidates: PlaceCandidate[] }>(`/api/places?${query({ q, lang })}`),
  place: (lat: number, lon: number) => request<PlaceAndOutlook>(`/api/place?${query({ lat, lon })}`),
  official: (lat: number, lon: number) => request<OfficialAlerts>(`/api/official?${query({ lat, lon })}`),
  shelters: (lat: number, lon: number, hazard: 'heat' | 'flood') =>
    request<Shelters>(`/api/shelters?${query({ lat, lon, hazard })}`),
  rules: () => request<Rules>('/api/rules'),
  replays: () => request<ReplayEvent[]>('/api/replays'),
  replay: (id: string) => request<Replay>(`/api/replays/${encodeURIComponent(id)}`),
  daily: () => request<Daily>('/api/daily'),
  chat: (sessionId: string, message: string, language: Language, place: SavedPlace | null,
    onProgress?: (step: ChatProgress) => void) => chat(sessionId, message, language, place, onProgress),
}

const CHAT_FAILED = 'Something went wrong. For emergencies call 112. For disaster help call 1077.'

/** Chat arrives as one JSON line per event: each agent step as it starts and finishes, then the
 *  checked reply. A refusal (too long, too many, agents off) is a plain JSON error, as elsewhere. */
async function chat(sessionId: string, message: string, language: Language, place: SavedPlace | null,
  onProgress?: (step: ChatProgress) => void): Promise<ChatReply> {
  let response: Response
  try {
    response = await fetch('/api/chat', {
      method: 'POST',
      headers: { 'content-type': 'application/json', accept: 'application/x-ndjson' },
      body: JSON.stringify({ session_id: sessionId, message, language, place }),
    })
  } catch {
    throw new ApiError('offline', 'No internet connection.', 0)
  }
  if (!response.ok || !response.body || !response.headers.get('content-type')?.includes('ndjson')) {
    const body = await response.json().catch(() => ({}))
    if (!response.ok) throw new ApiError(body.error ?? 'failed', body.message ?? 'Something went wrong.', response.status)
    return body as ChatReply
  }
  const reader = response.body.pipeThrough(new TextDecoderStream()).getReader()
  let buffer = ''
  try {
    for (;;) {
      const { value, done } = await reader.read()
      if (done) break
      buffer += value
      const lines = buffer.split('\n')
      buffer = lines.pop() ?? ''
      for (const line of lines.filter((l) => l.trim())) {
        const event = JSON.parse(line)
        if (event.type === 'step') onProgress?.({ agent: event.agent, tool: event.tool, done: !!event.done })
        else if (event.type === 'reply') return event as ChatReply
        else if (event.type === 'error') throw new ApiError(event.error ?? 'failed', event.message ?? CHAT_FAILED, 502)
      }
    }
  } catch (e) {
    if (e instanceof ApiError) throw e
    throw new ApiError('offline', 'The connection dropped before the answer arrived.', 0)
  }
  throw new ApiError('failed', CHAT_FAILED, 502)
}
