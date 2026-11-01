// Every screen, in every language: it renders, shows that language's words and safety text,
// and (for Hindi and Marathi) shows no English sentence from the site or the safety advice.
import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react'
import type { ReactNode } from 'react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import App from '../App'
import { ApiError } from '../api'
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
import { events, outlook, place, policy, replay, rules, shelters, status, telanganaWatch } from './fixtures/data'

const LANGUAGES: Language[] = ['en', 'hi', 'mr']
// Names kept on purpose: the brand, data sources, and the technical agent name next to its translation.
const SAME_IN_ALL = new Set<TextKey>(['brand.name'])

// Every English sentence the site or the safety advice could show (short words like "Heat" skipped).
const ENGLISH_SENTENCES = [
  ...Object.entries(en).filter(([k]) => !SAME_IN_ALL.has(k as TextKey)).map(([, v]) => v),
  ...Object.values(policy.guidance.en).flatMap((v): string[] =>
    typeof v === 'string' ? [v]
      : Array.isArray(v) ? v.flatMap((x: string | { who: string; what: string }) => (typeof x === 'string' ? [x] : [x.who, x.what]))
        : Object.values(v)), // a table of texts, e.g. work_heat by level
].map((s) => s.split('{name}')[0].trim()).filter((s) => s.length >= 12)

