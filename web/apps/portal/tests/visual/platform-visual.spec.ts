import { test, expect } from '@playwright/test';

// Test user credentials matching database seed
const TEST_USERS = {
  student: { email: 'student@example.com', password: 'password123' },
  teacher: { email: 'teacher@example.com', password: 'password123' },
  parent: { email: 'parent@example.com', password: 'password123' },
};

const SAMPLE_EXAM_ID = 'e8efa978-a1cd-481c-bd6b-83a1e05d8e00';

async function login(page: any, role: 'student' | 'teacher' | 'parent') {
  const user = TEST_USERS[role];
  const apiUrl = process.env.API_URL || 'http://127.0.0.1:8002';
  try {
    const res = await page.request.post(`${apiUrl}/auth/token`, {
      form: { username: user.email, password: user.password },
    });
    if (res.ok()) {
      const data = await res.json();
      await page.goto('/login', { waitUntil: 'domcontentloaded' });
      await page.evaluate((tok: string) => localStorage.setItem('access_token', tok), data.access_token);
      return;
    }
  } catch {
    // Fallback to UI form login if direct API call fails
  }

  await page.goto('/login', { waitUntil: 'domcontentloaded' });
  await page.fill('input[type="email"], input[name="email"]', user.email);
  await page.fill('input[type="password"], input[name="password"]', user.password);
  await page.click('button[type="submit"]');
  await page.waitForURL('/', { timeout: 10000 });
  await page.waitForTimeout(500);
}

async function assertNoHorizontalOverflow(page: any) {
  const hasOverflow = await page.evaluate(() => {
    const docWidth = document.documentElement.clientWidth;
    return document.documentElement.scrollWidth > docWidth + 4 || document.body.scrollWidth > docWidth + 4;
  });
  expect(hasOverflow).toBe(false);
}

test.describe('Public Pages Visual & Layout Tests', () => {
  test('Landing/Login page - desktop', async ({ page }) => {
    await page.goto('/login', { waitUntil: 'domcontentloaded' });
    await page.waitForTimeout(500);
    await assertNoHorizontalOverflow(page);
    await expect(page).toHaveScreenshot('login-desktop.png', { fullPage: true });
  });

  test('Landing/Login page - mobile', async ({ page }) => {
    await page.setViewportSize({ width: 375, height: 667 });
    await page.goto('/login', { waitUntil: 'domcontentloaded' });
    await page.waitForTimeout(500);
    await assertNoHorizontalOverflow(page);
    await expect(page).toHaveScreenshot('login-mobile.png', { fullPage: true });
  });

  test('Landing/Login page - tablet', async ({ page }) => {
    await page.setViewportSize({ width: 768, height: 1024 });
    await page.goto('/login', { waitUntil: 'domcontentloaded' });
    await page.waitForTimeout(500);
    await assertNoHorizontalOverflow(page);
    await expect(page).toHaveScreenshot('login-tablet.png', { fullPage: true });
  });

  test('Register page - desktop', async ({ page }) => {
    await page.goto('/register', { waitUntil: 'domcontentloaded' });
    await page.waitForTimeout(500);
    await assertNoHorizontalOverflow(page);
    await expect(page).toHaveScreenshot('register-desktop.png', { fullPage: true });
  });

  test('Register page - mobile', async ({ page }) => {
    await page.setViewportSize({ width: 375, height: 667 });
    await page.goto('/register', { waitUntil: 'domcontentloaded' });
    await page.waitForTimeout(500);
    await assertNoHorizontalOverflow(page);
    await expect(page).toHaveScreenshot('register-mobile.png', { fullPage: true });
  });
});

test.describe('Student Dashboard Visual Tests', () => {
  test.beforeEach(async ({ page }) => {
    await login(page, 'student');
    await page.goto('/', { waitUntil: 'domcontentloaded' });
    await page.waitForTimeout(600);
  });

  test('Student Dashboard - desktop', async ({ page }) => {
    await assertNoHorizontalOverflow(page);
    await expect(page).toHaveScreenshot('dashboard-student-desktop.png', { fullPage: true });
  });

  test('Student Dashboard - mobile', async ({ page }) => {
    await page.setViewportSize({ width: 375, height: 667 });
    await page.waitForTimeout(500);
    await assertNoHorizontalOverflow(page);
    await expect(page).toHaveScreenshot('dashboard-student-mobile.png', { fullPage: true });
  });
});

