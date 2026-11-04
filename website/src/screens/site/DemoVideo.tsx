import { useEffect, useRef, useState } from 'react'
import { Icon } from '../../components/Icon'
import { useLanguage } from '../../text'
import { DEMO_VIDEO, DEMO_YOUTUBE } from './team'

/** "Watch the 3-minute demo": plays our own copy in place, so a judge stays on the site.
 *  Unknown paths get the page back, not a 404, so the file counts only if it answers as video.
 *  Without it, the link goes to YouTube; with neither, nothing shows. */
export function DemoVideo() {
  const { t } = useLanguage()
  const [hasFile, setHasFile] = useState(false)
  const dialog = useRef<HTMLDialogElement>(null)
  const video = useRef<HTMLVideoElement>(null)

  useEffect(() => {
    let live = true
    fetch(DEMO_VIDEO, { method: 'HEAD' })
      .then((r) => live && setHasFile(r.ok && (r.headers.get('content-type') ?? '').startsWith('video/')))
      .catch(() => {})
    return () => { live = false }
  }, [])

  if (!hasFile) {
    return DEMO_YOUTUBE
      ? <a href={DEMO_YOUTUBE} target="_blank" rel="noreferrer" className="ap-link"><Icon name="play" size={18} /> {t('site.watchDemo')}</a>
      : null
  }
  const open = () => {
    dialog.current?.showModal()
    Promise.resolve(video.current?.play()).catch(() => {}) // a browser may block autoplay: the controls are there
  }
  return (
    <>
      <button type="button" className="ap-link ap-demo-open" onClick={open}><Icon name="play" size={18} /> {t('site.watchDemo')}</button>
      <dialog ref={dialog} className="ap-demo" aria-label={t('site.watchDemo')} onClose={() => video.current?.pause()}
        onClick={(e) => { if (e.target === dialog.current) dialog.current.close() }}>
        <video ref={video} src={DEMO_VIDEO} controls playsInline preload="none" />
        <div className="ap-demo-bar">
          {DEMO_YOUTUBE && <a href={DEMO_YOUTUBE} target="_blank" rel="noreferrer" className="ap-link">{t('site.demoYoutube')}</a>}
          <button type="button" className="btn" onClick={() => dialog.current?.close()}>{t('site.demoClose')}</button>
        </div>
      </dialog>
    </>
  )
}
