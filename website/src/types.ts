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
  rainy_day?: boolean | null // the country's "rainy day" line (IMD: 2.5 mm); null when rain is unknown
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
  official: OfficialAlerts
  attribution: string
}

/** Official warnings in force (IMD, state disaster authorities) from SACHET; they come first. */
export interface OfficialAlert {
  id: string
  event: string
  level: 'red' | 'orange' | 'yellow' | 'green'
  level_word: string
  source: string
  area: string
  starts: string
  ends: string
  language: string
  message: string
  translations: Record<string, string> // language -> message (translated by SACHET)
  flood_related: boolean
}

export interface OfficialAlerts {
  status: 'ok' | 'unavailable' | 'not_connected'
  alerts: OfficialAlert[]
  source: string | null
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
  work_heat: Record<string, string> // first card for each work-heat level, by level name
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
  unusual_rain_mm?: number | null
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

/** A tool starting or finishing while the agents work on a chat reply. */
export interface ChatProgress {
  agent: string
  tool: string
  done: boolean
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

/** The lines our checks use, served from rules/ (GET /api/rules). Official (IMD) and ours apart. */
export interface Rules {
  country: string
  heat: {
    base_tmax_c: Record<string, number> // by terrain: plains, coast, hills
    departure_c: number
    absolute_c: number
    min_days: number
    agreement: number
    work_heat_c: Record<string, number> // ours, by level name
    excess_heat_percentile: number
  }
  rain_mm: { heavy: number; very_heavy: number; extremely_heavy: number }
  unusual_rain: { percentile: number; min_mm: number }
  river_return_period_years: number
  flood_guide: {
    prepare_signals: string[]
    prepare_within_days: number
    urgent_within_days: number
    urgent_rain_category: string
    heavy_rain_days_in_a_row: number
    stay_on_quiet_days: number
  }
  correction: { training_days: number; max_shift_c: number }
  rules_version: string
}

// The morning run (weatherwise/daily_run.py, GET /api/daily): the agent's own work, already done.
export interface DailyPlace {
  place: { name: string; lat: number; lon: number; language: Language; why?: string }
  ok: boolean
  error?: string
  hazard_kind?: 'heat_dry' | 'flood' | 'all_clear' | null
  body?: string | null
  used_fallback?: boolean
  model_error?: string | null
  flood_guide?: { mode: string | null; reasons: string[] } | null
  evaluator_sent_back?: string[][]
  earlier_warnings?: { day: string; kind: string; message: string }[]
  model_calls?: number
  wall_seconds: number
}

export interface DailySummary {
  places: number
  finished: number
  failed: number
  warnings_written: number
  updates_of_earlier_warnings?: number
  all_clears?: number
  drafts_sent_back_by_evaluator: number
  safe_fallbacks_used: number
  model_calls: number
  model_cost_usd: number | null
  total_seconds: number
}

export interface DailyRun {
  run_date: string
  started_at: string
  model_id: string
  summary: DailySummary
  places: DailyPlace[]
}

export interface Daily {
  status: 'ok' | 'not_run_yet' | 'not_connected'
  latest?: DailyRun | null
  history?: ({ run_date: string } & DailySummary)[]
}
