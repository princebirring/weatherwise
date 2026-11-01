import type { ReactNode } from 'react'
import { api } from '../../api'
import { ErrorBox, Loading } from '../../components/Shell'
import { useAsync } from '../../components/useAsync'
import { useLanguage } from '../../text'
import type { Rules } from '../../types'

// Every number here comes from GET /api/rules (read from rules/ by the API), never from this file.
// Only the drawing range of each gauge is chosen here.
const HEAT_RANGE: [number, number] = [34, 50]
const RAIN_TOP_SHARE = 1.12 // the rain gauge ends a little above the "move now" line

interface Mark { at: number; label: ReactNode; value: string; ours?: boolean }
interface Zone { from: number; to: number; kind: string }

/** A vertical gauge: coloured zones, and lines labelled on the right at their true height. */
function Gauge({ title, low, high, marks, zones }: { title: string; low: number; high: number; marks: Mark[]; zones: Zone[] }) {
  const pos = (v: number) => `${((Math.min(Math.max(v, low), high) - low) / (high - low)) * 100}%`
  return (
    <div className="gauge">
      <b className="gauge-title">{title}</b>
      <div className="gauge-body">
        <div className="gauge-bar">
          {zones.map((z) => <i key={z.kind} className={`zone ${z.kind}`} style={{ bottom: pos(z.from), height: `calc(${pos(z.to)} - ${pos(z.from)})` }} />)}
        </div>
        <ol className="gauge-marks">
          {marks.map((m) => (
            <li key={m.value} style={{ bottom: pos(m.at) }}>
              <span className="gauge-value">{m.value}</span>
              <span className="gauge-label">{m.label}{m.ours && <Ours />}</span>
            </li>
          ))}
        </ol>
      </div>
    </div>
  )
}

function Ours() {
  const { t } = useLanguage()
  return <span className="tag ours">{t('show.oursTag')}</span>
}

const Imd = () => <span className="tag imd" lang="en">IMD</span>

export function RulesDiagram() {
  const rules = useAsync(() => api.rules(), 'rules')
  if (rules.loading) return <Loading />
  if (rules.error) return <ErrorBox error={rules.error} retry={rules.retry} />
  return rules.data ? <Scales r={rules.data} /> : null
}

function Scales({ r }: { r: Rules }) {
  const { t } = useLanguage()
  const h = r.heat
  const rain = r.rain_mm
  const g = r.flood_guide
  const pct = (x: number) => `${Math.round(x * 100)}%`
  const signals = new Set(g.prepare_signals)

  return (
    <div className="stack" style={{ gap: 18 }}>
      <div className="decide-grid">
        <article className="decide-card">
          <Gauge title={t('show.heatScale')} low={HEAT_RANGE[0]} high={HEAT_RANGE[1]}
            zones={[
              { from: h.work_heat_c.take_care, to: h.work_heat_c.danger, kind: 'care' },
              { from: h.work_heat_c.danger, to: h.absolute_c, kind: 'danger' },
              { from: h.absolute_c, to: HEAT_RANGE[1], kind: 'severe' },
            ]}
            marks={[
              { at: h.work_heat_c.take_care, value: `${h.work_heat_c.take_care}°`, label: t('show.markTakeCare'), ours: true },
              { at: h.work_heat_c.danger, value: `${h.work_heat_c.danger}°`, label: t('show.markDanger'), ours: true },
              { at: h.absolute_c, value: `${h.absolute_c}°`, label: <>{t('show.markHeatWave')} <Imd /></> },
            ]} />
          <ul className="decide-notes">
            <li><Imd /> {t('show.markHeatWave')}: ≥ {h.base_tmax_c.plains} °C, {h.departure_c} °C {t('show.aboveNormal')}</li>
            <li>{t('show.daysRunning', h.min_days)} · {t('show.runsAgree', pct(h.agreement))}</li>
            <li><Ours /> {t('show.excessNote')}</li>
          </ul>
        </article>

        <article className="decide-card">
          <Gauge title={t('show.rainScale')} low={0} high={rain.extremely_heavy * RAIN_TOP_SHARE}
            zones={[
              { from: r.unusual_rain.min_mm, to: rain.extremely_heavy, kind: 'prepare' },
              { from: rain.extremely_heavy, to: rain.extremely_heavy * RAIN_TOP_SHARE, kind: 'urgent' },
            ]}
            marks={[
              ...(signals.has('unusual_rain') ? [{ at: r.unusual_rain.min_mm, value: `≥ ${r.unusual_rain.min_mm}`, label: t('show.markUnusual', r.unusual_rain.min_mm), ours: true }] : []),
              { at: rain.heavy, value: `${rain.heavy}`, label: <>{t('show.markHeavy', g.heavy_rain_days_in_a_row)} <Imd /></> },
              { at: rain.very_heavy, value: `${rain.very_heavy}`, label: <>{t('show.markVeryHeavy')} <Imd /></> },
              { at: rain.extremely_heavy, value: `${rain.extremely_heavy}`, label: <>{t('show.markExtreme')} <Imd /></> },
            ]} />
          <div className="decide-split">
            <div>
              <b className="zone-key key-prepare">{t('show.zonePrepare')}</b>
              <ul className="decide-notes">
                <li>{t('show.startsPrepare')}: {t('show.markVeryHeavy')}, {t('show.markHeavy', g.heavy_rain_days_in_a_row)}</li>
                {signals.has('river_flood') && <li><Ours /> {t('show.riverNote', r.river_return_period_years)}</li>}
                <li>{t('show.alertOrange')}</li>
              </ul>
            </div>
            <div>
              <b className="zone-key key-urgent">{t('show.zoneUrgent')}</b>
              <ul className="decide-notes">
                <li>{t('show.alertRed')}</li>
                <li>{t('show.markExtreme')} ≥ {rain.extremely_heavy} mm</li>
              </ul>
            </div>
          </div>
        </article>
      </div>

      <div className="grid-auto">
        <p className="rule-tile"><b>{t('show.rule2b')}</b> {t('show.rule2t')}</p>
        <p className="rule-tile">{t('show.ruleStays', g.stay_on_quiet_days)}</p>
        <p className="rule-tile">{t('show.ruleCorrect', r.correction.training_days)}</p>
      </div>
    </div>
  )
}
