import { existsSync, rmSync, unlinkSync } from 'fs';
import { resolve, dirname } from 'path';
import { fileURLToPath } from 'url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = dirname(__filename);

const PROJECT_ROOT = resolve(__dirname, '../../../../');
const E2E_ROOT = resolve(__dirname, '../../');
const PLAYWRIGHT_ROOT = resolve(__dirname, '../');
const PORTAL_ROOT = resolve(PROJECT_ROOT, 'web/apps/portal');

const TEMP_DIRS = [
  resolve(E2E_ROOT, 'test-results'),
  resolve(E2E_ROOT, 'playwright-report'),
  resolve(E2E_ROOT, 'blob-report'),
  resolve(PLAYWRIGHT_ROOT, 'test-results'),
  resolve(PLAYWRIGHT_ROOT, 'playwright-report'),
  resolve(PLAYWRIGHT_ROOT, 'blob-report'),
  resolve(PORTAL_ROOT, 'test-results'),
  resolve(PORTAL_ROOT, 'playwright-report'),
  resolve(PORTAL_ROOT, 'blob-report'),
  resolve(PROJECT_ROOT, 'artifacts/visual-test-screenshots'),
];

const TEMP_FILES = [
  resolve(PROJECT_ROOT, 'artifacts/visual-test-report.json'),
  resolve(PROJECT_ROOT, 'test_visual.db'),
  resolve(PLAYWRIGHT_ROOT, 'frontend-server.out.log'),
  resolve(PLAYWRIGHT_ROOT, 'frontend-server.err.log'),
  resolve(PORTAL_ROOT, 'frontend-server.log'),
];

export default async function globalTeardown() {
  if (process.env.SKIP_TEARDOWN === 'true') {
    console.log('[Cleanup Rule] SKIP_TEARDOWN=true: Preserving test database and artifacts during active test execution.');
    return;
  }
  console.log('[Cleanup Rule] Cleaning up visual test temporary files and artifacts...');
  
  for (const dir of TEMP_DIRS) {
    if (existsSync(dir)) {
      try {
        rmSync(dir, { recursive: true, force: true });
        console.log(`Cleaned up temporary directory: ${dir}`);
      } catch (err) {
        console.warn(`Could not remove ${dir}:`, err);
      }
    }
  }

  for (const file of TEMP_FILES) {
    if (existsSync(file)) {
      try {
        unlinkSync(file);
        console.log(`Cleaned up temporary file: ${file}`);
      } catch (err) {
        console.warn(`Could not remove ${file}:`, err);
      }
    }
  }

  console.log('[Cleanup Rule] Teardown cleanup complete.');
}
