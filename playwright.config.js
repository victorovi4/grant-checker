// @ts-check
const { defineConfig } = require('@playwright/test')

module.exports = defineConfig({
  testDir: './tests/e2e',
  timeout: 120_000,
  use: {
    baseURL: 'http://localhost:8000',
  },
})
