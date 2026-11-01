// How a hazard detection from hazard_outlook is shown: IMD colour level, title, short chips.
// Display only: whether a hazard exists is decided by the risk engine, never here.
import type { IconName } from './components/Icon'
import type { T } from './text'
import { en, type TextKey } from './text/en'
import type { DayRow, Detection, Language } from './types'

export type Level = 'red' | 'orange' | 'yellow'

// IMD's colour code: yellow = be aware, orange = be prepared, red = take action.
const LEVELS: Record<string, Level> = {
  'heat_wave:heat_wave': 'orange',
  'heat_wave:severe': 'red',
  'work_heat:take_care': 'yellow',
  'work_heat:danger': 'orange',
  'excess_heat:heatwave': 'orange',
  'excess_heat:severe': 'red',
  'heavy_rain:heavy': 'yellow',
  'heavy_rain:very_heavy': 'orange',
  'heavy_rain:extremely_heavy': 'red',
  'unusual_rain:unusual': 'yellow',
  'dry_spell:dry_spell': 'yellow',
  'sowing_risk:sow_or_wait': 'yellow',
  'river_flood:above_flood_level': 'orange',
}
const RANK: Record<Level, number> = { red: 3, orange: 2, yellow: 1 }

// Rules taken from the official service; everything else is labelled "ours".
const OFFICIAL_HAZARDS = new Set(['heat_wave', 'heavy_rain'])

export const HEAT_HAZARDS = new Set(['heat_wave', 'work_heat', 'excess_heat'])
export const FLOOD_HAZARDS = new Set(['heavy_rain', 'unusual_rain', 'river_flood'])

export const levelOf = (d: Detection): Level => LEVELS[`${d.hazard}:${d.severity}`] ?? 'yellow'
export const levelOfKey = (hazardKey: string): Level => LEVELS[hazardKey] ?? 'yellow'
export const isOurs = (d: Detection) => !OFFICIAL_HAZARDS.has(d.hazard) || String(d.evidence.rule ?? '').startsWith('ours')

/** Most serious first, then soonest. */
export function sortDetections(ds: Detection[]): Detection[] {
  return [...ds].sort((a, b) => RANK[levelOf(b)] - RANK[levelOf(a)] || a.days_ahead - b.days_ahead)
}

export function titleOf(d: Detection, t: T): string {
  const specific = `hazard.${d.hazard}:${d.severity}`
  return specific in en ? t(specific as TextKey) : t(`hazard.${d.hazard}` as TextKey)
}

/** "Very likely" etc. from the share of forecast runs that agree. */
export function likelihood(d: Detection, t: T): string {
  return t(d.agreement >= 0.8 ? 'likely.high' : d.agreement >= 0.6 ? 'likely.mid' : 'likely.low')
}

export function iconOf(hazard: string): IconName {
  if (hazard === 'heavy_rain' || hazard === 'unusual_rain') return 'drop'
  if (hazard === 'river_flood') return 'waves'
  if (hazard === 'dry_spell' || hazard === 'sowing_risk') return 'dry'
  return 'heat'
}

export const LOCALES: Record<Language, string> = { en: 'en-IN', hi: 'hi-IN', mr: 'mr-IN' }

export function weekday(isoDay: string, language: Language): string {
  return new Intl.DateTimeFormat(LOCALES[language], { weekday: 'short', timeZone: 'UTC' }).format(new Date(isoDay))
}

export function longDay(isoDay: string, language: Language): string {
  return new Intl.DateTimeFormat(LOCALES[language], { weekday: 'long', timeZone: 'UTC' }).format(new Date(isoDay))
}

export function shortDate(isoDay: string, language: Language): string {
  return new Intl.DateTimeFormat(LOCALES[language], { day: 'numeric', month: 'short', timeZone: 'UTC' }).format(new Date(isoDay))
}

/** "Thursday – Saturday" (or one day), in the chosen language. */
export function whenOf(d: Detection, language: Language): string {
  const first = longDay(d.first_day, language)
  return d.first_day === d.last_day ? first : `${first} – ${longDay(d.last_day, language)}`
}

