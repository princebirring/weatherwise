// Every screen, in every language: it renders, shows that language's words and safety text,
// and (for Hindi and Marathi) shows no English sentence from the site or the safety advice.
import { cleanup, render, screen, waitFor } from '@testing-library/react'
import type { ReactNode } from 'react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import App from '../App'
import { LanguageProvider, textFor } from '../text'
import { en, type TextKey } from '../text/en'
import { FloodGuide } from '../screens/FloodGuide'
import { Help } from '../screens/Help'
import { Home } from '../screens/Home'
import { NotCovered } from '../screens/NotCovered'
import { Shelter } from '../screens/Shelter'
import { Showcase } from '../screens/Showcase'
import { Todo } from '../screens/Todo'
import { Welcome } from '../screens/Welcome'
import { Ask } from '../screens/Ask'
import type { Language, PlaceAndOutlook } from '../types'
import { events, outlook, place, policy, replay, shelters, status } from './fixtures/data'

const LANGUAGES: Language[] = ['en', 'hi', 'mr']
// Names kept on purpose: the brand, data sources, and the technical agent name next to its translation.
const SAME_IN_ALL = new Set<TextKey>(['brand.name', 'show.layer5b', 'show.layer3n'])

// Every English sentence the site or the safety advice could show (short words like "Heat" skipped).
const ENGLISH_SENTENCES = [
  ...Object.entries(en).filter(([k]) => !SAME_IN_ALL.has(k as TextKey)).map(([, v]) => v),
  ...Object.values(policy.guidance.en).flatMap((v) =>
    typeof v === 'string' ? [v] : v.flatMap((x: string | { who: string; what: string }) => (typeof x === 'string' ? [x] : [x.who, x.what]))),
].map((s) => s.split('{name}')[0].trim()).filter((s) => s.length >= 12)

const loaded = (data: PlaceAndOutlook) => ({ data, error: null, loading: false, retry: () => {} })

function show(language: Language, ui: ReactNode) {
  return render(
    <LanguageProvider language={language} setLanguage={() => {}} t={textFor(language)} policy={policy}>{ui}</LanguageProvider>,
  )
}

function expectOnlyLanguage(language: Language) {
  const text = document.body.textContent ?? ''
  if (language === 'en') return
  expect(text).toMatch(/[ऀ-ॿ]/)
  const leftovers = ENGLISH_SENTENCES.filter((s) => text.includes(s))
  expect(leftovers).toEqual([])
}

function stubApi(overrides: Record<string, [number, unknown]> = {}) {
  const routes: Record<string, [number, unknown]> = {
    '/api/shelters': [200, shelters], '/api/replays/': [200, replay], '/api/replays': [200, events],
    '/api/policy': [200, policy], '/api/status': [200, status], ...overrides,
  }
  vi.stubGlobal('fetch', vi.fn(async (url: string) => {
    const path = Object.keys(routes).find((p) => url.startsWith(p)) ?? ''
    const [code, body] = routes[path] ?? [404, { error: 'not_found' }]
    return new Response(JSON.stringify(body), { status: code })
  }))
}

beforeEach(() => stubApi())
afterEach(() => { cleanup(); vi.unstubAllGlobals(); localStorage.clear(); window.history.pushState(null, '', '/') })

