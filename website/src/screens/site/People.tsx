import { useLanguage } from '../../text'
import type { Member } from './team'

/** One person: photo (or initials), role, and links. `short` leaves the bio for the About page. */
export function Person({ m, short = false }: { m: Member; short?: boolean }) {
  const { t } = useLanguage()
  return (
    <article className={`person ${short ? 'short' : ''}`}>
      {m.photo
        ? <img className="person-photo" src={m.photo} width={112} height={112} alt={m.name} />
        : <span className="person-photo initials" aria-hidden="true">{m.initials}</span>}
      <div>
        <h3>{m.name}</h3>
        <p className="person-role">{t(m.role)}</p>
        {!short && <p>{t(m.bio)}</p>}
        <p className="person-links">
          {(short ? m.links.slice(0, 1) : m.links).map((l) => <a key={l.href} href={l.href} target="_blank" rel="noreferrer" lang="en">{l.label} ↗</a>)}
        </p>
      </div>
    </article>
  )
}
