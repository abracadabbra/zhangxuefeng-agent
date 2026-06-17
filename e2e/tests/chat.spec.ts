import { expect, test } from './fixtures'

/** Navigate through portal -> form -> chat with API mocks. */
async function goToChat(page: import('@playwright/test').Page) {
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

  test('generates recommendations and syncs favorite state', async ({ page }) => {
    let favoritesPayload: unknown = null
    await page.route('**/api/recommend', (route) =>
      route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          session_id: 'e2e-session',
          summary: '建议按冲稳保组合填报。',
          gradient_summary: { 稳: ['北京邮电大学'] },
          recommendations: [
            {
              school_name: '北京邮电大学',
              reason: '计算机和通信学科强，符合职业方向。',
              admission_probability: 0.72,
              match_score: 0.88,
              strategy: '稳',
              risk_points: ['热门专业分数波动大'],
              alternatives: ['南京邮电大学'],
            },
          ],
        }),
      }),
    )
    await page.route('**/api/session/*/favorites', async (route) => {
      if (route.request().method() === 'PUT') {
        favoritesPayload = route.request().postDataJSON()
      }
      return route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({ favorite_keys: ['school:北京邮电大学'] }),
      })
    })

    await page.getByRole('button', { name: '生成志愿推荐' }).click()

    await expect(page.getByLabel('志愿推荐结果')).toBeVisible()
    await expect(page.getByRole('heading', { name: '北京邮电大学' })).toBeVisible()
    await page.getByRole('button', { name: '收藏 北京邮电大学' }).click()

    await expect.poll(() => favoritesPayload).toEqual({
      favorite_keys: ['school:北京邮电大学'],
    })
    await expect(page.getByRole('button', { name: '取消收藏 北京邮电大学' })).toBeVisible()
  })

  test('downloads Markdown and PDF recommendation reports', async ({ page }) => {
    await page.locator('#chat-input').fill('河南理科650分，想学计算机。')
    await page.getByRole('button', { name: '发送' }).click()
    await expect(page.getByText('河南理科650分，想学计算机。')).toBeVisible()

    const markdownDownloadPromise = page.waitForEvent('download')
    await page.getByRole('button', { name: '导出 Markdown 报告' }).click()
    const markdownDownload = await markdownDownloadPromise
    expect(markdownDownload.suggestedFilename()).toBe('chat-e2e.md')

    const pdfDownloadPromise = page.waitForEvent('download')
    await page.getByRole('button', { name: '导出 PDF 报告' }).click()
    const pdfDownload = await pdfDownloadPromise
    expect(pdfDownload.suggestedFilename()).toBe('chat-e2e.pdf')
  })

  test('shows RAG confidence metadata in the source panel', async ({ page }) => {
    await page.route('**/api/chat', (route) =>
      route.fulfill({
        status: 200,
        headers: { 'Content-Type': 'text/event-stream' },
        body: [
          'data: {"type":"tool_call","name":"semantic_search_schools","arguments":{"query":"计算机强校"}}\n\n',
          `data: ${JSON.stringify({
            type: 'tool_result',
            name: 'semantic_search_schools',
            result: JSON.stringify({
              query: '计算机强校',
              source: 'school-vector-index',
              results: [
                {
                  name: '北京邮电大学',
                  confidence: 'high',
                  source_type: 'vector_index',
                  source: 'chroma:school:school_1',
                },
              ],
            }),
          })}\n\n`,
          'data: {"type":"text","content":"我查到了北京邮电大学。"}\n\n',
        ].join(''),
      }),
    )

    await page.locator('#chat-input').fill('帮我查计算机强校')
    await page.getByRole('button', { name: '发送' }).click()

    await expect(page.getByText('我查到了北京邮电大学。')).toBeVisible()
    await expect(page.getByText('高可信')).toBeVisible()
    await expect(page.getByText('向量索引')).toBeVisible()
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
