import { useEffect, useState } from 'react'
import { useLanguage } from '../text'
import { Icon } from './Icon'

// Reads a card aloud with the phone's own voice (Web Speech API): free, no AWS service, and on
// most Android phones it has Marathi, which Amazon Polly does not. No voice for the language on
// this phone: no button, rather than reading Marathi with an English voice.

const synth = (): SpeechSynthesis | null =>
  typeof window !== 'undefined' && 'speechSynthesis' in window && typeof SpeechSynthesisUtterance !== 'undefined'
    ? window.speechSynthesis : null

const tagOf = (v: SpeechSynthesisVoice) => v.lang.toLowerCase().replace('_', '-')

/** The phone's best voice for a language code ("mr", "hi", "en"): Indian first, then any. */
function voiceFor(voices: SpeechSynthesisVoice[], lang: string): SpeechSynthesisVoice | null {
  const code = lang.toLowerCase()
  return voices.find((v) => tagOf(v) === `${code}-in`)
    ?? voices.find((v) => tagOf(v) === code || tagOf(v).startsWith(`${code}-`)) ?? null
}

function useVoice(lang: string) {
  const [voices, setVoices] = useState<SpeechSynthesisVoice[]>(() => synth()?.getVoices() ?? [])
  useEffect(() => {
    const s = synth()
    if (!s) return
    // Voices load after the page on most browsers.
    const update = () => setVoices(s.getVoices())
    s.addEventListener('voiceschanged', update)
    update()
    return () => s.removeEventListener('voiceschanged', update)
  }, [])
  return voiceFor(voices, lang)
}

/** "Listen" button for one card. `lang` is the language the text is written in.
 *  `round`: a small speaker button beside a heading, for screens that should stay quiet. */
export function Listen({ text, lang, round = false }: { text: string; lang?: string; round?: boolean }) {
  const { t, language } = useLanguage()
  const voice = useVoice(lang ?? language)
  // Which text is being read: a new card is never shown as "speaking".
  const [reading, setReading] = useState<string | null>(null)
  const speaking = reading === text

  // A new card, or leaving the screen, stops the reading.
  useEffect(() => () => { synth()?.cancel() }, [text])

  if (!voice) return null
  const s = synth()!
  const toggle = () => {
    s.cancel()
    if (speaking) { setReading(null); return }
    const u = new SpeechSynthesisUtterance(text)
    u.voice = voice
    u.lang = voice.lang
    u.rate = 0.9 // a little slower than normal, for clarity outdoors
    u.onend = u.onerror = () => setReading(null)
    s.speak(u)
    setReading(text)
  }
  if (round) {
    return (
      <button type="button" className="listen-round" onClick={toggle} aria-pressed={speaking}
        aria-label={speaking ? t('listen.stop') : t('listen.play')}>
        <Icon name="speaker" size={24} />
      </button>
    )
  }
  return (
    <button type="button" className="btn big secondary listen" onClick={toggle} aria-pressed={speaking}>
      <Icon name="speaker" size={26} />{speaking ? t('listen.stop') : t('listen.play')}
    </button>
  )
}
