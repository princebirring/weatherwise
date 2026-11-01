// The one way the website reaches data: the WeatherWise API (weatherwise/api/server.py).
import type {
  ChatReply, Language, OfficialAlerts, PlaceAndOutlook, PlaceCandidate, Policy, Replay, ReplayEvent, Rules, SavedPlace, Shelters, Status,
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
  chat: (sessionId: string, message: string, language: Language, place: SavedPlace | null) =>
    request<ChatReply>('/api/chat', {
      method: 'POST',
      body: JSON.stringify({ session_id: sessionId, message, language, place }),
    }),
}
