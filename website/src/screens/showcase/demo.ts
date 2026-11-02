// Sample forecasts for the phone on the landing page. The phone runs the real app screens on
// these, so it always shows the app as it is today. Dates are counted from today; the places are
// examples only (any point in India works the same way).
import type { Detection, DayRow, OfficialAlerts, PlaceAndOutlook, SavedPlace } from '../../types'

export type Story = 'heat' | 'flood' | 'urgent'

const day = (ahead: number) => new Date(Date.now() + ahead * 86_400_000).toISOString().slice(0, 10)

const PLACES: Record<Story, SavedPlace & { district: string; state: string }> = {
  heat: { name: 'Akola', label: 'Akola, Maharashtra', lat: 20.7, lon: 77.0, district: 'Akola', state: 'Maharashtra' },
  flood: { name: 'Kolhapur', label: 'Kolhapur, Maharashtra', lat: 16.7, lon: 74.24, district: 'Kolhapur', state: 'Maharashtra' },
  urgent: { name: 'Kolhapur', label: 'Kolhapur, Maharashtra', lat: 16.7, lon: 74.24, district: 'Kolhapur', state: 'Maharashtra' },
}

// A hot spell building and easing, and a week of heavy rain on a large river.
const HEAT: [number, number, number][] = [[38, 37, 40], [41, 37, 44], [44, 38, 47], [45, 38, 48], [42, 38, 45], [39, 38, 41], [37, 38, 39]]
const RAIN = [22, 74, 128, 96, 40, 12, 4]

function rows(story: Story): DayRow[] {
  return Array.from({ length: 7 }, (_, i) => story === 'heat'
    ? { day: day(i), tmax_c: HEAT[i][0], normal_tmax_c: HEAT[i][1], feels_like_max_c: HEAT[i][2], rain_mm: 0, river_m3s: null, rainy_day: false, hazards: [] }
    : { day: day(i), tmax_c: 29, normal_tmax_c: 30, feels_like_max_c: 33, rain_mm: RAIN[i], river_m3s: null, rainy_day: true, hazards: [] })
}

const warn = (hazard: string, severity: string, from: number, to: number, agreement: number): Detection =>
  ({ hazard, severity, first_day: day(from), last_day: day(to), days_ahead: from, agreement, evidence: {} })

const DETECTIONS: Record<Story, Detection[]> = {
  heat: [warn('work_heat', 'danger', 2, 3, 0.85), warn('heat_wave', 'heat_wave', 3, 3, 0.7)],
  flood: [warn('heavy_rain', 'very_heavy', 2, 3, 0.8)],
  urgent: [warn('heavy_rain', 'extremely_heavy', 0, 1, 0.9)],
}

export const NO_OFFICIAL: OfficialAlerts = { status: 'ok', alerts: [], source: 'SACHET' }

export function demoPlace(story: Story): SavedPlace {
  const { name, label, lat, lon } = PLACES[story]
  return { name, label, lat, lon }
}

export function demoData(story: Story): PlaceAndOutlook {
  const p = PLACES[story]
  const flood = story !== 'heat'
  return {
    place: {
      lat: p.lat, lon: p.lon, name: p.name, admin: { country_code: 'in', state: p.state, district: p.district },
      timezone: 'Asia/Kolkata', cell: '', elevation_m: null, coast_km: null, terrain: 'plains',
      river: { flood_level_m3s: null, is_river_area: flood, upstream_source: null }, derived_from: {},
    },
    outlook: {
      place: { name: p.name, district: p.district, state: p.state, terrain: 'plains', large_river_nearby: flood },
      issue_date: day(0),
      detections: DETECTIONS[story],
      flood_guide: { mode: story === 'flood' ? 'prepare' : story === 'urgent' ? 'urgent' : null, reasons: [] },
      data_missing: [],
      days: rows(story),
      flood_level_m3s: null,
      official: NO_OFFICIAL,
      attribution: '',
    },
  }
}
