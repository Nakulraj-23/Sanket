import { defineConfig } from '@playwright/test'
import fs from 'node:fs'

// Use PLAYWRIGHT_CHROMIUM_PATH if set, else any chrome in PLAYWRIGHT_BROWSERS_PATH, else Playwright default.
let executablePath = process.env.PLAYWRIGHT_CHROMIUM_PATH
if (!executablePath && process.env.PLAYWRIGHT_BROWSERS_PATH) {
  const root = process.env.PLAYWRIGHT_BROWSERS_PATH
  const dir = fs.existsSync(root) && fs.readdirSync(root).find((d) => /^chromium-\d+$/.test(d))
  if (dir) executablePath = `${root}/${dir}/chrome-linux64/chrome`
}

const live = !!process.env.SANKET_LIVE_API
export default defineConfig({
  testDir: './e2e',
  // Replay specs run against a dev server with no API. @live specs run only with SANKET_LIVE_API=http://localhost:8000.
  webServer: live
    ? { command: `VITE_API_URL=${process.env.SANKET_LIVE_API} npx vite --port 5173`, url: 'http://localhost:5173', reuseExistingServer: true }
    : { command: 'npx vite --port 5173', url: 'http://localhost:5173', reuseExistingServer: true },
  use: { baseURL: live ? 'http://localhost:5173' : 'http://localhost:5173', launchOptions: { executablePath, args: ['--no-sandbox'] } },
})
