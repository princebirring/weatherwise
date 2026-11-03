// Stroke icons, drawn in the current text colour. Decorative unless a label is given.
const PATHS = {
  pin: <><path d="M12 21s-7-6.2-7-11.5A7 7 0 0 1 19 9.5C19 14.8 12 21 12 21z" /><circle cx="12" cy="9.5" r="2.5" /></>,
  search: <><circle cx="11" cy="11" r="7" /><path d="M20 20l-3.5-3.5" /></>,
  locate: <><circle cx="12" cy="12" r="3" /><path d="M12 2v3M12 19v3M2 12h3M19 12h3" /></>,
  sun: <><circle cx="12" cy="12" r="4" /><path d="M12 2v2M12 20v2M2 12h2M20 12h2M5 5l1.5 1.5M17.5 17.5L19 19M5 19l1.5-1.5M17.5 6.5L19 5" /></>,
  heat: <><path d="M12 3v11" /><circle cx="12" cy="17.5" r="3.5" /><path d="M15 6h3M15 10h3" /></>,
  drop: <><path d="M12 3c3 4.5 6 7.6 6 11a6 6 0 0 1-12 0c0-3.4 3-6.5 6-11z" /></>,
  rain: <><path d="M4 14.9A7 7 0 1 1 15.7 8h1.8a4.5 4.5 0 0 1 2.5 8.2" /><path d="M8 14v5M12 16v5M16 14v5" /></>,
  storm: <><path d="M6 16.3A7 7 0 1 1 15.7 8h1.8a4.5 4.5 0 0 1 .5 9" /><path d="M13 12l-3 5h4l-3 5" /></>,
  wind: <><path d="M12.8 19.6A2 2 0 1 0 14 16H2" /><path d="M17.5 8a2.5 2.5 0 1 1 2 4H2" /><path d="M9.8 4.4A2 2 0 1 1 11 8H2" /></>,
  dry: <><path d="M12 3c3 4.5 6 7.6 6 11a6 6 0 0 1-12 0c0-3.4 3-6.5 6-11z" /><path d="M4 4l16 16" /></>,
  waves: <><path d="M2 15c2 0 2-1.5 4-1.5S8 15 10 15s2-1.5 4-1.5 2 1.5 4 1.5 2-1.5 4-1.5" /><path d="M2 19c2 0 2-1.5 4-1.5S8 19 10 19s2-1.5 4-1.5 2 1.5 4 1.5 2-1.5 4-1.5" /><path d="M6 10V7l6-4 6 4v3" /></>,
  home: <><path d="M3 11l9-7 9 7" /><path d="M5 10v10h14V10" /><path d="M10 20v-5h4v5" /></>,
  chat: <><path d="M4 5h16v11H9l-5 4z" /></>,
  shield: <><path d="M12 3l8 4v5c0 5-3.5 8-8 9-4.5-1-8-4-8-9V7z" /></>,
  speaker: <><path d="M4 9v6h4l5 4V5L8 9z" /><path d="M16 9a4 4 0 0 1 0 6" /></>,
  send: <><path d="M5 12h14M13 6l6 6-6 6" /></>,
  phone: <><path d="M5 4h4l2 5-2.5 1.5a11 11 0 0 0 5 5L15 13l5 2v4a2 2 0 0 1-2 2A16 16 0 0 1 3 6a2 2 0 0 1 2-2z" /></>,
  check: <><path d="M5 12l5 5L20 7" /></>,
  clock: <><circle cx="12" cy="12" r="9" /><path d="M12 7v5l3 2" /></>,
  cow: <><path d="M4 8l2-3M20 8l-2-3" /><rect x="6" y="7" width="12" height="9" rx="4" /><path d="M9 20v-4M15 20v-4" /></>,
  alert: <><path d="M12 3l10 18H2z" /><path d="M12 10v5M12 18v.5" /></>,
  share: <><circle cx="18" cy="5" r="3" /><circle cx="6" cy="12" r="3" /><circle cx="18" cy="19" r="3" /><path d="M8.6 13.5l6.8 4M15.4 6.5l-6.8 4" /></>,
  back: <><path d="M15 5l-7 7 7 7" /></>,
  plant: <><path d="M12 21V10" /><path d="M12 13c-4 0-6-3-6-7 4 0 6 3 6 7z" /><path d="M12 10c0-4 2-6 6-6 0 4-2 6-6 6z" /></>,
  bag: <><path d="M5 8h14l-1 12H6z" /><path d="M9 8a3 3 0 0 1 6 0" /></>,
} as const

export type IconName = keyof typeof PATHS

export function Icon({ name, size = 22, label }: { name: IconName; size?: number; label?: string }) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"
      strokeLinecap="round" strokeLinejoin="round" {...(label ? { role: 'img', 'aria-label': label } : { 'aria-hidden': true })}>
      {PATHS[name]}
    </svg>
  )
}

export function Logo({ size = 32 }: { size?: number }) {
  return (
    <svg width={size} height={size} viewBox="0 0 34 34" aria-hidden="true">
      <rect width="34" height="34" rx="10" fill="#0B5F5A" />
      <path d="M9 20c2.5-6 13.5-6 16 0" stroke="#FFFFFF" strokeWidth="2.4" fill="none" strokeLinecap="round" />
      <circle cx="17" cy="12" r="3.2" fill="#F5C518" />
      <path d="M8 25h18" stroke="#FFFFFF" strokeWidth="2.4" strokeLinecap="round" />
    </svg>
  )
}
