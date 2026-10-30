import { expect, test } from '@playwright/test'

test.beforeEach(async ({ request }) => {
  const cleared = await request.delete('/api/data', {
    headers: { 'X-Dayloom-Confirm': 'DELETE MY DATA' },
  })
  expect(cleared.status()).toBe(204)
})

test('create, edit and complete a task', async ({ page }) => {
  await page.goto('/tasks?new=1')
  await page.getByLabel('Task title').fill('Write the first draft')
  await page.getByLabel('Estimate (minutes)').fill('45')
  await page.getByRole('button', { name: 'Create task', exact: true }).click()
  await expect(
    page.getByRole('button', { name: 'Write the first draft', exact: true }),
  ).toBeVisible()
  await page.getByRole('button', { name: 'Edit Write the first draft', exact: true }).click()
  await page.getByLabel('Task title').fill('Review the first draft')
  await page.getByRole('button', { name: 'Save changes', exact: true }).click()
  await page.getByRole('button', { name: 'Complete Review the first draft', exact: true }).click()
  await page.getByRole('tab', { name: 'Completed', exact: true }).click()
  await expect(
    page.getByRole('button', { name: 'Review the first draft', exact: true }),
  ).toBeVisible()
})

test('assistant proposal requires approval and executes in the worker', async ({
  page,
  request,
}) => {
  await page.goto('/inbox')
  await page.getByLabel('Message Dayloom').fill("Prepare tomorrow's reading list")
  await page.getByRole('button', { name: 'Send message', exact: true }).click()
  await expect(page.getByText('Awaiting your approval')).toBeVisible()
  expect(await (await request.get('/api/tasks')).json()).toEqual([])
  await page.getByRole('button', { name: 'Revise action', exact: true }).click()
  await page.getByLabel('Task title').fill('Prepare a focused reading list')
  await page.getByRole('button', { name: 'Save revision', exact: true }).click()
  await page.getByRole('button', { name: 'Approve', exact: true }).click()
  await expect
    .poll(async () => (await (await request.get('/api/actions')).json())[0].status)
    .toBe('succeeded')
  await page.goto('/tasks')
  await expect(
    page.getByRole('button', { name: 'Prepare a focused reading list', exact: true }),
  ).toBeVisible()
})

test('memory editing and explicit deletion', async ({ page }) => {
  await page.goto('/memories')
  await page.getByRole('button', { name: 'New memory', exact: true }).click()
  await page.getByLabel('Memory', { exact: true }).fill('I prefer morning writing.')
  await page.getByRole('button', { name: 'Save memory', exact: true }).click()
  await expect(page.getByText('I prefer morning writing.', { exact: true })).toBeVisible()
  await page.getByRole('button', { name: 'Edit memory', exact: true }).click()
  await page.getByLabel('Memory', { exact: true }).fill('I prefer afternoon writing.')
  await page.getByRole('button', { name: 'Save memory', exact: true }).click()
  await expect(page.getByText('I prefer afternoon writing.', { exact: true })).toBeVisible()
  await page.getByRole('button', { name: 'Delete memory', exact: true }).click()
  await page.getByRole('button', { name: 'Delete', exact: true }).click()
  await expect(page.getByText('I prefer afternoon writing.', { exact: true })).toHaveCount(0)
})

test('all views fit their viewport and images load', async ({ page, request }, testInfo) => {
  await request.post('/api/demo')
  for (const route of ['today', 'inbox', 'tasks', 'memories', 'activity', 'settings']) {
    await page.goto(`/${route}`)
    await expect(page.getByRole('heading', { level: 1 })).toBeVisible()
    await expect
      .poll(() => page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth))
      .toBe(true)
    await expect
      .poll(() =>
        page
          .locator('img')
          .evaluateAll((images) =>
            images.every((image) => image.complete && image.naturalWidth > 0),
          ),
      )
      .toBe(true)
    await page.screenshot({ path: testInfo.outputPath(`${route}.png`), fullPage: true })
  }
})

test('mobile navigation opens and closes', async ({ page, isMobile }) => {
  test.skip(!isMobile, 'Mobile-only navigation')
  await page.goto('/today')
  await page.getByRole('button', { name: 'Open navigation', exact: true }).click()
  await page.getByRole('link', { name: 'Memories', exact: true }).click()
  await expect(page).toHaveURL(/\/memories$/)
  await expect(page.getByRole('button', { name: 'Close navigation' })).toHaveCount(0)
})