test.describe('Teacher Views Visual Tests', () => {
  test.beforeEach(async ({ page }) => {
    await login(page, 'teacher');
  });

  test('Teacher Exams List - desktop', async ({ page }) => {
    await page.goto('/teacher-exams', { waitUntil: 'domcontentloaded' });
    await page.waitForTimeout(600);
    await assertNoHorizontalOverflow(page);
    await expect(page).toHaveScreenshot('teacher-exams-desktop.png', { fullPage: true });
  });

  test('Teacher Exams List - mobile', async ({ page }) => {
    await page.setViewportSize({ width: 375, height: 667 });
    await page.goto('/teacher-exams', { waitUntil: 'domcontentloaded' });
    await page.waitForTimeout(600);
    await assertNoHorizontalOverflow(page);
    await expect(page).toHaveScreenshot('teacher-exams-mobile.png', { fullPage: true });
  });

  test('Exam Editor - desktop', async ({ page }) => {
    await page.goto(`/teacher-exams/${SAMPLE_EXAM_ID}`, { waitUntil: 'domcontentloaded' });
    await page.waitForTimeout(600);
    await assertNoHorizontalOverflow(page);
    await expect(page).toHaveScreenshot('exam-editor-desktop.png', { fullPage: true });
  });

  test('Teacher Classes - desktop', async ({ page }) => {
    await page.goto('/teacher-classes', { waitUntil: 'domcontentloaded' });
    await page.waitForTimeout(600);
    await assertNoHorizontalOverflow(page);
    await expect(page).toHaveScreenshot('teacher-classes-desktop.png', { fullPage: true });
  });
});

test.describe('Admin Dashboard Visual Tests', () => {
  test.beforeEach(async ({ page }) => {
    await login(page, 'teacher');
    await page.goto('/admin', { waitUntil: 'domcontentloaded' });
    await page.waitForTimeout(600);
  });

  test('Admin Dashboard - desktop', async ({ page }) => {
    await assertNoHorizontalOverflow(page);
    await expect(page).toHaveScreenshot('dashboard-admin-desktop.png', { fullPage: true });
  });
});

test.describe('Take Exam Visual Tests', () => {
  test.beforeEach(async ({ page }) => {
    await login(page, 'student');
    await page.goto(`/exam/${SAMPLE_EXAM_ID}`, { waitUntil: 'domcontentloaded' });
    await page.waitForTimeout(600);
  });

  test('Take Exam page - desktop', async ({ page }) => {
    await assertNoHorizontalOverflow(page);
    await expect(page).toHaveScreenshot('take-exam-desktop.png', { fullPage: true });
  });

  test('Take Exam page - mobile', async ({ page }) => {
    await page.setViewportSize({ width: 375, height: 667 });
    await page.waitForTimeout(500);
    await assertNoHorizontalOverflow(page);
    await expect(page).toHaveScreenshot('take-exam-mobile.png', { fullPage: true });
  });
});

test.describe('Settings Page Visual Tests', () => {
  test.beforeEach(async ({ page }) => {
    await login(page, 'student');
    await page.goto('/settings', { waitUntil: 'domcontentloaded' });
    await page.waitForTimeout(600);
  });

  test('Settings page - desktop', async ({ page }) => {
    await assertNoHorizontalOverflow(page);
    await expect(page).toHaveScreenshot('settings-desktop.png', { fullPage: true });
  });

  test('Settings page - mobile', async ({ page }) => {
    await page.setViewportSize({ width: 375, height: 667 });
    await page.waitForTimeout(500);
    await assertNoHorizontalOverflow(page);
    await expect(page).toHaveScreenshot('settings-mobile.png', { fullPage: true });
  });
});

test.describe('Theme & Radius Visual Tests', () => {
  test('Themes cycle in Settings', async ({ page }) => {
    await login(page, 'teacher');
    await page.goto('/settings', { waitUntil: 'domcontentloaded' });
    await page.waitForTimeout(500);

    const themes = ['skyward', 'carbon_cyan', 'enterprise_blue', 'matrix_green', 'black_orange', 'comic_stage'];
    for (const theme of themes) {
      await page.evaluate((t: string) => document.documentElement.setAttribute('data-theme', t), theme);
      await page.waitForTimeout(150);
      await assertNoHorizontalOverflow(page);
    }
  });
});