import { test, expect } from '@playwright/test'

/** Navigate through portal -> form -> chat with API mocks. */
async function goToChat(page: import('@playwright/test').Page) {
  await page.route('**/api/sessions*', (route) =>
    route.fulfill({ status: 200, contentType: 'application/json', body: '[]' }),
  )
  await page.route('**/api/session/**', (route) => {
    if (route.request().method() === 'GET') {
      return route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: '{"messages":[]}',
      })
    }
    return route.fulfill({ status: 200, contentType: 'application/json', body: '{}' })
  })
  await page.route('**/api/profile/**', (route) =>
    route.fulfill({ status: 200, contentType: 'application/json', body: '{}' }),
  )

  await page.goto('/')

  // Click first scenario card (gaokao)
  await page.getByRole('listitem').first().click()
  await expect(page.getByRole('form')).toBeVisible({ timeout: 10_000 })

  // Skip the profile form — button text: "跳过，直接提问 →"
  await page.getByText('跳过，直接提问').click()

  // Wait for the chat view to appear (aria-label defaultValue: '聊天区域')
  await expect(page.getByLabel('聊天区域')).toBeVisible({ timeout: 10_000 })
}

test.describe('Chat Interface', () => {
  test.beforeEach(async ({ page }) => {
    await goToChat(page)
  })

  test('shows empty state with welcome message', async ({ page }) => {
    await expect(page.getByText('你好！我是张雪峰 AI 助手')).toBeVisible()
  })

  test('send button is disabled when input is empty', async ({ page }) => {
    const sendButton = page.getByRole('button', { name: '发送' })
    await expect(sendButton).toBeDisabled()
  })

  test('typing enables the send button', async ({ page }) => {
    const input = page.locator('#chat-input')
    await input.fill('你好')
    const sendButton = page.getByRole('button', { name: '发送' })
    await expect(sendButton).toBeEnabled()
  })

  test('sends a message and receives a streamed reply', async ({ page }) => {
    await page.route('**/api/chat', async (route) => {
      const sseBody = [
        'data: {"type":"text","content":"你好！"}\n\n',
        'data: {"type":"text","content":"我是张雪峰。"}\n\n',
      ].join('')

      return route.fulfill({
        status: 200,
        headers: {
          'Content-Type': 'text/event-stream',
          'Cache-Control': 'no-cache',
        },
        body: sseBody,
      })
    })

    const input = page.locator('#chat-input')
    await input.fill('你好，我想咨询高考志愿')
    await page.getByRole('button', { name: '发送' }).click()

    // User message should appear
    await expect(page.getByText('你好，我想咨询高考志愿')).toBeVisible()

    // Assistant reply should appear (SSE streamed)
    await expect(page.getByText('你好！我是张雪峰。')).toBeVisible()
  })

  test('shows error message when API fails', async ({ page }) => {
    await page.route('**/api/chat', (route) =>
      route.fulfill({ status: 500, contentType: 'application/json', body: '{"detail":"error"}' }),
    )

    const input = page.locator('#chat-input')
    await input.fill('测试消息')
    await page.getByRole('button', { name: '发送' }).click()

    // Error message: "抱歉，发生了错误，请重试。"
    await expect(page.getByText('抱歉')).toBeVisible()
  })

  test('Enter key sends message', async ({ page }) => {
    await page.route('**/api/chat', async (route) => {
      return route.fulfill({
        status: 200,
        headers: { 'Content-Type': 'text/event-stream' },
        body: 'data: {"type":"text","content":"收到！"}\n\n',
      })
    })

    const input = page.locator('#chat-input')
    await input.fill('回车发送测试')
    await input.press('Enter')

    await expect(page.getByText('回车发送测试')).toBeVisible()
    await expect(page.getByText('收到！')).toBeVisible()
  })

  test('input is disabled while loading', async ({ page }) => {
    await page.route('**/api/chat', async (route) => {
      await new Promise((r) => setTimeout(r, 2000))
      return route.fulfill({
        status: 200,
        headers: { 'Content-Type': 'text/event-stream' },
        body: 'data: {"type":"text","content":"延迟回复"}\n\n',
      })
    })

    const input = page.locator('#chat-input')
    await input.fill('测试加载状态')
    await page.getByRole('button', { name: '发送' }).click()

    // Input should be disabled during loading
    await expect(input).toBeDisabled()

    // After response, input should be re-enabled
    await expect(input).toBeEnabled({ timeout: 10_000 })
  })
})