describe.each(LANGUAGES)('in %s', (language) => {
  const t = textFor(language)
  const g = policy.guidance[language]

  it('Start: language, search and location', () => {
    show(language, <Welcome onPlace={() => {}} />)
    expect(screen.getByText(t('start.searchVillage'))).toBeTruthy()
    expect(screen.getByRole('button', { name: new RegExp(t('start.useLocation')) })).toBeTruthy()
    expectOnlyLanguage(language)
  })

  it('Today on a danger day: the warning, what to do, send to family', () => {
    show(language, <Home place={place} data={loaded(outlook(true))} status={status} onPlace={() => {}} />)
    expect(screen.getByRole('heading', { level: 1 }).textContent).toBe(t('hazard.heat_wave'))
    expect(screen.getByText(t('today.whatToDo'))).toBeTruthy()
    expect(screen.getByText(t('today.share'))).toBeTruthy()
    expect(screen.getByText(t('chip.upTo', 45))).toBeTruthy()
    expect(screen.getByText(t('likely.high'))).toBeTruthy()
    expect(screen.getByText(t('hazard.dry_spell'))).toBeTruthy() // "also coming"
    expectOnlyLanguage(language)
  })

  it('Today on a safe day', () => {
    show(language, <Home place={place} data={loaded(outlook(false))} status={status} onPlace={() => {}} />)
    expect(screen.getByText(t('today.safeTitle'))).toBeTruthy()
    expect(screen.queryByText(t('today.whatToDo'))).toBeNull()
    // Never an all-clear: our checks do not see cyclones or official alerts, so IMD is one tap away.
    expect(document.body.textContent).not.toMatch(/safe to work|काम करणे सुरक्षित|काम करना सुरक्षित/i)
    expect(screen.getByText(t('today.officialWarnings')).closest('a')?.getAttribute('href')).toBe('https://sachet.ndma.gov.in/')
    expectOnlyLanguage(language)
  })

  it('What to do: one card at a time, with the safety text in this language', () => {
    show(language, <Todo index={0} data={loaded(outlook(true))} />)
    expect(screen.getByText(g.heat[0].what)).toBeTruthy()
    expect(screen.getByText(g.heat[0].who)).toBeTruthy()
    screen.getByText(t('todo.next')).click()
    expectOnlyLanguage(language)
  })

  it('Safe place: no cooling place near, honest note and hospitals', async () => {
    show(language, <Shelter place={place} initialKind="heat" />)
    await screen.findByText(t('shelter.noneNearHeat', 20))
    expect(screen.getByText(t('shelter.healthTitle'))).toBeTruthy()
    expectOnlyLanguage(language)
  })

  it('Safe place in a flood: the safety line, and never a route', async () => {
    show(language, <Shelter place={place} initialKind="flood" />)
    await screen.findByText(t('shelter.noRoute'))
    expect(screen.getByText(g.flood_safety_line)).toBeTruthy()
    expect(screen.queryByText(t('shelter.showWay'))).toBeNull()
    expectOnlyLanguage(language)
  })

  it('Help: one tap to every helpline', async () => {
    show(language, <Help place={place} flood={false} />)
    for (const n of ['112', '108', '1077']) expect(document.querySelector(`a[href="tel:${n}"]`)).toBeTruthy()
    expect(screen.getByText(t('help.sendLocation'))).toBeTruthy()
    await waitFor(() => expect(fetch).toHaveBeenCalled())
    expectOnlyLanguage(language)
  })

  it('Flood guide: first step for a village, in this language', () => {
    show(language, <FloodGuide place={place} data={loaded(outlook(false))} />)
    expect(screen.getByText(g.flood_village[0])).toBeTruthy()
    expect(screen.getByText(t('flood.calmTitle'))).toBeTruthy()
    expectOnlyLanguage(language)
  })

  it('Flood guide in urgent mode: one short message and the calls', () => {
    show(language, <FloodGuide place={place} data={loaded(outlook(false, 'urgent'))} />)
    expect(screen.getByText(g.flood_urgent)).toBeTruthy()
    expect(document.querySelector('a[href="tel:112"]')).toBeTruthy()
    expectOnlyLanguage(language)
  })

  it('Ask while chat is not connected: says so plainly', () => {
    show(language, <Ask place={place} status={status} />)
    expect(screen.getByText(t('ask.offlineTitle'))).toBeTruthy()
    expectOnlyLanguage(language)
  })

  it('Not covered (a village in Kenya): honest, and no Indian helplines', () => {
    show(language, <NotCovered />)
    expect(screen.getByText(t('notCovered.title'))).toBeTruthy()
    expect(document.body.textContent).not.toMatch(/1077|108\b/)
    expectOnlyLanguage(language)
  })

  it('Showcase: replay titles and scores in this language', async () => {
    show(language, <Showcase />)
    await screen.findAllByText(events[0].titles[language])
    expect(screen.getAllByText(t('show.replayTitle')).length).toBeGreaterThan(0)
    await screen.findAllByText(new RegExp(t('show.far')))
    expectOnlyLanguage(language)
  })
})

describe('the whole app', () => {
  it('a saved Kenyan place shows "not covered" in the saved language, without Indian helplines', async () => {
    localStorage.setItem('weatherwise.language', JSON.stringify('mr'))
    localStorage.setItem('weatherwise.place', JSON.stringify({ name: 'Kisumu', label: 'Kenya', lat: -0.1, lon: 34.75 }))
    stubApi({ '/api/place': [422, { error: 'not_covered', message: 'not covered', country_code: 'ke' }] })
    window.history.pushState(null, '', '/app')
    render(<App />)
    await screen.findByText(textFor('mr')('notCovered.title'))
    expect(document.body.textContent).not.toContain('1077')
  })

  it('switching language changes every word on the screen', async () => {
    localStorage.setItem('weatherwise.place', JSON.stringify(place))
    stubApi({ '/api/place': [200, outlook(true)] })
    window.history.pushState(null, '', '/app')
    render(<App />)
    await screen.findByText(textFor('en')('today.whatToDo'))
    const picker = screen.getAllByRole('combobox')[0] as HTMLSelectElement
    picker.value = 'mr'
    picker.dispatchEvent(new Event('change', { bubbles: true }))
    await screen.findByText(textFor('mr')('today.whatToDo'))
    expect(screen.queryByText(textFor('en')('today.whatToDo'))).toBeNull()
    expect(screen.getByText(textFor('mr')('tabs.help'))).toBeTruthy()
    expectOnlyLanguage('mr')
  })
})
