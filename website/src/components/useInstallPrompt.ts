import { useEffect, useState } from 'react'

// "Add to home screen": Android browsers offer it through beforeinstallprompt. Where they do not
// (iPhone, or already added), this returns null and no button is shown, rather than a dead button.

interface InstallEvent extends Event {
  prompt: () => Promise<void>
  userChoice: Promise<{ outcome: 'accepted' | 'dismissed' }>
}

export interface InstallPrompt {
  prompt: () => Promise<void>
}

export function useInstallPrompt(): InstallPrompt | null {
  const [event, setEvent] = useState<InstallEvent | null>(null)
  useEffect(() => {
    const offer = (e: Event) => { e.preventDefault(); setEvent(e as InstallEvent) }
    const installed = () => setEvent(null)
    window.addEventListener('beforeinstallprompt', offer)
    window.addEventListener('appinstalled', installed)
    return () => {
      window.removeEventListener('beforeinstallprompt', offer)
      window.removeEventListener('appinstalled', installed)
    }
  }, [])
  if (!event) return null
  return {
    prompt: async () => {
      await event.prompt()
      await event.userChoice.catch(() => null)
      setEvent(null) // the browser offers it once per event
    },
  }
}
