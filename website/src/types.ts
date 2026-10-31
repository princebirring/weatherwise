// Shapes returned by the WeatherWise API (weatherwise/api). They mirror the Climate Risk MCP tools.

export type Language = 'en' | 'hi' | 'mr'

export interface SavedPlace {
  name: string
  label: string
  lat: number
  lon: number
}

export interface PlaceCandidate {
  label: string
  lat: number
  lon: number
  source: string
}

export interface PlaceFacts {
  lat: number
  lon: number
  name: string
  admin: { country_code: string; state: string; district: string }
  timezone: string
  cell: string
  elevation_m: number | null
  coast_km: number | null
  terrain: 'plains' | 'coast' | 'hills'
  river: { flood_level_m3s: number | null; is_river_area: boolean; upstream_source: string | null }
  derived_from: Record<string, string>
}

export interface Detection {
  hazard: string
  severity: string
  first_day: string
  last_day: string
  days_ahead: number
  agreement: number
  evidence: Record<string, unknown>
}

export interface DayRow {
  day: string
  tmax_c: number | null
  normal_tmax_c: number | null
  feels_like_max_c: number | null
  rain_mm: number | null
  river_m3s: number | null
  hazards: string[]
}

export interface Outlook {
  place: { name: string; district: string; state: string; terrain: string; large_river_nearby: boolean }
  issue_date: string
  detections: Detection[]
  flood_guide: { mode: 'prepare' | 'urgent' | null; reasons: string[] }
  data_missing: string[]
  days: DayRow[]
  flood_level_m3s: number | null
  attribution: string
}

export interface PlaceAndOutlook {
  place: PlaceFacts
  outlook: Outlook
}

export interface ShelterPlace {
  name: string
  km: number
  contact: string | null
  source: string
  checked_on: string
  verified: boolean
  directions_link: string | null // always null in floods: no map routes
}

export interface Shelters {
  hazard: string
  place_type: string
  places: ShelterPlace[]
  helpline: Record<string, string>
  notes: string[]
  health_facilities?: { name: string; kind: string; km: number; source: string }[]
  confirm_line: string
  search_km: number
  stale_nearby: number
  health_status: 'ok' | 'unavailable' | 'not_needed'
}

export interface AdviceItem {
  who: string
  what: string
}

export interface Guidance {
  heat: AdviceItem[]
  heatstroke: string
  dry_spell: AdviceItem[]
  sowing: AdviceItem[]
  heavy_rain: AdviceItem[]
  flood_village: string[]
  flood_city: string[]
  flood_always: string
  flood_urgent: string
  flood_safety_line: string
}

export interface Policy {
  helplines: Record<string, string>
  default_languages: string[]
  footer: Record<string, string>
  guidance: Record<string, Guidance>
}

export interface ReplayEvent {
  id: string
  title: string
  titles: Record<Language, string>
  name: string
  lat: number
  lon: number
  first_day: string
  last_day: string
}

export interface HazardScore {
  hazard: string
  hits: number
  misses: number
  false_alarms: number
  correct_negatives: number
  event_lead_days: [string, number | null][]
  pod: number | null
  far: number | null
}

export interface ReplayDay {
  day: string
  would_have_sent: string[]
  flood_guide: string | null
  what_happened: string[]
  observed: Record<string, number | null>
}

export interface Replay {
  event: ReplayEvent
  mode: 'as_issued' | 'conditions_only'
  flood_level_m3s: number | null
  verification: {
    mode: string
    scores?: Record<string, HazardScore>
    conditions_met?: Record<string, string[]>
    note?: string
    notes?: string[]
  }
  timeline: ReplayDay[]
  notes: string[]
}

export interface AgentStep {
  agent: string
  tool: string
  status: string
  seconds: number
}

export interface ChatReply {
  text: string
  used_fallback: boolean
  violations: string[]
  steps: AgentStep[]
  seconds: number
}

export interface Status {
  agents_ready: boolean
  languages: Language[]
  limits: { max_message_chars: number }
}