const inSpan = (d: Detection, rows: DayRow[]) => rows.filter((r) => r.day >= d.first_day && r.day <= d.last_day)
const maxOf = (xs: (number | null)[]) => {
  const v = xs.filter((x): x is number => x !== null)
  return v.length ? Math.max(...v) : null
}

/** Upstream heavy rain is reported for the rain point, not the person's place. */
export function upstreamPlace(d: Detection, placeName: string): string | null {
  const p = d.evidence.place
  return d.hazard === 'heavy_rain' && typeof p === 'string' && p !== placeName ? p : null
}

/** Short facts for a warning, from the forecast rows only: "Up to 45°", "Very likely". */
export function chipsOf(d: Detection, rows: DayRow[], placeName: string, t: T): string[] {
  const span = inSpan(d, rows)
  const chips: string[] = []
  if (d.hazard === 'heat_wave' || d.hazard === 'excess_heat') {
    const top = maxOf(span.map((r) => r.tmax_c))
    if (top !== null) chips.push(t('chip.upTo', Math.round(top)))
  } else if (d.hazard === 'work_heat') {
    const feels = maxOf(span.map((r) => r.feels_like_max_c))
    if (feels !== null) chips.push(t('chip.feelsLike', Math.round(feels)))
  } else if (d.hazard === 'heavy_rain') {
    const upstream = upstreamPlace(d, placeName)
    const rain = maxOf(span.map((r) => r.rain_mm))
    if (upstream) chips.push(t('chip.upstream', upstream))
    else if (rain !== null) chips.push(t('chip.rain', Math.round(rain)))
  } else if (d.hazard === 'unusual_rain') {
    const rain = maxOf(span.map((r) => r.rain_mm))
    if (rain !== null) chips.push(t('chip.rain', Math.round(rain)))
    chips.push(t('chip.rareHere'))
  } else if (d.hazard === 'dry_spell') {
    chips.push(t('chip.dry'))
  } else if (d.hazard === 'sowing_risk') {
    chips.push(t('chip.sow'))
  } else if (d.hazard === 'river_flood') {
    chips.push(t('chip.river'))
  }
  chips.push(likelihood(d, t))
  if (isOurs(d)) chips.push(t('chip.ours'))
  return chips
}

/** Day colour for the 7-day strip: the most serious hazard covering that day. */
export function dayLevel(row: DayRow): Level | null {
  let best: Level | null = null
  for (const h of row.hazards) {
    const l = levelOfKey(h)
    if (!best || RANK[l] > RANK[best]) best = l
  }
  return best
}

/** Picture for a day: the hazard covering it, else rain if it rains, else sun. */
export function dayIcon(row: DayRow): IconName {
  if (row.hazards.length) return iconOf(row.hazards[0].split(':')[0])
  return row.rain_mm !== null && row.rain_mm >= 2.5 ? 'drop' : 'sun'
}

// SACHET's event types, matched by keyword, most specific first, to our own translated names.
const OFFICIAL_EVENTS: [RegExp, TextKey][] = [
  [/cyclone|depression/i, 'event.cyclone'], [/storm surge/i, 'event.storm_surge'], [/tsunami/i, 'event.tsunami'],
  [/earthquake/i, 'event.earthquake'], [/flood|inundation/i, 'event.flood'], [/landslide/i, 'event.landslide'],
  [/rain|cloudburst/i, 'event.rain'], [/thunder/i, 'event.thunderstorm'], [/lightning/i, 'event.lightning'],
  [/hail/i, 'event.hail'], [/dust/i, 'event.dust'], [/wind|squall/i, 'event.wind'], [/heat/i, 'event.heat'],
  [/cold/i, 'event.cold'], [/fog/i, 'event.fog'],
]

/** An official alert's title in the chosen language: the issuer's own words in English,
 *  otherwise our translation of the event type (or "Official warning" if unknown). */
export function officialTitle(event: string, language: Language, t: T): string {
  if (language === 'en') return event
  const match = OFFICIAL_EVENTS.find(([pattern]) => pattern.test(event))
  return t(match ? match[1] : 'official.title')
}
