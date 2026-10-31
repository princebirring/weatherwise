// How warnings are shown: IMD colours, order, likelihood and day pictures. Display only.
import { describe, expect, it } from 'vitest'
import { chipsOf, dayIcon, dayLevel, levelOf, likelihood, sortDetections, titleOf, weekday, whenOf } from '../hazards'
import { textFor } from '../text'
import type { DayRow, Detection } from '../types'

const det = (hazard: string, severity: string, days_ahead = 1, agreement = 0.8, evidence = {}): Detection => ({
  hazard, severity, first_day: '2026-04-24', last_day: '2026-04-26', days_ahead, agreement, evidence,
})
const row = (day: string, tmax: number, hazards: string[] = [], rain = 0): DayRow => ({
  day, tmax_c: tmax, normal_tmax_c: 41, feels_like_max_c: tmax + 2, rain_mm: rain, river_m3s: null, hazards,
})

describe('warning display', () => {
  it("uses IMD's colours", () => {
    expect(levelOf(det('heat_wave', 'severe'))).toBe('red')
    expect(levelOf(det('heavy_rain', 'very_heavy'))).toBe('orange')
    expect(levelOf(det('dry_spell', 'dry_spell'))).toBe('yellow')
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
    expect(titleOf(det('humid_heat', 'danger'), textFor('hi'))).toBe('खतरनाक उमस भरी गर्मी')
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
  })

  it('colours and pictures each day by its most serious hazard', () => {
    expect(dayLevel(row('2026-04-24', 45, ['dry_spell:dry_spell', 'heat_wave:severe']))).toBe('red')
    expect(dayLevel(row('2026-04-24', 30))).toBeNull()
    expect(dayIcon(row('2026-04-24', 30, [], 12))).toBe('drop')
    expect(dayIcon(row('2026-04-24', 30))).toBe('sun')
  })
})
