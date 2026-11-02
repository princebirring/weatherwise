// A small path router: the site has a handful of fixed screens, so no library is needed.
import { createContext, useContext, useEffect, useState, type AnchorHTMLAttributes, type MouseEvent } from 'react'

const listeners = new Set<() => void>()

/** The app shown inside the landing page's phone keeps its own path, so its links and tabs move
 *  the phone, never the page around it. */
interface Embedded { path: string; go: (path: string) => void }
const EmbeddedContext = createContext<Embedded | null>(null)
export const EmbeddedRouter = EmbeddedContext.Provider

/** Go to a screen. `replace` swaps the current history entry (old links, so Back does not loop). */
export function navigate(path: string, { replace = false } = {}): void {
  const [target, hash] = path.split('#')
  const here = window.location.pathname + window.location.search
  if (target !== here || replace) {
    if (replace) window.history.replaceState(null, '', path)
    else window.history.pushState(null, '', path)
    window.scrollTo(0, 0)
    listeners.forEach((l) => l())
  } else if (hash) {
    window.history.pushState(null, '', path)
  } else {
    return
  }
  // "/#team": scroll to that section once the new page has drawn.
  if (hash) requestAnimationFrame(() => document.getElementById(hash)?.scrollIntoView({ behavior: 'smooth' }))
}

export function usePath(): string {
  const embedded = useContext(EmbeddedContext)
  const [path, setPath] = useState(window.location.pathname)
  useEffect(() => {
    const update = () => setPath(window.location.pathname)
    listeners.add(update)
    window.addEventListener('popstate', update)
    return () => {
      listeners.delete(update)
      window.removeEventListener('popstate', update)
    }
  }, [])
  return embedded?.path ?? path
}

export function Link({ href, onClick, ...rest }: AnchorHTMLAttributes<HTMLAnchorElement> & { href: string }) {
  const embedded = useContext(EmbeddedContext)
  const handle = (e: MouseEvent<HTMLAnchorElement>) => {
    onClick?.(e)
    if (e.defaultPrevented || e.metaKey || e.ctrlKey || e.shiftKey || e.button !== 0) return
    if (!href.startsWith('/')) return
    e.preventDefault()
    if (embedded) embedded.go(href)
    else navigate(href)
  }
  return <a href={href} onClick={handle} {...rest} />
}
