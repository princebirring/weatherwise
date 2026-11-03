import { dayIcon, dayLevel, weekday } from '../hazards'
import { useLanguage } from '../text'
import type { Outlook } from '../types'
import { Icon } from './Icon'

// Rain worth showing on the week strip: a whole millimetre or more (a display choice, not a warning line).
const wet = (mm: number | null) => mm !== null && Math.round(mm) >= 1
// The rain bars share one scale, at least 20 mm, so a drizzle never looks like a downpour.
const BAR_MM = 20

/** The 7-day strip: icon, high temperature and a rain bar per day, coloured by warning level. */
export function Week({ outlook }: { outlook: Outlook }) {
  const { t, language } = useLanguage()
  const scale = Math.max(BAR_MM, ...outlook.days.map((d) => d.rain_mm ?? 0))
  // In a dry week the bars would be seven empty tracks: leave them out.
  const anyRain = outlook.days.some((d) => wet(d.rain_mm))
  return (
    <section className="stack" style={{ gap: 8 }} aria-labelledby="week-heading">
      <h2 id="week-heading" className="h-mid">{t('today.week')}</h2>
      <ol className="week">
        {outlook.days.map((d) => {
          const level = dayLevel(d)
          return (
            <li key={d.day} className={level ?? ''} aria-label={`${weekday(d.day, language)}: ${d.tmax_c === null ? '–' : Math.round(d.tmax_c)}°${wet(d.rain_mm) ? `, ${t('today.rainMm', Math.round(d.rain_mm as number))}` : ''}, ${level ? t('today.danger') : t('today.noDanger')}`}>
              <span className="wd">{weekday(d.day, language)}</span>
              <Icon name={dayIcon(d)} size={26} />
              <b>{d.tmax_c === null ? '–' : `${Math.round(d.tmax_c)}°`}</b>
              {anyRain && <span className="rainbar" aria-hidden="true"><i style={{ height: `${wet(d.rain_mm) ? Math.max(12, ((d.rain_mm as number) / scale) * 100) : 0}%` }} /></span>}
              {anyRain && <span className="rain">{wet(d.rain_mm) ? t('today.rainMm', Math.round(d.rain_mm as number)) : ' '}</span>}
            </li>
          )
        })}
      </ol>
    </section>
  )
}
