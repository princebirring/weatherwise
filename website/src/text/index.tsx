import { createContext, useContext, type ReactNode } from 'react'
import type { Guidance, Language, Policy } from '../types'
import { en, type TextKey } from './en'
import { hi } from './hi'
import { mr } from './mr'

const TEXT: Record<Language, Record<TextKey, string>> = { en, hi, mr }

// Names shown on the language buttons, each in its own script.
export const LANGUAGE_NAMES: Record<Language, string> = { mr: 'मराठी', hi: 'हिंदी', en: 'English' }
export const LANGUAGES: Language[] = ['mr', 'hi', 'en']

export function textFor(language: Language) {
  return (key: TextKey, value?: string | number) => {
    const s = TEXT[language][key]
    return value === undefined ? s : s.replaceAll('{name}', String(value))
  }
}

export type T = ReturnType<typeof textFor>

interface LanguageState {
  language: Language
  setLanguage: (l: Language) => void
  t: T
  policy: Policy | null
}

const LanguageContext = createContext<LanguageState | null>(null)

export function LanguageProvider(props: LanguageState & { children: ReactNode }) {
  const { children, ...value } = props
  return <LanguageContext.Provider value={value}>{children}</LanguageContext.Provider>
}

export function useLanguage(): LanguageState {
  const state = useContext(LanguageContext)
  if (!state) throw new Error('useLanguage outside LanguageProvider')
  return state
}

/** Safety advice for the chosen language (English where not yet verified), from message_policy. */
export function useGuidance(): Guidance | null {
  const { policy, language } = useLanguage()
  return policy ? (policy.guidance[language] ?? policy.guidance.en) : null
}
