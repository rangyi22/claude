import { defineConfig } from '@playwright/test';

const externalUrl = process.env.E2E_BASE_URL;

export default defineConfig({
  testDir: 'e2e',
  fullyParallel: false,
  workers: 1,
  use: { baseURL: externalUrl ?? 'http://localhost:3100', trace: 'retain-on-failure' },
  webServer: externalUrl
    ? undefined
    : {
        command: 'npx next build && npx tsx scripts/e2eServer.ts',
        url: 'http://localhost:3100',
        timeout: 180_000,
        reuseExistingServer: false,
      },
});