const loaded = <T,>(data: T) => ({ data, error: null, loading: false, retry: () => {} })
// Official warnings not fetched separately: Today falls back to those inside the forecast.
const idle = { data: null, error: null, loading: false, retry: () => {} }

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
    '/api/policy': [200, policy], '/api/status': [200, status], '/api/rules': [200, rules], ...overrides,
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
    show(language, <Home place={place} official={idle} data={loaded(outlook(true))} status={status} onPlace={() => {}} />)
    expect(screen.getByRole('heading', { level: 1 }).textContent).toBe(t('hazard.heat_wave'))
    expect(screen.getByText(t('today.whatToDo'))).toBeTruthy()
    expect(screen.getByText(t('today.share'))).toBeTruthy()
    expect(screen.getByText(t('chip.upTo', 45))).toBeTruthy()
    expect(screen.getByText(t('likely.high'))).toBeTruthy()
    expect(screen.getByText(t('hazard.dry_spell'))).toBeTruthy() // "also coming"
    expectOnlyLanguage(language)
  })

  it('Today on a safe day', () => {
    show(language, <Home place={place} official={idle} data={loaded(outlook(false))} status={status} onPlace={() => {}} />)
    expect(screen.getByText(t('today.safeTitle'))).toBeTruthy()
    expect(screen.queryByText(t('today.whatToDo'))).toBeNull()
    // Never an all-clear: our checks do not see cyclones or official alerts, so IMD is one tap away.
    expect(document.body.textContent).not.toMatch(/safe to work|काम करणे सुरक्षित|काम करना सुरक्षित/i)
    expect(screen.getByText(t('official.none'))).toBeTruthy() // SACHET checked: nothing in force
    expectOnlyLanguage(language)
  })

  it('Official warnings come first, in this language, with who issued them', () => {
    const alerts = { status: 'ok' as const, alerts: [telanganaWatch], source: 'SACHET' }
    show(language, <Home place={place} official={idle} data={loaded(outlook(false, null, alerts))} status={status} onPlace={() => {}} />)
    const card = document.querySelector('article.official')!
    expect(card).toBeTruthy()
    expect(card.compareDocumentPosition(document.querySelector('.hero-card')!) & Node.DOCUMENT_POSITION_FOLLOWING).toBeTruthy()
    expect(card.textContent).toContain(telanganaWatch.translations[language])
    expect(card.querySelector('h1')?.textContent).toBe(language === 'en' ? telanganaWatch.event : t('event.thunderstorm'))
    expect(card.textContent).toContain(t('official.level.yellow'))
    expect(card.textContent).toContain(t('official.kicker', 'Telangana SDMA'))
    expect(screen.getByText(t('today.nothingMore'))).toBeTruthy()       // our checks follow, quietly
    expect(screen.queryByText(t('today.safeTitle'))).toBeNull()
    expectOnlyLanguage(language)
  })

  it('An official warning with no translation shows the original and says so', () => {
    const untranslated = { ...telanganaWatch, translations: { en: telanganaWatch.translations.en } }
    show(language, <Home place={place} official={idle} data={loaded(outlook(false, null, { status: 'ok', alerts: [untranslated], source: 'S' }))}
      status={status} onPlace={() => {}} />)
    const card = document.querySelector('article.official')!
    expect(card.textContent).toContain(telanganaWatch.message)
    if (language !== 'en') expect(card.textContent).toContain(t('official.original', '').trim().split(' ')[0])
  })

  it('Official warnings still show when our forecast is down', () => {
    const forecastDown = { data: null, error: new ApiError('failed', 'Open-Meteo rate limit', 502), loading: false, retry: () => {} }
    show(language, <Home place={place} data={forecastDown}
      official={loaded({ status: 'ok' as const, alerts: [telanganaWatch], source: 'SACHET' })} status={status} onPlace={() => {}} />)
    const card = document.querySelector('article.official')!
    expect(card.textContent).toContain(telanganaWatch.translations[language])
    const error = screen.getByText(t('state.failed'))
    expect(card.compareDocumentPosition(error) & Node.DOCUMENT_POSITION_FOLLOWING).toBeTruthy() // warning first
  })

  it('If official warnings cannot be checked, it says so: never "none"', () => {
    show(language, <Home place={place} official={idle} data={loaded(outlook(false, null, { status: 'unavailable', alerts: [], source: null }))}
      status={status} onPlace={() => {}} />)
    expect(screen.getByText(t('official.unavailable'))).toBeTruthy()
    expect(screen.queryByText(t('official.none'))).toBeNull()
    expectOnlyLanguage(language)
  })

  it('Too hot to work: the level advice comes first, in this language', async () => {
    const data = outlook(false)
    data.outlook.detections = [{ hazard: 'work_heat', severity: 'danger', first_day: '2026-04-24', last_day: '2026-04-24',
      days_ahead: 2, agreement: 0.8, evidence: { rule: 'ours (feels-like heat for outdoor work)' } }]
    show(language, <Todo index={0} data={loaded(data)} />)
    expect(screen.getByText(g.work_heat.danger)).toBeTruthy()
    screen.getByText(t('todo.next')).click()
    expect(await screen.findByText(g.heat[0].what)).toBeTruthy()
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
    expect(screen.getByText(t('show.riverAxis', '1,321'))).toBeTruthy()
    expectOnlyLanguage(language)
  })

  it('Showcase: how a warning is decided, with every line from the rules file', async () => {
    show(language, <Showcase />)
    await screen.findAllByText(new RegExp(t('show.markVeryHeavy')))
    const decide = document.getElementById('decide')!.textContent ?? ''
    for (const v of [rules.rain_mm.very_heavy, rules.rain_mm.extremely_heavy, rules.heat.absolute_c]) expect(decide).toContain(String(v))
    expect(decide).toContain(t('show.ruleStays', rules.flood_guide.stay_on_quiet_days))
    expect(decide).toContain(t('show.oursTag'))
    expectOnlyLanguage(language)
  })

  it('Showcase: the phone switches screens by its tabs, with the real advice text', () => {
    show(language, <Showcase />)
    expect(screen.getByText(t('hazard.work_heat:danger'))).toBeTruthy()
    fireEvent.click(screen.getByRole('tab', { name: t('show.zoneUrgent') }))
    expect(screen.getByText(g.flood_urgent)).toBeTruthy()
    fireEvent.click(screen.getByRole('tab', { name: t('show.tabHeat') }))
    fireEvent.click(screen.getByRole('button', { name: t('today.whatToDo') }))
    expect(screen.getByText(g.work_heat.danger)).toBeTruthy()
    fireEvent.click(screen.getByRole('button', { name: t('todo.next') }))
    expect(screen.getByText(g.heat[0].what)).toBeTruthy()            // the next real advice card
    fireEvent.click(screen.getByRole('tab', { name: t('today.floodGuide') }))
    fireEvent.click(screen.getByRole('button', { name: t('todo.next') }))
    expect(screen.getByText(g.flood_village[1])).toBeTruthy()        // flood guide, step 2
    fireEvent.click(screen.getByRole('button', { name: new RegExp(t('help.title')) }))
    fireEvent.click(screen.getByRole('button', { name: new RegExp(t('help.ambulance')) }))
    expect(screen.getByText(t('show.demoCall', '108'))).toBeTruthy()  // never dials from the page
  })

  it('Showcase: the tech flow shows the Today journey, then the Ask journey', () => {
    show(language, <Showcase />)
    expect(screen.getByText(t('show.today4'))).toBeTruthy()
    fireEvent.click(screen.getByRole('tab', { name: t('show.flowAsk') }))
    expect(screen.getByText(t('show.ask6'))).toBeTruthy()
    expect(screen.queryByText(t('show.today4'))).toBeNull()
  })

  it('Showcase: proof numbers come from the replays, and nothing is claimed that is not built', async () => {
    show(language, <Showcase />)
    await screen.findByText(t('show.statReplays'))
    expect(document.body.textContent).not.toMatch(/WhatsApp|6 AM/)
    expect(document.body.textContent).not.toMatch(/\b1 days\b/)
  })

  it('Showcase: a flood from rain is charted as rain, against the place\'s own line', async () => {
    const rainFlood = { ...replay, unusual_rain_mm: 44.6, timeline: replay.timeline.map((d, i) => ({
      ...d, what_happened: i === 2 ? ['unusual_rain'] : [], observed: { ...d.observed, rain_mm: [3, 45, 186, 94][i] } })) }
    stubApi({ '/api/replays/': [200, rainFlood] })
    show(language, <Showcase />)
    expect(await screen.findByText(t('show.rainAxis', 45))).toBeTruthy()
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

describe('Listen (the phone reads the card aloud)', () => {
  // A phone's speech engine with the given voices; records what it is asked to say.
  function fakePhone(voiceLangs: string[]) {
    const said: SpeechSynthesisUtterance[] = []
    const engine = {
      getVoices: () => voiceLangs.map((lang) => ({ lang, name: lang }) as SpeechSynthesisVoice),
      speak: vi.fn((u: SpeechSynthesisUtterance) => said.push(u)),
      cancel: vi.fn(),
      addEventListener: () => {}, removeEventListener: () => {},
    }
    vi.stubGlobal('speechSynthesis', engine)
    vi.stubGlobal('SpeechSynthesisUtterance', class { text: string; voice = null; lang = ''; rate = 1; onend = null; onerror = null
      constructor(text: string) { this.text = text } })
    return { engine, said }
  }

  it('reads the warning in Marathi with a Marathi voice, and Stop stops it', () => {
    const { engine, said } = fakePhone(['en-US', 'mr-IN'])
    const t = textFor('mr')
    show('mr', <Home place={place} official={idle} data={loaded(outlook(true))} status={status} onPlace={() => {}} />)
    fireEvent.click(screen.getByRole('button', { name: t('listen.play') }))
    expect(said).toHaveLength(1)
    expect(said[0].text).toContain(t('hazard.heat_wave'))
    expect(said[0].lang).toBe('mr-IN')
    fireEvent.click(screen.getByRole('button', { name: t('listen.stop') }))
    expect(engine.cancel).toHaveBeenCalled()
    expect(screen.getByRole('button', { name: t('listen.play') })).toBeTruthy()
    expectOnlyLanguage('mr')
  })

  it('no Marathi voice on the phone: no button, never Marathi read by an English voice', () => {
    fakePhone(['en-IN', 'hi-IN'])
    show('mr', <Home place={place} official={idle} data={loaded(outlook(true))} status={status} onPlace={() => {}} />)
    expect(screen.queryByRole('button', { name: textFor('mr')('listen.play') })).toBeNull()
  })

  it('no speech engine at all (older browsers): no button', () => {
    show('en', <Home place={place} official={idle} data={loaded(outlook(true))} status={status} onPlace={() => {}} />)
    expect(screen.queryByRole('button', { name: 'Listen' })).toBeNull()
  })
})
