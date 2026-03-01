// @ts-check
const { defineConfig } = require('@playwright/test')

module.exports = defineConfig({
  testDir: './tests/e2e',
  timeout: 120_000,
  use: {
    baseURL: 'http://localhost:8000',
  },
  webServer: {
    command: 'venv/bin/uvicorn api:app --port 8000',
    url: 'http://localhost:8000/health',
    reuseExistingServer: true,
    timeout: 30_000,
  },
})
