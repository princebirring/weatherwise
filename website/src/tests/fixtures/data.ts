// Test data shaped like the WeatherWise API's answers. policy.json is the real message_policy
// (regenerate: uv run python -c "from weatherwise.rules import message_policy; ...").
import type { OfficialAlert, OfficialAlerts, PlaceAndOutlook, Policy, Replay, ReplayEvent, SavedPlace, Shelters, Status } from '../../types'
import policyJson from './policy.json'

export const policy = policyJson as unknown as Policy

export const place: SavedPlace = { name: 'Akola', label: 'Akola, Maharashtra', lat: 20.7, lon: 77.0 }

const days = ['2026-04-22', '2026-04-23', '2026-04-24', '2026-04-25', '2026-04-26', '2026-04-27', '2026-04-28']
const tmax = [41, 43, 45.4, 45.1, 44, 42, 40]

// A real Telangana SDMA watch from SACHET (Oct 31, 2026), with SACHET's own translations.
export const telanganaWatch: OfficialAlert = {
  id: '1793433201489030', event: 'Thunderstorm, Lightning, and Gusty winds', level: 'yellow', level_word: 'WATCH',
  source: 'Telangana SDMA', area: '15 districts of Telangana', starts: '2026-10-31T13:16:00+05:30',
  ends: '2026-11-01T08:31:00+05:30', language: 'en', flood_related: false,
  message: 'Thunderstorm accompanied with Lightning and Gusty Winds of 30-40 kmph very likely to occur at isolated places.',
  translations: {
    en: 'Thunderstorm accompanied with Lightning and Gusty Winds of 30-40 kmph very likely to occur at isolated places.',
    mr: 'काही ठिकाणी विजांच्या कडकडाटासह 30-40 किमी प्रतितास वेगाने वादळ आणि सोसाट्याचा वारा येण्याची दाट शक्यता आहे.',
    hi: 'कुछ स्थानों पर बिजली और 30-40 किमी प्रति घंटे की तेज़ हवाओं के साथ आंधी आने की बहुत संभावना है.',
  },
}

export function outlook(withDanger: boolean, floodMode: 'prepare' | 'urgent' | null = null,
  official: OfficialAlerts = { status: 'ok', alerts: [], source: 'SACHET' }): PlaceAndOutlook {
  return {
    place: {
      lat: 20.7, lon: 77.0, name: 'Akola', admin: { country_code: 'in', state: 'Maharashtra', district: 'Akola' },
      timezone: 'Asia/Kolkata', cell: '0.25:20.75:77.0', elevation_m: 285, coast_km: 400, terrain: 'plains',
      river: { flood_level_m3s: null, is_river_area: false, upstream_source: null }, derived_from: {},
    },
    outlook: {
      place: { name: 'Akola', district: 'Akola', state: 'Maharashtra', terrain: 'plains', large_river_nearby: false },
      issue_date: days[0],
      detections: withDanger ? [
        { hazard: 'heat_wave', severity: 'heat_wave', first_day: days[2], last_day: days[4], days_ahead: 2, agreement: 0.8, evidence: {} },
        { hazard: 'dry_spell', severity: 'dry_spell', first_day: days[0], last_day: days[6], days_ahead: 0, agreement: 0.7, evidence: {} },
      ] : [],
      flood_guide: { mode: floodMode, reasons: [] },
      data_missing: [],
      days: days.map((day, i) => ({
        day, tmax_c: tmax[i], normal_tmax_c: 41, feels_like_max_c: tmax[i] + 2, rain_mm: 0, river_m3s: null,
        hazards: withDanger && i >= 2 && i <= 4 ? ['heat_wave:heat_wave'] : [],
      })),
      flood_level_m3s: null,
      official,
      attribution: 'Weather data by Open-Meteo.com',
    },
  }
}

export const status: Status = { agents_ready: false, languages: ['en', 'hi', 'mr'], limits: { max_message_chars: 500 } }

export const shelters: Shelters = {
  hazard: 'heat', place_type: 'cooling_center', places: [], notes: ['No verified cooling center within 20 km. Call 1077.'],
  helpline: { disaster: '1077', ambulance: '108', emergency: '112' },
  health_facilities: [{ name: 'District Hospital', kind: 'hospital', km: 1.2, source: 'OpenStreetMap (unverified)' }],
  confirm_line: 'Call 1077 to confirm the place is open.', search_km: 20, stale_nearby: 0, health_status: 'ok',
}

export const events: ReplayEvent[] = [{
  id: 'kolhapur_flood_2024_07', title: 'Kolhapur-Sangli floods, July 2024', name: 'Kolhapur', lat: 16.7, lon: 74.24,
  first_day: '2024-07-24', last_day: '2024-07-27',
  titles: { en: 'Kolhapur-Sangli floods, July 2024', mr: 'कोल्हापूर-सांगली पूर, जुलै 2024', hi: 'कोल्हापुर-सांगली बाढ़, जुलाई 2024' },
}]

export const replay: Replay = {
  event: events[0], mode: 'as_issued', flood_level_m3s: 1321, notes: ['Official alerts are not archived.'],
  verification: {
    mode: 'as_issued', notes: ['Official alerts are not archived.'],
    scores: { river_flood: { hazard: 'river_flood', hits: 1, misses: 0, false_alarms: 0, correct_negatives: 0,
      event_lead_days: [['2024-07-26', 5]], pod: 1, far: 0 } },
  },
  timeline: ['2024-07-24', '2024-07-25', '2024-07-26', '2024-07-27'].map((day, i) => ({
    day, would_have_sent: i === 0 ? ['river_flood:above_flood_level'] : [], flood_guide: i === 0 ? 'prepare' : null,
    what_happened: i === 2 ? ['river_above_flood_level'] : [],
    observed: { tmax: 25, normal_tmax: 26, river_m3s: [1036, 1243, 1376, 1215][i], rain_mm: 10 },
  })),
}
