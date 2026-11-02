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
  for (const route of ['today', 'inbox', 'tasks', 'memories', 'activity', 'settings', 'guide']) {
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

test('Simplified Chinese persists without rewriting workspace content', async ({
  page,
  request,
}) => {
  await request.post('/api/tasks', {
    data: { title: 'Keep my original task 原始任务', minutes: 30, priority: 'normal' },
  })
  await page.goto('/settings')
  await page.getByLabel('Language', { exact: true }).selectOption('zh-CN')
  await expect(page.locator('html')).toHaveAttribute('lang', 'zh-CN')
  await expect(page.getByRole('heading', { name: '按你的习惯设置', exact: true })).toBeVisible()
  await page.reload()
  await expect(page.getByLabel('语言', { exact: true })).toHaveValue('zh-CN')
  await page.goto('/tasks')
  await expect(page.getByRole('heading', { name: '给重要的事留出空间', exact: true })).toBeVisible()
  await expect(
    page.getByRole('button', { name: 'Keep my original task 原始任务', exact: true }),
  ).toBeVisible()
  await page.goto('/settings')
  await page.getByLabel('语言', { exact: true }).selectOption('en')
  await expect(page.locator('html')).toHaveAttribute('lang', 'en')
  await expect(page.getByRole('heading', { name: 'On your terms.', exact: true })).toBeVisible()
})

test('guided setup requires consent, retries testing and reviews a real local proposal', async ({
  page,
  request,
}) => {
  await request.delete('/api/models')
  let connectionTests = 0
  let conversations = 0
  await page.route('**/api/settings', async (route) => {
    const response = await route.fetch()
    const settings = await response.json()
    if (settings.provider.managed === 'server')
      settings.provider = {
        ...settings.provider,
        name: 'UnconfiguredProvider',
        external: true,
        configured: false,
      }
    await route.fulfill({ json: settings })
  })
  await page.route('**/api/models/test', async (route) => {
    connectionTests += 1
    await route.fulfill(
      connectionTests === 1
        ? {
            status: 502,
            json: { detail: 'Provider connection or structured-response test failed' },
          }
        : {
            json: {
              connected: true,
              model: 'guide-test-model',
              message: 'Test fixture connected',
              proposals_executed: 0,
            },
          },
    )
  })
  await page.route('**/api/chat', async (route) => {
    conversations += 1
    expect(route.request().postDataJSON().allow_external).toBe(true)
    const proposed = await request.post('/api/actions', {
      data: {
        tool: 'CreateTask',
        payload: { title: 'Guided test task', minutes: 30, priority: 'normal' },
      },
    })
    expect(proposed.status()).toBe(201)
    await route.fulfill({
      json: {
        message: {
          id: 'guide-fixture',
          role: 'assistant',
          content: '请核对任务后再批准。',
          provider: 'test-fixture',
          created_at: new Date().toISOString(),
        },
        actions: [await proposed.json()],
      },
    })
  })
  try {
    await page.goto('/today')
    await expect(page).toHaveURL(/\/guide$/)
    await page.getByLabel('Language', { exact: true }).selectOption('zh-CN')
    await page.getByRole('button', { name: '稍后继续', exact: true }).click()
    await expect(page).toHaveURL(/\/today$/)
    await page.reload()
    await expect(page.getByRole('link', { name: '继续设置', exact: true })).toBeVisible()
    await page.getByRole('link', { name: '继续设置', exact: true }).click()
    await page.getByRole('button', { name: '开始配置模型', exact: true }).click()
    await expect(page.getByRole('heading', { name: '连接 API', exact: true })).toBeFocused()
    await page.getByLabel('API 服务商', { exact: true }).selectOption('https://api.deepseek.com/v1')
    await expect(page.getByLabel('模型名称', { exact: true })).toHaveValue('deepseek-chat')
    await page.getByLabel('API 密钥', { exact: true }).fill('discard-this-synthetic-key')
    await page.getByLabel('API 服务商', { exact: true }).selectOption('https://api.openai.com/v1')
    await expect(page.getByLabel('API 密钥', { exact: true })).toHaveValue('')
    await page.getByLabel('API 基础地址', { exact: true }).fill('https://api.openai.com/v1')
    await page.getByLabel('模型名称', { exact: true }).fill('guide-test-model')
    await page
      .getByLabel('API 密钥', { exact: true })
      .fill('synthetic-guide-key-not-a-real-credential')
    await page.getByRole('button', { name: '保存连接', exact: true }).click()
    await expect(page.getByRole('heading', { name: '测试连接', exact: true })).toBeVisible()
    const testButton = page.getByRole('button', { name: '测试连接', exact: true })
    await expect(testButton).toBeDisabled()
    expect(connectionTests).toBe(0)
    const savedProgress = await page.evaluate(() => JSON.stringify(localStorage))
    expect(savedProgress).not.toContain('synthetic-guide-key')
    await page.getByRole('checkbox').check()
    await testButton.click()
    await expect(page.locator('.guide-error')).toContainText('连接或格式测试失败')
    await expect(page.getByRole('button', { name: '尝试第一次对话', exact: true })).toHaveCount(0)
    await testButton.click()
    await expect(page.getByText('连接测试成功，模型已就绪。', { exact: true })).toBeVisible()
    await page.getByRole('button', { name: '尝试第一次对话', exact: true }).click()
    await page.reload()
    await expect(page.getByRole('heading', { name: '测试连接', exact: true })).toBeVisible()
    expect(connectionTests).toBe(2)
    await page.getByRole('checkbox').check()
    await testButton.click()
    await expect(page.getByRole('heading', { name: '首次对话', exact: true })).toBeVisible()
    const sendButton = page.getByRole('button', { name: '发送第一条消息', exact: true })
    await expect(sendButton).toBeDisabled()
    expect(conversations).toBe(0)
    await page.getByRole('checkbox').check()
    await sendButton.click()
    await expect(page.getByText('Guided test task', { exact: true })).toBeVisible()
    expect(await (await request.get('/api/tasks')).json()).toEqual([])
    await page.getByRole('button', { name: '批准执行', exact: true }).click()
    await expect.poll(async () => (await (await request.get('/api/tasks')).json()).length).toBe(1)
    await page.getByRole('button', { name: '进入我的工作区', exact: true }).click()
    await expect(page).toHaveURL(/\/today$/)
    expect(connectionTests).toBe(3)
    expect(conversations).toBe(1)
    expect(JSON.stringify(await (await request.get('/api/models')).json())).not.toContain(
      'synthetic-guide-key',
    )
  } finally {
    await request.delete('/api/models')
  }
})
