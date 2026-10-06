import { existsSync, rmSync, unlinkSync } from 'fs';
import { resolve } from 'path';

const PROJECT_ROOT = resolve(__dirname, '../../../../');
const PORTAL_ROOT = resolve(__dirname, '../../');

const TEMP_DIRS = [
  resolve(PORTAL_ROOT, 'test-results'),
  resolve(PORTAL_ROOT, 'playwright-report'),
  resolve(PORTAL_ROOT, 'blob-report'),
  resolve(PROJECT_ROOT, 'artifacts/visual-test-screenshots'),
];

const TEMP_FILES = [
  resolve(PROJECT_ROOT, 'artifacts/visual-test-report.json'),
  resolve(PROJECT_ROOT, 'scratch/test_auth_flow.py'),
  resolve(PROJECT_ROOT, 'test_visual.db'),
];

export default async function globalTeardown() {
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
