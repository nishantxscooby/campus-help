import { defineConfig } from '@playwright/test';
import { fileURLToPath } from 'node:url';

const root = fileURLToPath(new URL('../', import.meta.url));
const server = (port, env = {}) => ({
  command: `python -m uvicorn campus_help.web.api:app --host 127.0.0.1 --port ${port}`,
  cwd: root,
  env,
  url: `http://127.0.0.1:${port}/health`,
  reuseExistingServer: false,
});

export default defineConfig({
  testDir: './e2e',
  workers: 1,
  use: { baseURL: 'http://127.0.0.1:8100', browserName: 'chromium' },
  webServer: [...['APPROVED', 'PENDING_REVIEW', 'REJECTED', 'wrong_page', 'stale'].map((scenario, index) => ({
    ...server(8102 + index, { REVIEW_TEST_CASE: scenario }),
    command: `python -m uvicorn --app-dir tests review_fixture:browser_app --factory --host 127.0.0.1 --port ${8102 + index}`,
  })), server(8100), server(8101, { CAMPUS_HELP_DATA_DIR: 'tests/absent-policy-source' })],
});
