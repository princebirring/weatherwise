import { useState } from 'react'
import { api } from '../../api'
import { ErrorBox, Loading } from '../../components/Shell'
import { useAsync } from '../../components/useAsync'
import { LOCALES } from '../../hazards'
import { useLanguage, type T } from '../../text'
import type { TextKey } from '../../text/en'
import type { HazardScore, Language, Replay, ReplayEvent } from '../../types'

// Real past events, replayed with only the forecasts that existed each morning.

const hazardName = (h: string, t: T) => t(`score.${h}` as TextKey)
const fullDate = (iso: string, language: Language) =>
  new Intl.DateTimeFormat(LOCALES[language], { day: 'numeric', month: 'short', year: 'numeric', timeZone: 'UTC' }).format(new Date(iso))

export function Replays({ events }: { events: ReplayEvent[] }) {
  const { t, language } = useLanguage()
  const [id, setId] = useState(events[0]?.id)
  const replay = useAsync(id ? () => api.replay(id) : null, id ?? '')
  return (
    <>
      <div className="tabs" role="tablist" aria-label={t('show.events')}>
        {events.map((e) => (
          <button key={e.id} type="button" role="tab" aria-selected={e.id === id} onClick={() => setId(e.id)}>{e.titles[language]}</button>
        ))}
      </div>
      <div className="card stack" role="tabpanel" style={{ padding: 22, borderRadius: 20, gap: 14 }}>
        {replay.loading && <Loading />}
        {replay.error && <ErrorBox error={replay.error} retry={replay.retry} />}
        {replay.data && <ReplayView r={replay.data} />}
      </div>
    </>
  )
}

type ChartKind = 'river' | 'rain' | 'heat'

/** What the replay's chart shows: the river if it flooded, else rain if the flood came from rain
 *  (towns flood from streams and drains too), else the day's top temperature. */
function chartKind(r: Replay): ChartKind {
  const happened = (e: string) => r.timeline.some((d) => d.what_happened.includes(e))
  if (r.flood_level_m3s !== null && happened('river_above_flood_level')) return 'river'
  if (happened('very_heavy_rain') || happened('unusual_rain')) return 'rain'
  return 'heat'
}

function ReplayView({ r }: { r: Replay }) {
  const { t, language } = useLanguage()
  const kind = chartKind(r)
  const line = kind === 'river' ? r.flood_level_m3s : kind === 'rain' ? r.unusual_rain_mm ?? null : null
  const metric = (d: Replay['timeline'][number]) =>
    (kind === 'river' ? d.observed.river_m3s : kind === 'rain' ? d.observed.rain_mm : d.observed.tmax) ?? null
  const values = r.timeline.map(metric)
  const known = values.filter((v): v is number => v !== null)
  const floor = kind === 'heat' ? Math.min(...known, ...r.timeline.map((d) => d.observed.normal_tmax ?? Infinity)) - 3 : 0
  const top = Math.max(...known, line !== null ? line * 1.04 : -Infinity)
  const y = (v: number) => ((v - floor) / (top - floor)) * 100
  const cols = { gridTemplateColumns: `repeat(${r.timeline.length}, minmax(0, 1fr))` }
  const scores = Object.values(r.verification.scores ?? {}).filter((s) => s.hits + s.misses + s.false_alarms > 0)
  const conditions = r.verification.conditions_met

  return (
    <>
      <div className="row" style={{ flexWrap: 'wrap', alignItems: 'baseline', gap: '6px 20px' }}>
        <b style={{ fontSize: 21 }}>{r.event.titles[language]}</b>
        <span className="small">
          {kind === 'river' ? t('show.riverAxis', Math.round(line ?? 0).toLocaleString('en-IN'))
            : kind === 'rain' ? t('show.rainAxis', Math.round(line ?? 0)) : t('show.tmaxAxis')}
        </span>
      </div>
      <div className="timeline">
        <div className="inner">
          <div className="plot" style={cols} role="img"
            aria-label={r.timeline.map((d, i) => `${d.day}: ${values[i] ?? '–'}${d.what_happened.length ? ` (${d.what_happened.join(', ')})` : ''}`).join('; ')}>
            {line !== null && <div className="refline" style={{ bottom: `${y(line)}%` }} />}
            {r.timeline.map((d, i) => (
              <div key={d.day} style={{ position: 'relative', height: '100%', display: 'flex', alignItems: 'flex-end' }}>
                <i className={d.what_happened.length ? 'hit' : ''} style={{ width: '100%', height: `${values[i] === null ? 0 : y(values[i] as number)}%` }} />
                {kind === 'heat' && d.observed.normal_tmax != null && (
                  <span style={{ position: 'absolute', left: 0, right: 0, bottom: `${y(d.observed.normal_tmax)}%`, borderTop: '2px dashed var(--ink)' }} />
                )}
              </div>
            ))}
          </div>
          <div className="marks" style={cols} aria-hidden="true">
            {r.timeline.map((d) => <span key={d.day} className={d.flood_guide ? 'guide' : d.would_have_sent.length ? 'warned' : ''} title={d.would_have_sent.join(', ')} />)}
          </div>
          <div className="labels" style={cols} aria-hidden="true">
            {r.timeline.map((d) => <span key={d.day}>{Number(d.day.slice(8))}</span>)}
          </div>
        </div>
      </div>
      <div className="legend" style={{ fontSize: 14, color: 'var(--ink-2)' }}>
        {r.timeline.some((d) => d.flood_guide) && <span><i className="swatch" style={{ background: 'var(--flood)' }} />{t('show.legendGuide')}</span>}
        <span><i className="swatch" style={{ background: '#9DB8DA' }} />{t('show.legendWarned')}</span>
        <span><i className="swatch" style={{ background: 'var(--red)' }} />{t('show.legendHappened')}</span>
      </div>

      <div className="grid-auto" style={{ gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))' }}>
        {scores.map((s) => <ScoreCards key={s.hazard} s={s} />)}
        {conditions && (
          <div className="mini">
            <b>{Object.values(conditions).filter((hs) => hs.includes('heat_wave')).length} / {Object.keys(conditions).length}</b>
            {t('show.conditionsDays')}
          </div>
        )}
      </div>
      <p className="small">{r.mode === 'as_issued' ? t('show.noArchive') : t('show.conditionsOnly')}</p>
    </>
  )
}

function ScoreCards({ s }: { s: HazardScore }) {
  const { t, language } = useLanguage()
  const name = hazardName(s.hazard, t)
  const lead = s.event_lead_days.find(([, l]) => l !== null)
  return (
    <>
      {lead && <div className="mini"><b>{lead[1]}</b>{t(lead[1] === 1 ? 'show.leadOne' : 'show.lead', fullDate(lead[0], language))} · {name}</div>}
      {s.pod !== null && <div className="mini"><b>{Math.round(s.pod * 100)}%</b>{t('show.pod')} · {name}</div>}
      <div className="mini"><b>{s.far === null ? '–' : `${Math.round(s.far * 100)}%`}</b>{t('show.far')} · {name}</div>
    </>
  )
}
