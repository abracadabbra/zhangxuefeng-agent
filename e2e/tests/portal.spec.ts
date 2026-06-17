import { expect, test } from './fixtures'

async function openPortal(page: import('@playwright/test').Page, sessions: unknown[] = []) {
  await page.route('**/api/sessions*', (route) =>
    route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify(sessions),
    }),
  )
  await page.goto('/')
}

test.describe('Portal Homepage', () => {
  test('loads the homepage with title and scenario cards', async ({ page }) => {
    await openPortal(page)
    await expect(page.getByRole('banner')).toBeVisible()
    const cards = page.getByRole('listitem')
    await expect(cards).toHaveCount(3)
  })

  test('clicking gaokao card navigates to profile form', async ({ page }) => {
    await openPortal(page)
    await page.getByRole('listitem').first().click()
    await expect(page.getByRole('form')).toBeVisible()
  })

  test('clicking kaoyan card navigates to profile form', async ({ page }) => {
    await openPortal(page)
    await page.getByRole('listitem').nth(1).click()
    await expect(page.getByRole('form')).toBeVisible()
  })

  test('clicking career card navigates to profile form', async ({ page }) => {
    await openPortal(page)
    await page.getByRole('listitem').nth(2).click()
    await expect(page.getByRole('form')).toBeVisible()
  })

  test('theme toggle button is visible and clickable', async ({ page }) => {
    await openPortal(page)
    // aria-label is "切换到暗色模式" in zh-CN
    const themeButton = page.getByRole('button', { name: '切换到暗色模式' })
    await expect(themeButton).toBeVisible()
    await themeButton.click()
  })

  test('language toggle switches between EN and ZH', async ({ page }) => {
    await openPortal(page)
    // Initially shows "EN" as visible text in zh mode
    const langButton = page.getByText('EN')
    await expect(langButton).toBeVisible()
    await langButton.click()
    // After switching to English, button text changes to "中"
    await expect(page.getByText('中')).toBeVisible()
  })

  test('session history section shows when sessions exist', async ({ page }) => {
    await openPortal(page, [
      {
        session_id: 'aaaa-bbbb-cccc-dddd',
        created_at: new Date().toISOString(),
        message_count: 5,
      },
    ])

    // sessions.title = "历史会话", rendered as a <span class="stamp">
    await expect(page.getByText('历史会话')).toBeVisible()
  })
})
