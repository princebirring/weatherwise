import { dayIcon, dayLevel, dryDays, weekday } from '../hazards'
import { useLanguage } from '../text'
import type { Outlook } from '../types'
import { Icon } from './Icon'

// Rain worth showing on the week strip: a whole millimetre or more (a display choice, not a warning line).
const wet = (mm: number | null) => mm !== null && Math.round(mm) >= 1

/** The 7-day strip, coloured by warning level, with the days that are good for spraying. */
export function Week({ outlook }: { outlook: Outlook }) {
  const { t, language } = useLanguage()
  const dry = dryDays(outlook.days)
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
              {wet(d.rain_mm) && <span className="rain">{t('today.rainMm', Math.round(d.rain_mm as number))}</span>}
            </li>
          )
        })}
      </ol>
      {dry && (
        <p className="spray">
          <Icon name="plant" size={24} />
          <span>
            {dry.length ? t('week.sprayDays', dry.map((d) => weekday(d.day, language)).join(', ')) : t('week.sprayNone')}
            {' '}<span className="small">{t('week.sprayWhy')}</span>
          </span>
        </p>
      )}
    </section>
  )
}
