// Node 25+ ships its own (empty) localStorage global, which hides jsdom's. Give the tests a
// plain in-memory Storage so saved language, place and flood progress behave as in a browser.
class MemoryStorage implements Storage {
  private items = new Map<string, string>()
  get length() { return this.items.size }
  clear() { this.items.clear() }
  getItem(key: string) { return this.items.get(key) ?? null }
  key(i: number) { return [...this.items.keys()][i] ?? null }
  removeItem(key: string) { this.items.delete(key) }
  setItem(key: string, value: string) { this.items.set(key, String(value)) }
}

Object.defineProperty(globalThis, 'localStorage', { value: new MemoryStorage(), configurable: true })
