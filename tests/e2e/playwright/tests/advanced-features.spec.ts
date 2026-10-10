import { test, expect } from '@playwright/test';

const TEST_USERS = {
  teacher: { email: 'teacher@example.com', password: 'password123' },
  student: { email: 'student@example.com', password: 'password123' },
  parent: { email: 'parent@example.com', password: 'password123' },
};

const SAMPLE_EXAM_ID = 'e8efa978-a1cd-481c-bd6b-83a1e05d8e00';
const LIVE_EXAM_ID = 'f9efa978-a1cd-481c-bd6b-83a1e05d8e01';

async function login(page: any, email: string, pass: string) {
  await page.goto('/login', { waitUntil: 'domcontentloaded' });
  const emailInput = page.locator('input[type="email"], input[name="email"]');
  await expect(emailInput).toBeVisible({ timeout: 10000 });
  await emailInput.fill(email);
  await page.fill('input[type="password"], input[name="password"]', pass);
  await page.click('button[type="submit"]');
  await page.waitForURL((url: URL) => !url.pathname.includes('/login'), { timeout: 10000 });
}

async function assertNoHorizontalOverflow(page: any) {
  const hasOverflow = await page.evaluate(() => {
    const docWidth = document.documentElement.clientWidth;
    return document.documentElement.scrollWidth > docWidth + 4 || document.body.scrollWidth > docWidth + 4;
  });
  expect(hasOverflow).toBe(false);
}

