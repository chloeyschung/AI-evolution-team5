import { defineConfig, devices } from '@playwright/test';

/**
 * Playwright configuration for Briefly web dashboard E2E tests.
 *
 * Run tests:
 *   npm run test:e2e          # Headless, CI mode
 *   npm run test:e2e:ui       # Interactive UI mode (shows test controller)
 *   npm run test:e2e:headed   # Headed browser (visible, runs all tests)
 *   npm run test:e2e:debug    # Debug mode with visible browser per test
 */

// Check if running in headed mode (via CLI flag or env)
const isHeaded = process.argv.includes('--headed') || process.env.PW_HEADED === 'true';

export default defineConfig({
  // Directory for test files
  testDir: './tests/e2e',

  // Run tests in files in parallel
  fullyParallel: true,

  // Fail the build on CI if you accidentally left test.only in the source code
  forbidOnly: !!process.env.CI,

  // Retry on CI only (flaky tests)
  retries: process.env.CI ? 2 : 0,

  // Opt out of parallel tests on CI for stability
  workers: process.env.CI ? 1 : undefined,

  // Reporter to use
  // Use 'list' for verbose output, 'html' for interactive report, 'line' for CI
  reporter: process.env.CI ? 'line' : 'html',

  // Shared settings for all projects
  use: {
    // Base URL for all tests (matches vite.config.ts server port)
    baseURL: 'http://localhost:3001',

    // Collect trace and screenshots for UI mode debugging
    trace: 'retain-on-failure',
    screenshot: 'only-on-failure',

    // Slow motion for UI mode to see what's happening
    // Uncomment for debugging:
    // actionTimeout: 15000,
    // navigationTimeout: 30000,
  },

  // Configure projects for different browsers
  projects: [
    {
      name: 'chromium',
      use: {
        ...devices['Desktop Chrome'],
        // Always show browser window (headed mode)
        launchOptions: {
          headless: false,
        },
      },
    },
  ],

  // Start web server before tests
  webServer: {
    command: 'npm run dev',
    url: 'http://localhost:3001',
    reuseExistingServer: true, // Reuse if already running
    timeout: 120000, // 2 minute timeout for server startup
  },
});
