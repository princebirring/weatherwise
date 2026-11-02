// Every screen, in every language: it renders, shows that language's words and safety text,
// and (for Hindi and Marathi) shows no English sentence from the site or the safety advice.
import { cleanup, fireEvent, render, screen, waitFor, within } from '@testing-library/react'
import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'
import type { ReactNode } from 'react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import App from '../App'
import { ApiError } from '../api'
import { shortDate, weekday } from '../hazards'
import { LanguageProvider, textFor } from '../text'
import { en, type TextKey } from '../text/en'
import { HazardPage } from '../screens/Hazard'
import { Help } from '../screens/Help'
import { Home } from '../screens/Home'
import { NotCovered } from '../screens/NotCovered'
import { Showcase } from '../screens/Showcase'
import { countOf, SAFETY, SCORECARD } from '../screens/site/results'
import { TEAM } from '../screens/site/team'
import { Welcome } from '../screens/Welcome'
import { AppHeader } from '../components/Shell'
import { Ask } from '../screens/Ask'
import type { Language } from '../types'
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

  it('Today on a calm day: your day in plain sentences, and three quiet danger lights', () => {
    show(language, <Home place={place} official={idle} data={loaded(outlook(false))} offline={false} install={null} />)
    const days = outlook(false).outlook.days
    const day = document.querySelector('.day-card')!.textContent ?? ''
    const dryDays = days.filter((d) => !d.rainy_day).map((d) => weekday(d.day, language)).join(', ')
    expect(day).toContain(t('week.sprayDays', dryDays))                 // every day but the rainy one
    expect(day).toContain(t('day.rainUpTo', 12))                        // the one rainy day
    expect(day).toContain(t('day.hot', 45))
    const tiles = [...document.querySelectorAll('a.tile')]
    expect(tiles.map((x) => x.getAttribute('href'))).toEqual(['/app/heat', '/app/flood', '/app/dry'])
    for (const x of tiles) expect(x.textContent).toContain(t('watch.quiet'))
    expect(document.querySelector('.danger-banner')).toBeNull()
    expect(screen.getByText(t('official.none'))).toBeTruthy() // SACHET checked: nothing in force
    // Never an all-clear: our checks do not see cyclones or official alerts, so IMD is one tap away.
    expect(document.body.textContent).not.toMatch(/safe to work|काम करणे सुरक्षित|काम करना सुरक्षित/i)
    expectOnlyLanguage(language)
  })

  it('Today on a danger day: a banner on top, one button to what to do, the light lit', () => {
    show(language, <Home place={place} official={idle} data={loaded(outlook(true))} offline={false} install={null} />)
    const banner = document.querySelector('.danger-banner')!
    expect(banner.querySelector('h2')?.textContent).toBe(t('hazard.heat_wave'))
    expect(screen.getByText(t('today.whatToDo')).closest('a')?.getAttribute('href')).toBe('/app/heat')
    const [heat, flood, dry] = [...document.querySelectorAll('a.tile')]
    expect(heat.className).toContain('lv-orange')
    expect(heat.textContent).toContain(t('level.orange'))               // IMD orange: be prepared
    expect(flood.textContent).toContain(t('watch.quiet'))
    expect(dry.textContent).toContain(t('level.yellow'))
    // A heat-wave day is never called good for spraying.
    const days = outlook(true).outlook.days
    expect(document.querySelector('.day-card')!.textContent).not.toContain(weekday(days[3].day, language))
    expectOnlyLanguage(language)
  })

  it('Today: the flood guide on prepare (an official orange alert) lights the flood light', () => {
    show(language, <Home place={place} official={idle} data={loaded(outlook(false, 'prepare'))} offline={false} install={null} />)
    expect(document.querySelector('.danger-banner h2')?.textContent).toBe(t('flood.prepareTitle'))
    expect(screen.getByText(t('today.whatToDo')).closest('a')?.getAttribute('href')).toBe('/app/flood')
    expect(screen.getByText(t('tile.flood')).closest('a')!.className).toContain('lv-orange')
    expectOnlyLanguage(language)
  })

  it('Today offline: says the forecast shown is the saved one', () => {
    show(language, <Home place={place} official={idle} data={loaded(outlook(false))} offline install={null} />)
    expect(screen.getByText(t('offline.banner', shortDate(outlook(false).outlook.issue_date, language)))).toBeTruthy()
    expectOnlyLanguage(language)
  })

  it('An official watch comes first, slim, in this language, with who issued it', () => {
    const alerts = { status: 'ok' as const, alerts: [telanganaWatch], source: 'SACHET' }
    show(language, <Home place={place} official={idle} data={loaded(outlook(false, null, alerts))} offline={false} install={null} />)
    const card = document.querySelector('article.official')!
    expect(card.compareDocumentPosition(document.querySelector('.day-card')!) & Node.DOCUMENT_POSITION_FOLLOWING).toBeTruthy()
    expect(card.querySelector('h2')?.textContent).toBe(language === 'en' ? telanganaWatch.event : t('event.thunderstorm'))
    expect(card.textContent).toContain(t('official.kicker', 'Telangana SDMA'))
    expect(card.textContent).toContain(t('official.level.yellow'))
    expect(card.querySelector('details')!.textContent).toContain(telanganaWatch.translations[language])
    expect(screen.queryByText(t('official.none'))).toBeNull()
    expectOnlyLanguage(language)
  })

  it('An official warning with no translation shows the original and says so', () => {
    const untranslated = { ...telanganaWatch, translations: { en: telanganaWatch.translations.en } }
    show(language, <Home place={place} official={idle} data={loaded(outlook(false, null, { status: 'ok', alerts: [untranslated], source: 'S' }))}
      offline={false} install={null} />)
    const card = document.querySelector('article.official')!
    expect(card.textContent).toContain(telanganaWatch.message)
    if (language !== 'en') expect(card.textContent).toContain(t('official.original', '').trim().split(' ')[0])
  })

  it('Official warnings still show when our forecast is down', () => {
    const forecastDown = { data: null, error: new ApiError('failed', 'Open-Meteo rate limit', 502), loading: false, retry: () => {} }
    show(language, <Home place={place} data={forecastDown}
      official={loaded({ status: 'ok' as const, alerts: [telanganaWatch], source: 'SACHET' })} offline={false} install={null} />)
    const card = document.querySelector('article.official')!
    expect(card.textContent).toContain(telanganaWatch.translations[language])
    const error = screen.getByText(t('state.failed'))
    expect(card.compareDocumentPosition(error) & Node.DOCUMENT_POSITION_FOLLOWING).toBeTruthy() // warning first
  })

  it('If official warnings cannot be checked, it says so: never "none"', () => {
    show(language, <Home place={place} official={idle} data={loaded(outlook(false, null, { status: 'unavailable', alerts: [], source: null }))}
      offline={false} install={null} />)
    expect(screen.getByText(t('official.unavailable'))).toBeTruthy()
    expect(screen.queryByText(t('official.none'))).toBeNull()
    expectOnlyLanguage(language)
  })

  it('An official red alert: the whole screen is that message and the calls, even before our forecast', () => {
    const red = { ...telanganaWatch, level: 'red' as const }
    const loading = { data: null, error: null, loading: true, retry: () => {} }
    show(language, <Home place={place} official={loaded({ status: 'ok' as const, alerts: [red], source: 'SACHET' })} data={loading}
      offline={false} install={null} />)
    const main = document.querySelector('main.emergency')!
    expect(main.textContent).toContain(t('official.level.red'))
    expect(main.textContent).toContain(red.translations[language])
    for (const n of ['112', '1077']) expect(main.querySelector(`a[href="tel:${n}"]`)).toBeTruthy()
    expect(screen.queryByText(t('day.title'))).toBeNull()
    expect(document.querySelector('.tiles')).toBeNull()
    expectOnlyLanguage(language)
  })

  it('Flood "move now" from our rain check: one message, the calls, the shelter names', () => {
    show(language, <Home place={place} official={idle} data={loaded(outlook(false, 'urgent'))} offline={false} install={null} />)
    const main = document.querySelector('main.emergency')!
    expect(main.textContent).toContain(g.flood_urgent)
    expect(main.textContent).toContain(t('flood.urgentWhy'))
    expect(screen.getByText(t('flood.shelterNames')).closest('a')?.getAttribute('href')).toBe('/app/flood')
    expectOnlyLanguage(language)
  })

  it('Too hot to work: the level advice comes first, in this language', () => {
    const data = outlook(false)
    data.outlook.detections = [{ hazard: 'work_heat', severity: 'danger', first_day: '2026-04-24', last_day: '2026-04-24',
      days_ahead: 2, agreement: 0.8, evidence: { rule: 'ours (feels-like heat for outdoor work)' } }]
    show(language, <HazardPage group="heat" place={place} data={loaded(data)} />)
    const advice = [...document.querySelectorAll('.advice-text')].map((e) => e.textContent)
    expect(advice[0]).toBe(g.work_heat.danger)
    expect(advice[1]).toBe(g.heat[0].what)
    expectOnlyLanguage(language)
  })

  it('Heat page: the warning, all the advice at once, call 108, cooling place, send to family', async () => {
    show(language, <HazardPage group="heat" place={place} data={loaded(outlook(true))} />)
    expect(screen.getByRole('heading', { level: 1 }).textContent).toBe(t('group.heat'))
    expect(screen.getAllByRole('heading', { level: 2 })[0].textContent).toBe(t('hazard.heat_wave'))
    expect(screen.getByText(t('page.whatNow'))).toBeTruthy()
    for (const a of g.heat) expect(screen.getByText(a.what)).toBeTruthy()
    expect(screen.getByText(g.heat[0].who)).toBeTruthy()
    expect(document.querySelector('.advice a[href="tel:108"]')).toBeTruthy()
    expect(screen.getByText(t('today.share'))).toBeTruthy()
    await screen.findByText(t('shelter.noneNearHeat', 20))
    expect(screen.getByText(t('shelter.healthTitle'))).toBeTruthy()
    expectOnlyLanguage(language)
  })

  it('Heat page on a calm day: says nothing was found, and what to do when heat comes', () => {
    show(language, <HazardPage group="heat" place={place} data={loaded(outlook(false))} />)
    expect(screen.getByText(t('page.calm.heat'))).toBeTruthy()
    expect(screen.getByText(t('page.when.heat'))).toBeTruthy()
    expect(screen.queryByText(t('today.share'))).toBeNull()
    expectOnlyLanguage(language)
  })

  it('Dry page: the dry spell and its advice', () => {
    show(language, <HazardPage group="dry" place={place} data={loaded(outlook(true))} />)
    expect(screen.getAllByRole('heading', { level: 2 })[0].textContent).toBe(t('hazard.dry_spell'))
    expect(screen.getByText(g.dry_spell[0].what)).toBeTruthy()
    expect(screen.getByText(g.sowing[0].what)).toBeTruthy()
    expectOnlyLanguage(language)
  })

  it('Flood page: steps as a checklist that remembers, shelter names, never a route', async () => {
    show(language, <HazardPage group="flood" place={place} data={loaded(outlook(false))} />)
    expect(screen.getByText(t('page.calm.flood'))).toBeTruthy()
    expect(screen.getByText(t('flood.calmBody'))).toBeTruthy()
    const first = screen.getByText(g.flood_village[0])
    fireEvent.click(first)
    expect((first.previousSibling as HTMLInputElement).checked).toBe(true)
    expect(localStorage.getItem(`weatherwise.flood_done.${place.lat},${place.lon},village`)).toBe('[0]')
    fireEvent.click(screen.getByRole('button', { name: t('flood.city') }))
    expect(screen.getByText(g.flood_city[0])).toBeTruthy()
    await screen.findByText(t('shelter.noRoute'))
    expect(screen.getByText(g.flood_safety_line)).toBeTruthy()
    expect(screen.queryByText(t('shelter.showWay'))).toBeNull()
    expectOnlyLanguage(language)
  })

  it('Flood page in urgent mode: one short message and the calls', () => {
    show(language, <HazardPage group="flood" place={place} data={loaded(outlook(false, 'urgent'))} />)
    expect(screen.getByText(g.flood_urgent)).toBeTruthy()
    expect(document.querySelector('a[href="tel:112"]')).toBeTruthy()
    expect(screen.queryByText(g.flood_village[0])).toBeNull()
    expectOnlyLanguage(language)
  })

  it('Help: one tap to every helpline', async () => {
    show(language, <Help place={place} flood={false} />)
    for (const n of ['112', '108', '1077']) expect(document.querySelector(`a[href="tel:${n}"]`)).toBeTruthy()
    expect(screen.getByText(t('help.sendLocation'))).toBeTruthy()
    await waitFor(() => expect(fetch).toHaveBeenCalled())
    expectOnlyLanguage(language)
  })

  it('The saved place shows a Change button, and changing it has a way back', () => {
    show(language, <AppHeader place={place} checked="2026-11-02" />)
    expect(screen.getByRole('link', { name: new RegExp(t('today.changePlace')) }).textContent).toContain(t('today.change'))
    cleanup()
    show(language, <Welcome onPlace={() => {}} current={place} />)
    expect(screen.getByRole('link', { name: t('start.keep', place.name) }).getAttribute('href')).toBe('/app')
    cleanup()
    show(language, <Welcome onPlace={() => {}} />)
    expect(screen.queryByRole('link', { name: t('start.keep', place.name) })).toBeNull() // first visit: nothing to keep
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

  // The public site: each page at its own path.
  const at = (path: string) => { window.history.pushState(null, '', path); return show(language, <Showcase />) }

  it('Landing: the pitch, the warnings ahead (misses on Impact), the AWS stack, coverage and the team', () => {
    at('/')
    expect(screen.getByText(t('site.headline'), { selector: 'h1' })).toBeTruthy()
    for (const r of SCORECARD) {
      if (r.outcome === 'ahead') expect(document.body.textContent).toContain(r.titles[language])
      else expect(document.body.textContent).not.toContain(r.titles[language])
    }
    expect(screen.getByRole('link', { name: new RegExp(t('site.impactAll', SCORECARD.length)) })).toBeTruthy()
    for (const name of ['Amazon ECS', 'Bedrock AgentCore', 'Climate Risk MCP']) expect(screen.getByText(name, { selector: '.stack-flow b' })).toBeTruthy()
    expect(screen.getByAltText(t('site.globeAlt'))).toBeTruthy()
    for (const m of TEAM) expect(screen.getByRole('heading', { name: m.name })).toBeTruthy()
    expectOnlyLanguage(language)
  })

  it('Impact: every replayed disaster, misses included', () => {
    at('/impact')
    for (const r of SCORECARD) expect(screen.getByText(r.titles[language])).toBeTruthy()
    expect(screen.getAllByText(t('site.missed'))).toHaveLength(countOf('missed'))
  })

  it('Nothing is claimed that is not built (plans only in the About roadmap)', () => {
    at('/')
    expect(document.body.textContent).not.toMatch(/WhatsApp|SMS|6 AM/)
    expect(document.body.textContent).not.toMatch(/\b1 days\b/)
    cleanup()
    at('/about')
    const roadmap = document.querySelector('.roadmap')!.textContent ?? ''
    expect((document.body.textContent ?? '').replace(roadmap, '')).not.toMatch(/WhatsApp|SMS|6 AM/)
    for (const m of TEAM) expect(screen.getByRole('heading', { name: m.name })).toBeTruthy()
  })

  it('Header links open the pages, and an unknown path shows the landing page', () => {
    vi.spyOn(window, 'scrollTo').mockImplementation(() => {}) // jsdom has no scrolling
    at('/nowhere')
    expect(window.location.pathname).toBe('/')
    fireEvent.click(screen.getAllByRole('link', { name: t('site.navImpact') })[0])
    expect(screen.getByText(t('site.proofTitle', SCORECARD.length), { selector: 'h1' })).toBeTruthy()
    expect(window.location.pathname).toBe('/impact')
    fireEvent.click(screen.getAllByRole('link', { name: t('site.navDevelopers') })[0])
    expect(screen.getByText('hazard_outlook')).toBeTruthy()
    fireEvent.click(screen.getAllByRole('link', { name: t('site.navAbout') })[0])
    expect(screen.getByText(t('site.aboutTitle'), { selector: 'h1' })).toBeTruthy()
  })

  it('An old /proof link opens Impact, at its new address', () => {
    at('/proof')
    expect(window.location.pathname).toBe('/impact')
    expect(screen.getByText(t('site.proofTitle', SCORECARD.length), { selector: 'h1' })).toBeTruthy()
  })

  it('Impact: replay titles and scores in this language', async () => {
    at('/impact')
    await screen.findAllByText(events[0].titles[language])
    expect(screen.getAllByText(t('show.replayTitle')).length).toBeGreaterThan(0)
    await screen.findAllByText(new RegExp(t('show.far')))
    expect(screen.getByText(t('show.riverAxis', '1,321'))).toBeTruthy()
    expect(screen.getByText(t('show.limit1'))).toBeTruthy()
    expectOnlyLanguage(language)
  })

  it('How it works: how a warning is decided, with every line from the rules file', async () => {
    at('/how-it-works')
    for (const name of ['Strands Agents', 'Amazon Bedrock AgentCore', 'Climate Risk MCP server']) expect(screen.getByRole('heading', { name })).toBeTruthy()
    await screen.findAllByText(new RegExp(t('show.markVeryHeavy')))
    const decide = document.getElementById('decide')!.textContent ?? ''
    for (const v of [rules.rain_mm.very_heavy, rules.rain_mm.extremely_heavy, rules.heat.absolute_c]) expect(decide).toContain(String(v))
    expect(decide).toContain(t('show.ruleStays', rules.flood_guide.stay_on_quiet_days))
    expect(decide).toContain(t('show.oursTag'))
    expectOnlyLanguage(language)
  })

  it('Landing: the phone runs the real app screens; taps move the phone, never the page', () => {
    at('/')
    const phone = within(screen.getByRole('region', { name: t('show.demoLabel') }))
    expect(phone.getByText(t('hazard.work_heat:danger'))).toBeTruthy()      // Today, with a heat warning
    fireEvent.click(phone.getByRole('link', { name: new RegExp(t('today.whatToDo')) }))
    expect(phone.getByText(g.work_heat.danger)).toBeTruthy()                 // the heat page's real advice
    fireEvent.click(phone.getByRole('link', { name: t('todo.call108') }))
    expect(phone.getByText(t('show.demoCall', '108'))).toBeTruthy()          // never dials from the page
    fireEvent.click(screen.getByRole('tab', { name: t('show.zoneUrgent') }))
    expect(phone.getByText(g.flood_urgent)).toBeTruthy()
    fireEvent.click(screen.getByRole('tab', { name: t('today.floodGuide') }))
    expect(phone.getByText(g.flood_village[1])).toBeTruthy()                 // the flood checklist
    fireEvent.click(document.querySelector('.phone .tabbar .tab-help')!)
    expect(phone.getByRole('heading', { name: t('help.title') })).toBeTruthy()
    expect(window.location.pathname).toBe('/')
  })

  it('How it works: the tech flow shows the Today journey, then the Ask journey', () => {
    at('/how-it-works')
    expect(screen.getByText(t('show.today4'))).toBeTruthy()
    fireEvent.click(screen.getByRole('tab', { name: t('show.flowAsk') }))
    expect(screen.getByText(t('show.ask6'))).toBeTruthy()
    expect(screen.queryByText(t('show.today4'))).toBeNull()
  })

  it('Impact: a flood from rain is charted as rain, against the place\'s own line', async () => {
    const rainFlood = { ...replay, unusual_rain_mm: 44.6, timeline: replay.timeline.map((d, i) => ({
      ...d, what_happened: i === 2 ? ['unusual_rain'] : [], observed: { ...d.observed, rain_mm: [3, 45, 186, 94][i] } })) }
    stubApi({ '/api/replays/': [200, rainFlood] })
    at('/impact')
    expect(await screen.findByText(t('show.rainAxis', 45))).toBeTruthy()
    expectOnlyLanguage(language)
  })
})

