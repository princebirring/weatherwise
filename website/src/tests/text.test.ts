// Full language switch: every word exists in every language, and is really translated.
import { describe, expect, it } from 'vitest'
import { en, type TextKey } from '../text/en'
import { hi } from '../text/hi'
import { mr } from '../text/mr'
import { textFor } from '../text'

const LANGS = { hi, mr }
const KEYS = Object.keys(en) as TextKey[]
const DEVANAGARI = /[ऀ-ॿ]/

// Strings that are names or data and stay the same in every language.
const SAME_IN_ALL = new Set<TextKey>(['brand.name', 'show.layer5b'])

describe.each(Object.entries(LANGS))('%s text', (_, table) => {
  it('has exactly the English keys', () => {
    expect(Object.keys(table).sort()).toEqual([...KEYS].sort())
  })

  it('is written in Devanagari, not left in English', () => {
    const untranslated = KEYS.filter((k) => !SAME_IN_ALL.has(k) && !DEVANAGARI.test(table[k]))
    expect(untranslated).toEqual([])
  })

  it('keeps every {name} placeholder', () => {
    const broken = KEYS.filter((k) => en[k].includes('{name}') !== table[k].includes('{name}'))
    expect(broken).toEqual([])
  })

  it('keeps every helpline number the English text gives', () => {
    const missing = KEYS.filter((k) => ['112', '108', '1077'].some((n) => en[k].includes(n) && !table[k].includes(n)))
    expect(missing).toEqual([])
  })
})

describe('textFor', () => {
  it('fills every {name} and switches the whole table', () => {
    expect(textFor('en')('shelter.km', 3.2)).toBe('3.2 km')
    expect(textFor('mr')('shelter.km', 3.2)).toBe('3.2 किमी')
    expect(textFor('hi')('tabs.help')).toBe('मदद')
  })
})