test.describe('Advanced & Newly Added Features Visual Verification', () => {
  test('1. Teacher Dashboard: Archive Management Panel & Statistics', async ({ page }) => {
    await login(page, TEST_USERS.teacher.email, TEST_USERS.teacher.password);
    await page.goto(`/teacher-dashboard/${SAMPLE_EXAM_ID}`, { waitUntil: 'domcontentloaded' });

    // Verify main dashboard heading
    const heading = page.locator('h1:has-text("AI Grading Dashboard")');
    await expect(heading).toBeVisible({ timeout: 10000 });

    // Locate Archive Management section
    const archiveHeading = page.locator('h3:has-text("Archived Submissions")');
    await expect(archiveHeading).toBeVisible({ timeout: 10000 });

    // Verify Archive Stats Cards
    const statsCards = page.locator('text=Total Archives');
    await expect(statsCards).toBeVisible({ timeout: 10000 });
    await expect(page.locator('text=Total Size')).toBeVisible();
    await expect(page.locator('text=Space Saved')).toBeVisible();

    // Verify Filters (Year, Month, Status)
    const filters = page.locator('select');
    await expect(filters.first()).toBeVisible();

    // Verify Archive Table contains seeded submission
    const archiveTable = page.locator('table');
    await expect(archiveTable.first()).toBeVisible();
    const bodyText = await page.textContent('body');
    expect(bodyText).toContain('sub-uuid-001');
    expect(bodyText).toContain('archived');
    expect(bodyText).toContain('4.0x');

    // Verify Action buttons (Download & Restore)
    const restoreBtn = page.locator('button:has-text("Restore")');
    await expect(restoreBtn.first()).toBeVisible();
    const downloadBtn = page.locator('button:has-text("Download")');
    await expect(downloadBtn.first()).toBeVisible();

    await assertNoHorizontalOverflow(page);
  });

  test('2. Teacher Dashboard: Test Package Manager & Export Modal', async ({ page }) => {
    await login(page, TEST_USERS.teacher.email, TEST_USERS.teacher.password);
    await page.goto(`/teacher-dashboard/${SAMPLE_EXAM_ID}`, { waitUntil: 'domcontentloaded' });

    // Locate Package Manager panel
    const pkgHeader = page.locator('h2:has-text("Test Package Manager")');
    await expect(pkgHeader).toBeVisible({ timeout: 10000 });

    // Click Export Current Exam button
    const exportBtn = page.locator('button:has-text("Export Current Exam")');
    await expect(exportBtn).toBeVisible({ timeout: 10000 });
    await exportBtn.click();

    // Verify Export Modal
    const modalHeader = page.locator('h3:has-text("Export Exam as Package")');
    await expect(modalHeader).toBeVisible({ timeout: 5000 });

    // Verify checkboxes and controls inside export dialog
    await expect(page.locator('text=Include correct answers')).toBeVisible();
    await expect(page.locator('text=Include rubrics')).toBeVisible();
    await expect(page.locator('text=Include question variables')).toBeVisible();
    await expect(page.locator('text=Format')).toBeVisible();
    await expect(page.locator('text=Compress (gzip)')).toBeVisible();

    // Verify Cancel button
    const cancelBtn = page.locator('button:has-text("Cancel")');
    await expect(cancelBtn).toBeVisible();
    await cancelBtn.click();
    await expect(modalHeader).not.toBeVisible({ timeout: 5000 });

    // Verify Import Package Section
    await expect(page.locator('h3:has-text("Import Package")')).toBeVisible();
    await expect(page.locator('text=Upload a test package (JSON or YAML)')).toBeVisible();
    await expect(page.locator('input[type="file"]')).toBeVisible();
    await expect(page.locator('button:has-text("Validate")')).toBeVisible();
    await expect(page.locator('button:has-text("Import")')).toBeVisible();

    await assertNoHorizontalOverflow(page);
  });

  test('3. Settings: 2FA TOTP Setup, Secret Key & Recovery Codes', async ({ page }) => {
    await login(page, TEST_USERS.teacher.email, TEST_USERS.teacher.password);
    await page.goto('/settings', { waitUntil: 'domcontentloaded' });

    const twoFASection = page.locator('h3:has-text("Two-Factor Authentication (TOTP)")');
    await expect(twoFASection).toBeVisible({ timeout: 10000 });

    // Click Enable 2FA button
    const enableBtn = page.locator('button:has-text("Enable 2FA")');
    await expect(enableBtn).toBeVisible({ timeout: 5000 });
    await enableBtn.click();

    // Verify Step 1: Scan QR Code & Secret
    const qrHeader = page.locator('h4:has-text("Step 1: Scan QR Code")');
    await expect(qrHeader).toBeVisible({ timeout: 10000 });

    const qrImage = page.locator('img[alt="2FA QR Code"]');
    await expect(qrImage).toBeVisible({ timeout: 5000 });
    await expect(page.locator('text=Or enter this secret manually:')).toBeVisible();

    // Verify Step 2: Verify Code input
    const step2Header = page.locator('h4:has-text("Step 2: Verify Code")');
    await expect(step2Header).toBeVisible();
    const totpInput = page.locator('input[placeholder="123456"]');
    await expect(totpInput).toBeVisible();

    // Verify Step 3: Recovery Codes
    const step3Header = page.locator('h4:has-text("Step 3: Save Recovery Codes")');
    await expect(step3Header).toBeVisible();

    // Cancel setup to return cleanly
    const cancelBtn = page.locator('button:has-text("Cancel")');
    await cancelBtn.click();
    await expect(qrHeader).not.toBeVisible({ timeout: 5000 });

    await assertNoHorizontalOverflow(page);
  });

  test('4. Settings: AI Provider BYOK Configuration & Model Settings', async ({ page }) => {
    await login(page, TEST_USERS.teacher.email, TEST_USERS.teacher.password);
    await page.goto('/settings', { waitUntil: 'domcontentloaded' });

    const aiHeader = page.locator('h3:has-text("AI Provider Settings")');
    await expect(aiHeader).toBeVisible({ timeout: 10000 });

    // Verify empathetic educational explanation
    await expect(page.locator('text=Configure your AI provider for automated grading')).toBeVisible();

    // Verify Provider Selector and Options
    const providerSelect = page.locator('select:has(option[value="gemini"])');
    await expect(providerSelect).toBeVisible();

    // Verify model name input
    const modelInput = page.locator('input[value*="gemini"], input[placeholder*="gemini"]');
    await expect(modelInput.first()).toBeVisible();

    // Verify Save Settings button
    const saveBtn = page.locator('button:has-text("Save AI Settings")');
    await expect(saveBtn).toBeVisible();

    await assertNoHorizontalOverflow(page);
  });

  test('5. Settings: Handwritten Math OCR & Speech-to-Text Processors', async ({ page }) => {
    await login(page, TEST_USERS.teacher.email, TEST_USERS.teacher.password);
    await page.goto('/settings', { waitUntil: 'domcontentloaded' });

    // Verify OCR Scanner Panel
    const ocrHeader = page.locator('h3:has-text("OCR Processor")');
    await expect(ocrHeader).toBeVisible({ timeout: 10000 });
    await expect(page.locator('text=Extract text from handwritten exam images using Tesseract OCR')).toBeVisible();
    await expect(page.locator('text=Math-specific OCR (optimized for equations)')).toBeVisible();
    await expect(page.locator('button:has-text("Process OCR")')).toBeVisible();

    // Verify Speech-to-Text Panel
    const sttHeader = page.locator('h3:has-text("Speech-to-Text Processor")');
    await expect(sttHeader).toBeVisible({ timeout: 10000 });
    await expect(page.locator('text=Transcribe audio recordings using faster-whisper')).toBeVisible();
    await expect(page.locator('button:has-text("Transcribe Audio")')).toBeVisible();

    await assertNoHorizontalOverflow(page);
  });

  test('6. Student Take Exam: Live Questions, Digital Hand Raise Chat & Timer', async ({ page }) => {
    await login(page, TEST_USERS.student.email, TEST_USERS.student.password);
    await page.goto(`/exam/${LIVE_EXAM_ID}`, { waitUntil: 'domcontentloaded' });

    // Verify Exam Container & Questions
    const question1 = page.locator('h3:has-text("Question 1")');
    await expect(question1).toBeVisible({ timeout: 10000 });
    await expect(page.locator('text=Which cellular organelle is responsible for generating the majority of cellular ATP?')).toBeVisible();

    // Verify answer choices
    await expect(page.locator('text=Mitochondria')).toBeVisible();
    await expect(page.locator('text=Chloroplast')).toBeVisible();

    // Verify Question 2 (Essay)
    await expect(page.locator('h3:has-text("Question 2")')).toBeVisible();
    await expect(page.locator('textarea[placeholder*="Type your answer here"]')).toBeVisible();

    // Verify Digital Hand Raise Chat
    const chatHeader = page.locator('strong:has-text("Digital Hand Raise")');
    await expect(chatHeader).toBeVisible({ timeout: 10000 });

    // Verify Timer Banner
    const timerText = page.locator('text=Time Remaining');
    await expect(timerText.first()).toBeVisible();

    await assertNoHorizontalOverflow(page);
  });

  test('7. Responsive Layout & Theme Adaptability on Mobile Viewport', async ({ page }) => {
    await page.setViewportSize({ width: 375, height: 667 });

    await login(page, TEST_USERS.teacher.email, TEST_USERS.teacher.password);
    await page.goto('/settings', { waitUntil: 'domcontentloaded' });

    // Test across distinct dark and light themes
    const themesToTest = ['skyward', 'carbon_cyan', 'matrix_green', 'black_orange', 'sunset_cabin'];

    for (const theme of themesToTest) {
      await page.evaluate((t: string) => document.documentElement.setAttribute('data-theme', t), theme);
      await page.waitForTimeout(100);
      await assertNoHorizontalOverflow(page);

      // Verify header and primary form inputs are visible without clipping
      await expect(page.locator('h1:has-text("Settings")')).toBeVisible();
      await expect(page.locator('input[type="tel"]')).toBeVisible();
    }
  });
});

