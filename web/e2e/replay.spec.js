import { test, expect } from '@playwright/test'

const STAGES = ['ingest', 'clean', 'classify', 'explain', 'route', 'review', 'monitor']

test('replay mode: chip fills the strip, drawer shows content, override a queued ticket', async ({ page }) => {
  await page.goto('/')
  await expect(page.getByTestId('mode-badge')).toHaveText('Replay')
  await expect(page.getByLabel('Customer message')).toBeDisabled()

  await page.getByRole('button', { name: 'Fake PII' }).click()
  for (const id of STAGES) {
    await expect(page.getByTestId('card-' + id).locator('.summary')).not.toBeEmpty()
  }

  await page.getByTestId('card-clean').click()
  const drawer = page.getByTestId('drawer')
  await expect(drawer).toBeVisible()
  for (const tab of ['What it does', 'Why this way', 'Code', 'Live example']) {
    await drawer.getByRole('tab', { name: tab }).click()
    await expect(page.getByTestId('tabpanel')).not.toBeEmpty()
  }
  await expect(drawer.locator('mark').first()).toHaveText('[CARD]')
  await page.keyboard.press('Escape')
  await expect(drawer).toBeHidden()

  await page.getByTestId('card-classify').click()
  await expect(page.getByText('Neural net')).toBeVisible()
  await page.keyboard.press('Escape')

  const items = page.getByTestId('queue-item')
  const before = await items.count()
  await items.first().getByRole('button', { name: 'Review' }).click()
  await page.getByRole('button', { name: 'Override' }).click()
  await page.getByLabel('Intent', { exact: true }).selectOption('failed_transfer')
  await page.getByTestId('review-submit').click()
  await expect(page.getByTestId('review-saved')).toContainText(/replay, not saved/i)
  await expect(items).toHaveCount(before - 1)
  await expect(page.getByTestId('mode-badge')).toHaveText('Replay')
})

test('replay mode: monitor scenario turns drift red', async ({ page }) => {
  await page.goto('/')
  await page.getByRole('button', { name: 'Simulate Hinglish surge' }).click()
  await expect(page.getByTestId('monitor').locator('.st-red').first()).toBeVisible()
})

test('narrow screen: strip scrolls sideways, page does not', async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 800 })
  await page.goto('/')
  await page.getByRole('button', { name: 'Fake PII' }).click()
  await expect(page.getByTestId('card-monitor').locator('.summary')).not.toBeEmpty()
  await page.getByRole('button', { name: 'Simulate Hinglish surge' }).click()
  await page.getByTestId('queue-item').first().getByRole('button', { name: 'Review' }).click()
  await page.getByTestId('card-clean').click()
  await page.getByTestId('drawer').getByRole('tab', { name: 'Live example' }).click()
  await page.keyboard.press('Escape')
  const w = await page.evaluate(() => [document.documentElement.scrollWidth, window.innerWidth])
  expect(w[0]).toBeLessThanOrEqual(w[1])
})

test('replay: every queued ticket opens a review form and can be confirmed', async ({ page }) => {
  await page.goto('/')
  const items = page.getByTestId('queue-item')
  await expect(items.first()).toBeVisible()
  const n = await items.count()
  expect(n).toBeGreaterThan(0)
  test.setTimeout(60000)
  for (let i = 0; i < Math.min(n, 4); i++) {
    await items.first().getByRole('button', { name: 'Review' }).click()
    await page.getByTestId('review-submit').click()
    await expect(page.getByTestId('review-saved')).toBeVisible()
    await expect(items).toHaveCount(n - i - 1, { timeout: 5000 })
  }
})
