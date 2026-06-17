import { expect, test } from './fixtures'

test.describe('Profile Form (Soul Question)', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/')

    // Click gaokao scenario to enter the form
    await page.getByRole('listitem').first().click()
    await expect(page.getByRole('form')).toBeVisible({ timeout: 10_000 })
  })

  test('displays form with progress bar and first step', async ({ page }) => {
    await expect(page.getByRole('progressbar')).toBeVisible()
    await expect(page.getByRole('form')).toBeVisible()
  })

  test('next button is disabled when no input', async ({ page }) => {
    // "下一步 →"
    const nextButton = page.getByRole('button', { name: '下一步 →' })
    await expect(nextButton).toBeDisabled()
  })

  test('filling score enables next button and advances to province step', async ({ page }) => {
    const scoreInput = page.locator('input[type="number"]')
    await scoreInput.fill('650')

    const nextButton = page.getByRole('button', { name: '下一步 →' })
    await expect(nextButton).toBeEnabled()
    await nextButton.click()

    // Step 2: Province select should appear
    await expect(page.locator('select')).toBeVisible()
  })

  test('completes full gaokao profile flow', async ({ page }) => {
    // Step 1: Score
    await page.locator('input[type="number"]').fill('620')
    await page.getByRole('button', { name: '下一步 →' }).click()

    // Step 2: Province (select dropdown)
    await page.locator('select').selectOption('北京')
    await page.getByRole('button', { name: '下一步 →' }).click()

    // Step 3: Subject (radio group)
    const subjectGroup = page.getByRole('radiogroup').first()
    await subjectGroup.getByRole('radio').first().click()
    await page.getByRole('button', { name: '下一步 →' }).click()

    // Step 4: Family budget (radio group)
    const budgetGroup = page.getByRole('radiogroup').first()
    await budgetGroup.getByRole('radio').first().click()

    // Last step — "开始咨询 →"
    await page.getByRole('button', { name: '开始咨询 →' }).click()

    // Should navigate to chat view (aria-label defaultValue: '聊天区域')
    await expect(page.getByLabel('聊天区域')).toBeVisible({ timeout: 10_000 })
  })

  test('back button returns to portal from first step', async ({ page }) => {
    // "返回" (exact match to avoid matching "← 返回首页" in header)
    const backButton = page.getByRole('button', { name: '返回', exact: true })
    await backButton.click()

    // Should be back on portal (scenario cards visible)
    await expect(page.getByRole('listitem').first()).toBeVisible()
  })

  test('back button goes to previous step from step 2', async ({ page }) => {
    // Fill step 1 and advance
    await page.locator('input[type="number"]').fill('500')
    await page.getByRole('button', { name: '下一步 →' }).click()

    // Now on step 2, click back — "上一步"
    await page.getByRole('button', { name: '上一步' }).click()

    // Should be back on step 1 — number input visible again
    await expect(page.locator('input[type="number"]')).toBeVisible()
  })

  test('skip button jumps directly to chat', async ({ page }) => {
    // Skip button text: "跳过，直接提问 →"
    await page.getByText('跳过，直接提问').click()

    await expect(page.getByLabel('聊天区域')).toBeVisible({ timeout: 10_000 })
  })

  test('progress bar updates as steps advance', async ({ page }) => {
    const progressbar = page.getByRole('progressbar')
    await expect(progressbar).toHaveAttribute('aria-valuenow', '1')

    // Advance to step 2
    await page.locator('input[type="number"]').fill('550')
    await page.getByRole('button', { name: '下一步 →' }).click()

    await expect(progressbar).toHaveAttribute('aria-valuenow', '2')
  })
})
