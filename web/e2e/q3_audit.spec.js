import { test, expect } from '@playwright/test'
import path from 'node:path'

// Q3 audit checks. Live ones need SANKET_LIVE_API (see playwright.config.js); replay ones need no API.
const SCREENS = path.resolve(process.cwd(), '..', 'docs', 'screens')

test('@live script and HTML in a ticket render as text, never run', async ({ page }) => {
  await page.goto('/')
  await expect(page.getByTestId('mode-badge')).toHaveText('Live')
  const evil = '<img src=x onerror="window.__xss=1"> my card is lost <script>window.__xss=2</script>'
  await page.getByLabel('Customer message').fill(evil)
  await page.getByRole('button', { name: 'Submit' }).click()
  await expect(page.getByText('<script>window.__xss=2</script>', { exact: false }).first()).toBeVisible()
  expect(await page.evaluate(() => window.__xss)).toBeUndefined()
})

test('@live screenshot of a live result', async ({ page }) => {
  await page.setViewportSize({ width: 1400, height: 900 })
  await page.goto('/')
  await expect(page.getByTestId('mode-badge')).toHaveText('Live')
  await page.getByRole('button', { name: 'Urgent fraud' }).click()
  await expect(page.getByTestId('card-route').locator('.summary')).not.toBeEmpty()
  await page.waitForTimeout(1200)
  await page.screenshot({ path: path.join(SCREENS, 'live.png'), fullPage: true })
})

// Known finding (Q3 MED): once the page is Live it never re-checks health, so the badge keeps
// saying Live after the API dies. test.fail() flips to a pass-required test once it is fixed.
test('@live API dies mid-session: badge must leave Live', async ({ page }) => {
  test.setTimeout(40000)
  await page.goto('/')
  await expect(page.getByTestId('mode-badge')).toHaveText('Live')
  await page.route('**/api/**', (route) => route.abort('connectionrefused'))
  await page.getByLabel('Customer message').fill('my card was stolen')
  await page.getByRole('button', { name: 'Submit' }).click()
  await expect(page.getByTestId('mode-badge')).toHaveText('Replay', { timeout: 20000 })
})

test('replay: drawer Code tab shows the functions that really run', async ({ page }) => {
  await page.goto('/')
  await expect(page.getByTestId('mode-badge')).toHaveText('Replay')
  const expected = { clean: 'def clean(', route: 'def decide(', classify: 'def predict_proba(' }
  for (const [id, sig] of Object.entries(expected)) {
    await page.getByTestId('card-' + id).click()
    await page.getByTestId('drawer').getByRole('tab', { name: 'Code' }).click()
    await expect(page.getByTestId('tabpanel')).toContainText(sig)
    await page.keyboard.press('Escape')
  }
})

test('replay: screenshot with the API stopped', async ({ page }) => {
  await page.setViewportSize({ width: 1400, height: 900 })
  await page.goto('/')
  await expect(page.getByTestId('mode-badge')).toHaveText('Replay')
  await page.getByRole('button', { name: 'Fake PII' }).click()
  await expect(page.getByTestId('card-route').locator('.summary')).not.toBeEmpty()
  await page.waitForTimeout(1200)
  await page.screenshot({ path: path.join(SCREENS, 'replay.png'), fullPage: true })
})
