// How warnings are shown: IMD colours, order, likelihood and day pictures. Display only.
import { describe, expect, it } from 'vitest'
import { chipsOf, dayGlance, dayIcon, dayLevel, dryDays, groupStatus, longDay, yourDay, levelOf, likelihood, officialIcon, officialTitle, sortDetections, titleOf, weekday, whenOf } from '../hazards'
import { textFor } from '../text'
import type { DayRow, Detection } from '../types'

const det = (hazard: string, severity: string, days_ahead = 1, agreement = 0.8, evidence = {}): Detection => ({
  hazard, severity, first_day: '2026-04-24', last_day: '2026-04-26', days_ahead, agreement, evidence,
})
const row = (day: string, tmax: number, hazards: string[] = [], rain = 0): DayRow => ({
  day, tmax_c: tmax, normal_tmax_c: 41, feels_like_max_c: tmax + 2, rain_mm: rain, river_m3s: null, hazards,
})

describe('official alert icons: the kind of weather, not how serious', () => {
  it('picks the weather icon from the event name', () => {
    expect(officialIcon('Heavy Rain')).toBe('rain')
    expect(officialIcon('Thunderstorm & Lightning')).toBe('storm')
    expect(officialIcon('Flood')).toBe('waves')
    expect(officialIcon('Cyclone')).toBe('wind')
    expect(officialIcon('Heat Wave')).toBe('heat')
    expect(officialIcon('Something new')).toBe('alert')
  })
})

describe('dayGlance: the farm week as three answers', () => {
  const t = textFor('en')
  const wet = (day: string, mm: number) => ({ day, tmax_c: 30, normal_tmax_c: 30, feels_like_max_c: 33, rain_mm: mm, river_m3s: null, rainy_day: mm >= 2.5, hazards: [] })
  it('says wait when it rains every day, and how much', () => {
    const g = dayGlance(['2026-11-03', '2026-11-04', '2026-11-05'].map((d) => wet(d, 17)), 'en', t)
    expect(g[0]).toMatchObject({ key: 'spray', ok: false, value: 'Wait' })
    expect(g[1]).toMatchObject({ key: 'rain', value: 'On 3 days', sub: 'Up to 17 mm' })
    expect(g[2]).toMatchObject({ key: 'heat', value: '30°', sub: 'Feels 33°' })
  })
  it('says good all week when it stays dry', () => {
    const g = dayGlance(['2026-11-03', '2026-11-04'].map((d) => wet(d, 0)), 'en', t)
    expect(g[0]).toMatchObject({ ok: true, value: 'Good all week' })
    expect(g[1]).toMatchObject({ key: 'rain', value: 'None this week' })
  })
})

describe('warning display', () => {
  it("uses IMD's colours", () => {
    expect(levelOf(det('heat_wave', 'severe'))).toBe('red')
    expect(levelOf(det('heavy_rain', 'very_heavy'))).toBe('orange')
    expect(levelOf(det('dry_spell', 'dry_spell'))).toBe('yellow')
  })

  it('colours our own work-heat levels and unusual rain', () => {
    expect(levelOf(det('work_heat', 'take_care'))).toBe('yellow')
    expect(levelOf(det('work_heat', 'danger'))).toBe('orange')
    expect(levelOf(det('unusual_rain', 'unusual'))).toBe('yellow')
  })

  it('puts the most serious warning first, then the soonest', () => {
    const order = sortDetections([det('dry_spell', 'dry_spell', 0), det('heat_wave', 'heat_wave', 3), det('heat_wave', 'severe', 4)])
    expect(order.map((d) => d.severity)).toEqual(['severe', 'heat_wave', 'dry_spell'])
  })

  it('says how likely in plain words, from how many forecasts agree', () => {
    const t = textFor('en')
    expect([0.9, 0.7, 0.5].map((a) => likelihood(det('heat_wave', 'heat_wave', 1, a), t))).toEqual(['Very likely', 'Likely', 'Possible'])
  })

  it('titles a warning in every language', () => {
    expect(titleOf(det('heat_wave', 'severe'), textFor('en'))).toBe('Severe heat wave')
    expect(titleOf(det('heat_wave', 'severe'), textFor('mr'))).toBe('तीव्र उष्णतेची लाट')
    expect(titleOf(det('work_heat', 'danger'), textFor('hi'))).toBe('धूप में काम के लिए खतरनाक गर्मी')
    expect(titleOf(det('work_heat', 'take_care'), textFor('en'))).toBe('Hot for work in the sun')
    expect(titleOf(det('unusual_rain', 'unusual'), textFor('mr'))).toBe('तुमच्या भागासाठी असामान्य पाऊस')
  })

  it('names days in the chosen language', () => {
    expect(weekday('2026-04-23', 'en')).toBe('Thu')
    expect(weekday('2026-04-23', 'mr')).toMatch(/[ऀ-ॿ]/)
    expect(whenOf(det('heat_wave', 'heat_wave'), 'hi')).toMatch(/[ऀ-ॿ].* – .*[ऀ-ॿ]/)
  })

  it('takes chips only from forecast numbers, and labels our own rules', () => {
    const rows = [row('2026-04-24', 44.6), row('2026-04-25', 45.4), row('2026-04-26', 43)]
    expect(chipsOf(det('heat_wave', 'heat_wave'), rows, 'Akola', textFor('en'))).toEqual(['Up to 45°', 'Very likely'])
    expect(chipsOf(det('excess_heat', 'heatwave', 1, 0.6, { rule: 'ours (Excess Heat Factor)' }), rows, 'Akola', textFor('en')))
      .toEqual(['Up to 45°', 'Likely', 'Our early signal'])
    expect(chipsOf(det('heavy_rain', 'heavy', 1, 0.8, { place: 'Gaganbawda (Ghats)' }), rows, 'Kolhapur', textFor('en'))[0])
      .toBe('Upstream: Gaganbawda (Ghats)')
    const ours = { rule: 'ours (feels-like heat for outdoor work)' }
    expect(chipsOf(det('work_heat', 'danger', 1, 0.8, ours), rows, 'Akola', textFor('en'))).toEqual(['Feels like 47°', 'Very likely', 'Our early signal'])
    const wet = [row('2026-04-24', 30, [], 52), row('2026-04-25', 30, [], 20)]
    expect(chipsOf(det('unusual_rain', 'unusual', 1, 0.5, { rule: 'ours (rain rare for this place)' }), wet, 'Vijayawada', textFor('en')))
      .toEqual(['Up to 52 mm rain', 'Rare here', 'Possible', 'Our early signal'])
  })

  it('colours and pictures each day by its most serious hazard', () => {
    expect(dayLevel(row('2026-04-24', 45, ['dry_spell:dry_spell', 'heat_wave:severe']))).toBe('red')
    expect(dayLevel(row('2026-04-24', 30))).toBeNull()
    expect(dayIcon(row('2026-04-24', 30, [], 12))).toBe('rain')
    expect(dayIcon(row('2026-04-24', 30))).toBe('sun')
  })
})