describe('the public site\'s numbers match the eval results', () => {
  // The scorecard and safety numbers are copied into the site; these fail if a re-run changes them.
  const replaysMd = readFileSync(resolve(process.cwd(), '../evals/results/REPLAYS.md'), 'utf8')
  const safetyMd = readFileSync(resolve(process.cwd(), '../evals/results/SAFETY.md'), 'utf8')

  it('every replayed event, with the same result', () => {
    const rows = replaysMd.split('\n').filter((l) => /^\| .+ \| (heat|flood) \|/.test(l))
    expect(rows).toHaveLength(SCORECARD.length)
    for (const r of SCORECARD) {
      const row = rows.find((l) => l.startsWith(`| ${r.titles.en.replace('°C', 'deg C')} | ${r.kind} |`))
      expect(row, r.id).toBeTruthy()
      const result = row!.split(' | ')[2]
      if (r.outcome === 'ahead') expect(result).toBe(`**warned ${r.days} days ahead**`)
      if (r.outcome === 'partly') expect(result).toMatch(new RegExp(`caught on the day.* ${r.days} days ahead`))
      if (r.outcome === 'conditions') expect(result).toBe('conditions only')
      if (r.outcome === 'missed') expect(result).toBe('**missed**')
    }
  })

  it('the safety evals', () => {
    for (const [a, b] of Object.values(SAFETY)) expect(safetyMd).toContain(`**${a}/${b}**`)
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

  it('an old warning link opens the page for that danger', async () => {
    localStorage.setItem('weatherwise.place', JSON.stringify(place))
    stubApi({ '/api/place': [200, outlook(true)] })
    window.history.pushState(null, '', '/app/todo/1') // the dry spell, in the old numbering
    render(<App />)
    await screen.findByText(textFor('en')('page.whatNow'))
    expect(window.location.pathname).toBe('/app/dry')
  })

  it('a link with a place opens that place\'s danger page, and keeps the place', async () => {
    stubApi({ '/api/place': [200, outlook(false, 'prepare')] })
    window.history.pushState(null, '', '/app/flood?lat=16.704&lon=74.243&name=Kolhapur')
    render(<App />)
    await screen.findByText(textFor('en')('flood.stepsTitle'))
    expect(window.location.search).toBe('')
    const kept = JSON.parse(localStorage.getItem('weatherwise.place')!)
    expect([kept.lat, kept.lon]).toEqual([16.7, 74.24])
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
    show('mr', <Home place={place} official={idle} data={loaded(outlook(true))} offline={false} install={null} />)
    fireEvent.click(screen.getByRole('button', { name: t('listen.play') }))
    expect(said).toHaveLength(1)
    expect(said[0].text).toContain(t('tile.heat'))
    expect(said[0].text).toContain(t('level.orange'))
    expect(said[0].lang).toBe('mr-IN')
    fireEvent.click(screen.getByRole('button', { name: t('listen.stop') }))
    expect(engine.cancel).toHaveBeenCalled()
    expect(screen.getByRole('button', { name: t('listen.play') })).toBeTruthy()
    expectOnlyLanguage('mr')
  })

  it('no Marathi voice on the phone: no button, never Marathi read by an English voice', () => {
    fakePhone(['en-IN', 'hi-IN'])
    show('mr', <Home place={place} official={idle} data={loaded(outlook(true))} offline={false} install={null} />)
    expect(screen.queryByRole('button', { name: textFor('mr')('listen.play') })).toBeNull()
  })

  it('no speech engine at all (older browsers): no button', () => {
    show('en', <Home place={place} official={idle} data={loaded(outlook(true))} offline={false} install={null} />)
    expect(screen.queryByRole('button', { name: 'Listen' })).toBeNull()
  })
})
