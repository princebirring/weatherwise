// How a hazard detection from hazard_outlook is shown: IMD colour level, title, short chips.
// Display only: whether a hazard exists is decided by the risk engine, never here.
import type { IconName } from './components/Icon'
import type { T } from './text'
import { en, type TextKey } from './text/en'
import type { DayRow, Detection, Language, Outlook } from './types'

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
export const DRY_HAZARDS = new Set(['dry_spell', 'sowing_risk'])

/** The three things WeatherWise checks, as a farmer sees them: heat, rain and flood, dry spells. */
export type HazardGroup = 'heat' | 'flood' | 'dry'
export const GROUPS: HazardGroup[] = ['heat', 'flood', 'dry']
export const GROUP_ICONS: Record<HazardGroup, IconName> = { heat: 'heat', flood: 'waves', dry: 'dry' }

export function groupOf(hazard: string): HazardGroup {
  if (HEAT_HAZARDS.has(hazard)) return 'heat'
  if (DRY_HAZARDS.has(hazard)) return 'dry'
  return 'flood'
}

export interface GroupStatus {
  level: Level | null
  detections: Detection[] // most serious first
  missing: boolean // a check in this group could not run
}

/** One group's state for the week. The flood guide's mode counts too: prepare is IMD's orange
 *  ("be prepared"), urgent is red, even when the trigger was an official alert, not our check. */
export function groupStatus(group: HazardGroup, outlook: Outlook): GroupStatus {
  const detections = sortDetections(outlook.detections).filter((d) => groupOf(d.hazard) === group)
  let level: Level | null = detections.length ? levelOf(detections[0]) : null
  if (group === 'flood') {
    const mode = outlook.flood_guide.mode
    if (mode === 'urgent') level = 'red'
    else if (mode === 'prepare' && (!level || RANK[level] < RANK.orange)) level = 'orange'
  }
  return { level, detections, missing: outlook.data_missing.some((h) => groupOf(h) === group) }
}

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

// Latin digits everywhere: Marathi dates would otherwise use Devanagari digits next to 33° and 7.
export const LOCALES: Record<Language, string> = { en: 'en-IN', hi: 'hi-IN', mr: 'mr-IN-u-nu-latn' }

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

/** Good days to spray: no rain expected (below the country's "rainy day" line) and no warning
 *  that day, so a "too hot to work" day is never called good for field work. */
export function dryDays(rows: DayRow[]): DayRow[] | null {
  if (rows.some((r) => r.rainy_day === null || r.rainy_day === undefined)) return null
  return rows.filter((r) => !r.rainy_day && r.hazards.length === 0)
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

export interface DayLine {
  icon: IconName
  text: string
}

const listDays = (rows: DayRow[], language: Language) => rows.map((r) => weekday(r.day, language)).join(', ')

/** "Your day": plain sentences for the farm week, from the forecast rows only (no new thresholds:
 *  a day is rainy by the country's own line, a warning day is never called good for field work). */
export function yourDay(rows: DayRow[], language: Language, t: T): DayLine[] {
  const lines: DayLine[] = []
  const rainKnown = rows.length > 0 && rows.every((r) => r.rainy_day === true || r.rainy_day === false)

  if (rainKnown) {
    const good = rows.map((r) => !r.rainy_day && r.hazards.length === 0)
    const firstBad = good.indexOf(false)
    const goodRows = rows.filter((_, i) => good[i])
    let spray: string
    if (firstBad === -1) spray = t('day.sprayAll', longDay(rows[rows.length - 1].day, language))
    // Dry now, then rain for the rest of the week: get the work done before it.
    else if (firstBad > 0 && rows[firstBad].rainy_day && good.slice(firstBad).every((g) => !g)) spray = t('day.sprayBy', longDay(rows[firstBad - 1].day, language))
    else if (goodRows.length) spray = t('week.sprayDays', listDays(goodRows, language))
    else spray = t('week.sprayNone')
    lines.push({ icon: 'plant', text: spray })

    const rainy = rows.map((r, i) => (r.rainy_day ? i : -1)).filter((i) => i >= 0)
    if (rainy.length) {
      const together = rainy[rainy.length - 1] - rainy[0] === rainy.length - 1
      const when = rainy.length === 1 ? longDay(rows[rainy[0]].day, language)
        : together ? `${longDay(rows[rainy[0]].day, language)} – ${longDay(rows[rainy[rainy.length - 1]].day, language)}`
          : listDays(rainy.map((i) => rows[i]), language)
      const most = Math.max(...rainy.map((i) => rows[i].rain_mm ?? 0))
      lines.push({ icon: 'drop', text: `${t('day.rain', when)} ${t('day.rainUpTo', Math.round(most))}` })
    }
  }

  const top = (xs: (number | null)[]) => {
    const v = xs.filter((x): x is number => x !== null)
    return v.length ? Math.round(Math.max(...v)) : null
  }
  const hot = top(rows.map((r) => r.tmax_c))
  const feels = top(rows.map((r) => r.feels_like_max_c))
  if (hot !== null) lines.push({ icon: 'sun', text: `${t('day.hot', hot)}${feels !== null && feels > hot ? ` ${t('day.feels', feels)}` : ''}` })
  return lines
}