describe('official warning titles', () => {
  it('keeps the issuer words in English and translates the event type otherwise', () => {
    const event = 'Thunderstorm, Lightning, and Gusty winds'
    expect(officialTitle(event, 'en', textFor('en'))).toBe(event)
    expect(officialTitle(event, 'mr', textFor('mr'))).toBe('गडगडाटी वादळ')
    expect(officialTitle('Deep Depression', 'hi', textFor('hi'))).toBe('चक्रवात')
    expect(officialTitle('Something new', 'mr', textFor('mr'))).toBe('अधिकृत इशारा')
  })
})

describe('three checks and spraying days', () => {
  const rainy = (r: DayRow, wet: boolean | null): DayRow => ({ ...r, rainy_day: wet })

  it('spraying days: dry and no warning; unknown rain says nothing', () => {
    const days = [rainy(row('2026-04-24', 38), false), rainy(row('2026-04-25', 38), true),
      rainy(row('2026-04-26', 44, ['work_heat:danger']), false)]
    expect(dryDays(days)?.map((d) => d.day)).toEqual(['2026-04-24'])
    expect(dryDays([rainy(row('2026-04-24', 38), null)])).toBeNull()
  })

  it('the flood row follows the flood guide: prepare is orange, urgent is red', () => {
    const outlook = (mode: 'prepare' | 'urgent' | null, detections: Detection[] = []) =>
      ({ detections, flood_guide: { mode, reasons: [] }, data_missing: [] }) as unknown as Parameters<typeof groupStatus>[1]
    expect(groupStatus('flood', outlook(null)).level).toBeNull()
    expect(groupStatus('flood', outlook('prepare', [det('unusual_rain', 'unusual')])).level).toBe('orange')
    expect(groupStatus('flood', outlook('urgent')).level).toBe('red')
    expect(groupStatus('heat', outlook('urgent')).level).toBeNull()
  })
})

describe('your day', () => {
  const t = textFor('en')
  const week = (rain: number[], hazards: Record<number, string[]> = {}): DayRow[] => rain.map((mm, i) => ({
    ...row(`2026-11-0${i + 3}`, 31, hazards[i] ?? [], mm), rainy_day: mm >= 2.5 }))

  it('a dry week: every day is good for spraying', () => {
    const rows = week([0, 1, 0, 0.6, 0, 1.5, 0])
    expect(yourDay(rows, 'en', t)[0].text).toBe(t('day.sprayAll', longDay(rows[6].day, 'en')))
    expect(yourDay(rows, 'en', t).map((l) => l.icon)).toEqual(['plant', 'sun']) // no rain line
  })

  it('dry now, rain for the rest of the week: spray and harvest before it', () => {
    const rows = week([1, 1.6, 3.5, 7.2, 6.5, 6.0, 2.6])
    const [spray, rain] = yourDay(rows, 'en', t)
    expect(spray.text).toBe(t('day.sprayBy', longDay(rows[1].day, 'en')))
    expect(rain.text).toBe(`${t('day.rain', `${longDay(rows[2].day, 'en')} – ${longDay(rows[6].day, 'en')}`)} ${t('day.rainUpTo', 7)}`)
  })

  it('a warning day is never good for field work; rain every day says wait', () => {
    const heatDay = week([0, 0, 0], { 1: ['work_heat:danger'] })
    expect(yourDay(heatDay, 'en', t)[0].text).not.toContain(longDay(heatDay[1].day, 'en').slice(0, 3))
    expect(yourDay(week([5, 6, 7]), 'en', t)[0].text).toBe(t('week.sprayNone'))
  })

  it('rain unknown: no spraying advice at all, never a guess', () => {
    const rows = week([0, 0]).map((r) => ({ ...r, rainy_day: null }))
    expect(yourDay(rows, 'en', t).map((l) => l.icon)).toEqual(['sun'])
  })
})
