import { api } from '../../api'
import { Icon, type IconName } from '../../components/Icon'
import { ErrorBox, Loading } from '../../components/Shell'
import { useAsync } from '../../components/useAsync'
import { useLanguage } from '../../text'
import type { TextKey } from '../../text/en'
import type { DailyPlace, DailyRun } from '../../types'
import { SectionTitle } from './SiteLayout'

const KIND: Record<string, { icon: IconName; label: TextKey }> = {
  heat_dry: { icon: 'heat', label: 'site.liveHeat' },
  flood: { icon: 'waves', label: 'site.liveFlood' },
  all_clear: { icon: 'check', label: 'site.liveAllClear' },
}

/** This morning's run: the agent on AgentCore wrote a warning wherever code found a risk. */
export function LiveRun() {
  const { t } = useLanguage()
  const daily = useAsync(() => api.daily(), 'daily')
  const run = daily.data?.latest
  return (
    <div className="stack" style={{ gap: 18 }}>
      <SectionTitle kicker={t('site.liveKicker')} title={t('site.liveTitle')}
        lede={t('site.liveLede', run?.summary.places ?? 25)} />
      {daily.loading && <Loading />}
      {daily.error && <ErrorBox error={daily.error} retry={daily.retry} />}
      {daily.data && !run && <p className="live-empty">{t('site.liveNotYet')}</p>}
      {run && <Run run={run} history={daily.data?.history ?? []} />}
    </div>
  )
}

function Run({ run, history }: { run: DailyRun; history: { run_date: string; warnings_written: number }[] }) {
  const { t } = useLanguage()
  const s = run.summary
  const written = run.places.filter((p) => p.ok && p.hazard_kind)
  const quiet = run.places.filter((p) => p.ok && !p.hazard_kind)
  const failed = run.places.filter((p) => !p.ok)
  const cost = s.model_cost_usd == null ? '-' : `$${s.model_cost_usd.toFixed(s.model_cost_usd < 0.1 ? 3 : 2)}`
  return (
    <>
      <div className="safety live-sums">
        <div><b>{s.finished}/{s.places}</b><span>{t('site.livePlaces')}</span></div>
        <div><b>{s.warnings_written}</b><span>{t('site.liveWritten', s.updates_of_earlier_warnings ?? 0)}</span></div>
        <div><b>{s.all_clears ?? 0}</b><span>{t('site.liveCleared')}</span></div>
        <div><b>{s.drafts_sent_back_by_evaluator}</b><span>{t('site.liveSentBack')}</span></div>
        <div><b>{cost}</b><span>{t('site.liveCost', s.model_calls)}</span></div>
        <p>{t('site.liveWhen', run.run_date)} · {run.model_id}</p>
      </div>
      {written.length > 0 && <ol className="live-list">{written.map((p) => <Place key={p.place.name} p={p} />)}</ol>}
      {quiet.length > 0 && (
        <p className="live-quiet"><b>{t('site.liveQuiet', quiet.length)}</b> {quiet.map((p) => p.place.name).join(', ')}</p>
      )}
      {failed.length > 0 && (
        <p className="live-quiet"><b>{t('site.liveFailed', failed.length)}</b> {failed.map((p) => p.place.name).join(', ')}</p>
      )}
      {history.length > 1 && (
        <p className="live-quiet"><b>{t('site.liveHistory')}</b>{' '}
          {history.map((h) => `${h.run_date}: ${h.warnings_written}`).join(' · ')}</p>
      )}
    </>
  )
}

function Place({ p }: { p: DailyPlace }) {
  const { t } = useLanguage()
  const kind = KIND[p.hazard_kind ?? ''] ?? KIND.heat_dry
  const earlier = p.earlier_warnings?.at(-1)
  const sentBack = (p.evaluator_sent_back ?? []).flat()
  return (
    <li className="live-place">
      <div className="live-head">
        <Icon name={kind.icon} size={20} label={t(kind.label)} />
        <b>{p.place.name}</b>
        <span>{t(kind.label)}</span>
        {earlier && p.hazard_kind !== 'all_clear' && <span className="live-tag">{t('site.liveUpdate', earlier.day)}</span>}
      </div>
      {p.hazard_kind === 'flood' && !!p.flood_guide?.reasons.length && (
        <p className="live-check">{t('site.liveWhy', p.flood_guide.reasons.join(', '))}</p>
      )}
      <p className="live-msg">{p.body}</p>
      <p className="live-check">
        {p.model_error ? t('site.liveModelDown') : p.used_fallback ? t('site.liveFallback')
          : sentBack.length ? t('site.liveChecked', [...new Set(sentBack)].join(', ').replaceAll('_', ' '))
            : t('site.livePassed')}
      </p>
    </li>
  )
}
