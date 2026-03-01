// @ts-check
const { test, expect } = require('@playwright/test')

const SAMPLE_TEXT = `В Ладожском озере с 2010-х годов нарастает экологическая проблема.
По данным Российской газеты и экспертов Института озероведения РАН,
шхеры и острова Ладожского озера ежегодно тонут в мусоре от «диких» туристов.
Национальный парк «Ладожские шхеры» создан в 2008 году, туристическая инфраструктура отсутствует.
Ладога получает около 85% воды через притоки — Волхов, Свирь, Вуоксу, Сясь.
По заключению директора Института озероведения РАН Шамиля Позднякова (АиФ Санкт-Петербург, 2021),
«экосистема Ладоги сегодня балансирует на краю».`

test.use({ headless: false, launchOptions: { slowMo: 600 } })

test.describe('GrantChecker', () => {

  // -------------------------------------------------------------------------
  // Базовая загрузка страницы
  // -------------------------------------------------------------------------

  test('страница загружается, селекторы провайдера и модели видны', async ({ page }) => {
    await page.goto('/')

    await expect(page.getByTestId('provider-select')).toBeVisible()
    await expect(page.getByTestId('model-select')).toBeVisible()
    await expect(page.getByTestId('text-input')).toBeVisible()
    await expect(page.getByTestId('submit-btn')).toBeVisible()
    await expect(page.getByTestId('results')).toBeAttached()
  })

  // -------------------------------------------------------------------------
  // /models endpoint — оба провайдера присутствуют
  // -------------------------------------------------------------------------

  test('GET /models возвращает anthropic и yandex', async ({ request }) => {
    const resp = await request.get('/models')
    expect(resp.ok()).toBeTruthy()
    const data = await resp.json()
    expect(data.anthropic).toContain('claude-sonnet-4-6')
    expect(data.yandex).toContain('yandexgpt/latest')
  })

  // -------------------------------------------------------------------------
  // Смена провайдера обновляет список моделей
  // -------------------------------------------------------------------------

  test('выбор YandexGPT меняет список моделей', async ({ page }) => {
    await page.goto('/')

    const providerSelect = page.getByTestId('provider-select')
    const modelSelect = page.getByTestId('model-select')

    // Дефолт — anthropic
    await expect(modelSelect).toHaveValue('claude-sonnet-4-6')

    // Переключаем на yandex
    await providerSelect.selectOption('yandex')

    // Список моделей должен обновиться
    await expect(modelSelect).toHaveValue('yandexgpt/latest')
    const options = await modelSelect.locator('option').allTextContents()
    expect(options).toContain('yandexgpt/latest')
    expect(options).not.toContain('claude-sonnet-4-6')
  })

  // -------------------------------------------------------------------------
  // Проверка через Anthropic (real API) @real-api
  // -------------------------------------------------------------------------

  test('проверка через Anthropic возвращает отчёт @real-api', async ({ page }) => {
    test.setTimeout(120_000)
    await page.goto('/')

    await page.getByTestId('provider-select').selectOption('anthropic')
    await page.getByTestId('model-select').selectOption('claude-sonnet-4-6')
    await page.getByTestId('text-input').fill(SAMPLE_TEXT)
    await page.getByTestId('submit-btn').click()

    // Лоадер появился
    await expect(page.getByTestId('loader')).toBeVisible()

    // Ждём результатов (до 90 сек)
    await expect(page.getByTestId('results')).not.toBeEmpty({ timeout: 90_000 })

    // Секции отчёта присутствуют
    const results = page.getByTestId('results')
    await expect(results.locator('.section')).toHaveCount(5)

    // Нет сообщения об ошибке
    await expect(results.locator('p[style*="color:red"]')).not.toBeVisible()

    await page.pause()
  })

  // -------------------------------------------------------------------------
  // Проверка через YandexGPT (real API) @real-api
  // -------------------------------------------------------------------------

  test('проверка через YandexGPT возвращает отчёт @real-api', async ({ page }) => {
    test.setTimeout(120_000)
    await page.goto('/')

    await page.getByTestId('provider-select').selectOption('yandex')
    await expect(page.getByTestId('model-select')).toHaveValue('yandexgpt/latest')

    await page.getByTestId('text-input').fill(SAMPLE_TEXT)
    await page.getByTestId('submit-btn').click()

    // Ждём результатов (секции или сообщение об ошибке)
    const results = page.getByTestId('results')
    await expect(results).not.toBeEmpty({ timeout: 90_000 })

    // Если есть сообщение об ошибке — выводим и падаем
    const errorMsg = results.locator('p[style*="color:red"]')
    if (await errorMsg.isVisible()) {
      const errText = await errorMsg.textContent()
      throw new Error(`YandexGPT вернул ошибку: ${errText}`)
    }

    // Есть все 5 секций отчёта
    await expect(results.locator('.section')).toHaveCount(5)
    await page.pause()
  })
})
