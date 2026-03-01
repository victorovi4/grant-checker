// @ts-check
const { test, expect } = require('@playwright/test')

test.use({ headless: false, launchOptions: { slowMo: 600 } })

// Mock report returned by /verify
const MOCK_REPORT = {
  critical: [
    { quote: 'Рост на 300%', issue: 'Данные не подтверждены источником', recommendation: 'Указать первоисточник (Росстат)' },
  ],
  significant: [
    { quote: 'по данным экспертов', issue: 'Отсутствует конкретный источник', recommendation: 'Указать организацию и публикацию' },
    { quote: 'за последние годы', issue: 'Не указан временной период', recommendation: 'Указать конкретные годы' },
  ],
  minor: [
    { quote: 'многие граждане', issue: 'Голословное обобщение', recommendation: 'Указать численность или долю' },
  ],
  confirmed: [
    { quote: 'Национальный парк создан в 2008 году', issue: 'факт проверен', recommendation: 'Источник: ООПТ России' },
  ],
  needs_manual: [
    { quote: 'за 5 лет помогли 3000 семьям', issue: 'Внутренняя статистика организации', recommendation: 'Приложить отчёты о проектах' },
  ],
  raw_response: '',
}

// Minimal valid DOCX (PK header = ZIP = DOCX)
const FAKE_DOCX = Buffer.from('504b0304', 'hex')

test.describe('Export buttons', () => {

  // Intercept /verify and /export/docx so no real API key is needed
  test.beforeEach(async ({ page }) => {
    await page.route('/verify', async route => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify(MOCK_REPORT),
      })
    })

    await page.route('/export/docx', async route => {
      await route.fulfill({
        status: 200,
        contentType: 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
        body: FAKE_DOCX,
        headers: { 'Content-Disposition': 'attachment; filename="grantchecker_test.docx"' },
      })
    })
  })

  // -------------------------------------------------------------------------
  // Кнопки скрыты до проверки
  // -------------------------------------------------------------------------

  test('кнопки экспорта скрыты до первой проверки', async ({ page }) => {
    await page.goto('/')

    await expect(page.getByTestId('export-pdf-btn')).not.toBeVisible()
    await expect(page.getByTestId('export-docx-btn')).not.toBeVisible()
  })

  // -------------------------------------------------------------------------
  // Кнопки появляются после успешной проверки
  // -------------------------------------------------------------------------

  test('кнопки экспорта появляются после успешной проверки', async ({ page }) => {
    await page.goto('/')

    await page.getByTestId('text-input').fill('Тестовый текст заявки для проверки')
    await page.getByTestId('submit-btn').click()

    // Ждём результатов
    await expect(page.getByTestId('results')).not.toBeEmpty({ timeout: 10_000 })

    // Кнопки должны быть видны
    await expect(page.getByTestId('export-pdf-btn')).toBeVisible()
    await expect(page.getByTestId('export-docx-btn')).toBeVisible()
  })

  // -------------------------------------------------------------------------
  // Кнопка DOCX запускает скачивание
  // -------------------------------------------------------------------------

  test('кнопка DOCX запускает скачивание файла', async ({ page }) => {
    await page.goto('/')

    await page.getByTestId('text-input').fill('Тестовый текст')
    await page.getByTestId('submit-btn').click()

    await expect(page.getByTestId('export-docx-btn')).toBeVisible({ timeout: 10_000 })

    const downloadPromise = page.waitForEvent('download')
    await page.getByTestId('export-docx-btn').click()
    const download = await downloadPromise

    expect(download.suggestedFilename()).toMatch(/grantchecker.*\.docx/)
  })

  // -------------------------------------------------------------------------
  // Кнопка PDF видна и кликабельна
  // -------------------------------------------------------------------------

  test('кнопка PDF видна и кликабельна после проверки', async ({ page }) => {
    await page.goto('/')

    // Мокируем window.print до взаимодействия чтобы диалог не блокировал тест
    await page.evaluate(() => { window.print = () => { window._printCalled = true } })

    await page.getByTestId('text-input').fill('Тестовый текст')
    await page.getByTestId('submit-btn').click()

    await expect(page.getByTestId('export-pdf-btn')).toBeVisible({ timeout: 10_000 })
    await expect(page.getByTestId('export-pdf-btn')).toBeEnabled()

    await page.getByTestId('export-pdf-btn').click()

    // Убеждаемся, что window.print() был вызван
    const printCalled = await page.evaluate(() => window._printCalled)
    expect(printCalled).toBe(true)
  })

  // -------------------------------------------------------------------------
  // Результаты отчёта отображаются корректно
  // -------------------------------------------------------------------------

  test('отчёт содержит 5 секций с правильными данными', async ({ page }) => {
    await page.goto('/')

    await page.getByTestId('text-input').fill('Тестовый текст')
    await page.getByTestId('submit-btn').click()

    const results = page.getByTestId('results')
    await expect(results).not.toBeEmpty({ timeout: 10_000 })

    // Все 5 секций
    await expect(results.locator('.section')).toHaveCount(5)

    // Критические ошибки — 1 элемент
    const critical = results.locator('.section.critical .section-item')
    await expect(critical).toHaveCount(1)

    // Существенные замечания — 2 элемента
    const significant = results.locator('.section.significant .section-item')
    await expect(significant).toHaveCount(2)
  })

})
