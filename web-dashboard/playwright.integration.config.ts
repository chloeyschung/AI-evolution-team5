import { defineConfig, devices } from '@playwright/test';

export default defineConfig({
  testDir: './tests/e2e',
  fullyParallel: false,
  retries: 0,
  reporter: 'list',
  use: {
    baseURL: 'http://localhost:3001',
    trace: 'retain-on-failure',
    screenshot: 'only-on-failure',
  },
  projects: [
    {
      name: 'chromium',
      use: {
        ...devices['Desktop Chrome'],
        launchOptions: {
          headless: true,
        },
      },
    },
  ],
  webServer: [
    {
      command: "bash -lc 'cd .. && set -a && source .env && set +a && uv run uvicorn src.api.app:app --host 127.0.0.1 --port 8000'",
      url: 'http://127.0.0.1:8000/',
      reuseExistingServer: true,
      timeout: 120000,
    },
    {
      command: 'VITE_API_BASE_URL=http://127.0.0.1:8000 npm run dev',
      url: 'http://localhost:3001',
      reuseExistingServer: true,
      timeout: 120000,
    },
  ],
});
