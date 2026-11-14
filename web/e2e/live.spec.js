import { test, expect } from '@playwright/test'

// Run with the API up: SANKET_LIVE_API=http://localhost:8000 npm run test:live
test('@live free text goes through the real API', async ({ page }) => {
  await page.goto('/')
  await expect(page.getByTestId('mode-badge')).toHaveText('Live')
  await page.getByLabel('Customer message').fill('My card was stolen yesterday, please block it')
  await page.getByRole('button', { name: 'Submit' }).click()
  for (const id of ['ingest', 'clean', 'classify', 'explain', 'route']) {
    await expect(page.getByTestId('card-' + id).locator('.summary')).not.toBeEmpty()
  }
  await page.getByTestId('card-route').click()
  await page.getByRole('tab', { name: 'Live example' }).click()
  await expect(page.getByTestId('tabpanel')).toContainText('Thresholds')
})

test('@live empty text is refused inline', async ({ page }) => {
  await page.goto('/')
  await page.getByLabel('Customer message').fill('1234 5678')
  await page.getByRole('button', { name: 'Submit' }).click()
  await expect(page.getByRole('alert')).toBeVisible()
})
