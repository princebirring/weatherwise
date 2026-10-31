import { defineConfig } from 'vitest/config'

export default defineConfig({
  esbuild: { jsx: 'automatic' },
  test: { environment: 'jsdom', environmentOptions: { jsdom: { url: 'http://localhost/' } }, include: ['src/tests/**/*.test.{ts,tsx}'], setupFiles: ['src/tests/setup.ts'] },
})
