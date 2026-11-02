// Keeps WeatherWise usable with no signal: the app itself, and the last answers for the saved
// place (forecast, official warnings, safe places, safety advice). Online, everything comes
// fresh from the server first; the saved copy is used only when the network fails.
// What is saved stays on this phone, like the place itself (see src/storage.ts).
const CACHE = 'weatherwise-v1'
const SAVED_API = ['/api/place', '/api/official', '/api/shelters', '/api/policy', '/api/status']

self.addEventListener('install', () => self.skipWaiting())

self.addEventListener('activate', (event) => {
  event.waitUntil((async () => {
    for (const key of await caches.keys()) if (key !== CACHE) await caches.delete(key)
    await self.clients.claim()
  })())
})

async function freshFirst(request, cacheKey) {
  const cache = await caches.open(CACHE)
  try {
    const response = await fetch(request)
    if (response.ok) await cache.put(cacheKey ?? request, response.clone())
    return response
  } catch (error) {
    const saved = await cache.match(cacheKey ?? request)
    if (saved) return saved
    throw error
  }
}

async function savedFirst(request) {
  const cache = await caches.open(CACHE)
  const saved = await cache.match(request)
  if (saved) return saved
  const response = await fetch(request)
  if (response.ok) await cache.put(request, response.clone())
  return response
}

self.addEventListener('fetch', (event) => {
  const request = event.request
  const url = new URL(request.url)
  if (request.method !== 'GET' || url.origin !== self.location.origin) return
  if (request.mode === 'navigate' && url.pathname.startsWith('/app')) {
    // Every app screen is the same page: keep one copy of it.
    event.respondWith(freshFirst(request, '/app'))
  } else if (url.pathname.startsWith('/assets/')) {
    event.respondWith(savedFirst(request)) // hashed names: a file never changes
  } else if (SAVED_API.includes(url.pathname)) {
    event.respondWith(freshFirst(request))
  }
})
