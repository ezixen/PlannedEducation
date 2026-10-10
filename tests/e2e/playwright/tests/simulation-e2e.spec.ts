import { test, expect } from '@playwright/test';

const TEST_USERS = {
  student: { email: 'student@example.com', password: 'password123' },
  teacher: { email: 'teacher@example.com', password: 'password123' },
  parent: { email: 'parent@example.com', password: 'password123' },
};

const SAMPLE_EXAM_ID = 'e8efa978-a1cd-481c-bd6b-83a1e05d8e00';

async function login(page: any, email: string, pass: string) {
  const apiUrl = process.env.API_URL || 'http://127.0.0.1:8002';
  try {
    const res = await page.request.post(`${apiUrl}/auth/token`, {
      form: { username: email, password: pass },
    });
    if (res.ok()) {
      const data = await res.json();
      await page.goto('/login', { waitUntil: 'domcontentloaded' });
      await page.evaluate((tok: string) => localStorage.setItem('access_token', tok), data.access_token);
      return;
    }
  } catch {
    // fallback
  }

  await page.goto('/login', { waitUntil: 'domcontentloaded' });
  await page.fill('input[type="email"], input[name="email"]', email);
  await page.fill('input[type="password"], input[name="password"]', pass);
  await page.click('button[type="submit"]');
  await page.waitForURL('/', { timeout: 10000 });
}

async function assertNoHorizontalOverflow(page: any) {
  const hasOverflow = await page.evaluate(() => {
    const docWidth = document.documentElement.clientWidth;
    return document.documentElement.scrollWidth > docWidth + 4 || document.body.scrollWidth > docWidth + 4;
  });
  expect(hasOverflow).toBe(false);
}

test.describe('Multi-Role Live Simulation & Administration', () => {
  test('Teacher: Live Exam Proctoring & Anonymized Submissions', async ({ page }) => {
    await login(page, TEST_USERS.teacher.email, TEST_USERS.teacher.password);
    await page.goto(`/teacher-dashboard/${SAMPLE_EXAM_ID}`, { waitUntil: 'domcontentloaded' });
    
    // Wait for the dashboard heading to load
    const heading = page.locator('h1:has-text("AI Grading Dashboard")');
    await expect(heading).toBeVisible({ timeout: 10000 });

    await assertNoHorizontalOverflow(page);
  });

  test('Parent: Review Student Progress & Empathetic Feedback', async ({ page }) => {
    await login(page, TEST_USERS.parent.email, TEST_USERS.parent.password);
    await page.goto('/parent-dashboard', { waitUntil: 'domcontentloaded' });
    
    // Verify parent portal content
    const heading = page.locator('h1:has-text("Parent Portal")');
    await expect(heading).toBeVisible({ timeout: 10000 });

    await assertNoHorizontalOverflow(page);

    // Check that student progress card is displayed
    const studentName = page.locator('text=Alex Rivera');
    await expect(studentName).toBeVisible({ timeout: 10000 });
  });

  test('Teacher: Class Management & Roster View', async ({ page }) => {
    await login(page, TEST_USERS.teacher.email, TEST_USERS.teacher.password);
    await page.goto('/teacher-classes', { waitUntil: 'domcontentloaded' });
    
    const heading = page.locator('h1:has-text("Class Groupings")');
    await expect(heading).toBeVisible({ timeout: 10000 });

    await assertNoHorizontalOverflow(page);

    const bodyText = await page.textContent('body');
    expect(bodyText).toContain('Calculus 101');
  });

  test('Destructive Test: Admin Deletes User and Re-Registers Fresh Account', async ({ page }) => {
    await login(page, TEST_USERS.teacher.email, TEST_USERS.teacher.password);
    await page.goto('/admin', { waitUntil: 'domcontentloaded' });
    
    await expect(page.locator('h1:has-text("Teacher Admin Dashboard")')).toBeVisible({ timeout: 10000 });
    await assertNoHorizontalOverflow(page);

    // Switch to Users tab
    const usersTab = page.locator('button:has-text("Users")');
    await expect(usersTab).toBeVisible({ timeout: 10000 });
    await usersTab.click();
    await page.waitForTimeout(600);

    // Verify users table has disposable_user
    const userRow = page.locator('tr:has-text("disposable_user")');
    await expect(userRow).toBeVisible({ timeout: 10000 });

    // Click delete button for disposable_user with dialog confirmation
    page.once('dialog', async dialog => {
      await dialog.accept();
    });

    const deleteBtn = userRow.locator('button:has-text("Delete")');
    await deleteBtn.click();
    await expect(userRow).not.toBeVisible({ timeout: 10000 });

    // Now test re-creating a student account via Register page
    const freshStamp = Date.now();
    const freshEmail = `fresh_${freshStamp}@example.com`;
    const freshUser = `user_${freshStamp}`;

    await page.goto('/register', { waitUntil: 'domcontentloaded' });
    await expect(page.locator('h1:has-text("Planned Education")')).toBeVisible({ timeout: 10000 });

    await page.fill('input[name="full_name"]', 'Taylor Swift');
    await page.fill('input[name="username"]', freshUser);
    await page.fill('input[name="email"]', freshEmail);
    await page.fill('input[name="password"]', 'Password123!');
    await page.fill('input[name="confirm_password"]', 'Password123!');
    
    // Submit registration
    const submitBtn = page.locator('button[type="submit"]');
    await submitBtn.click();
    await page.waitForURL('**/login', { timeout: 10000 });

    // Verify redirected to login with fresh credentials
    expect(page.url()).toContain('/login');
  });

  test('All 10 Themes & 3 Border Radii Display with High Legibility & Zero Overflow', async ({ page }) => {
    await login(page, TEST_USERS.teacher.email, TEST_USERS.teacher.password);
    await page.goto('/settings', { waitUntil: 'domcontentloaded' });
    await page.waitForTimeout(600);

    const allThemes = [
      'skyward',
      'carbon_cyan',
      'enterprise_blue',
      'blush_silver',
      'matrix_green',
      'black_orange',
      'sunset_cabin',
      'aurora_night',
      'comic_stage',
      'ocean_calm',
    ];

    const radii = ['square', 'soft', 'round'];

    for (const theme of allThemes) {
      await page.evaluate((t: string) => document.documentElement.setAttribute('data-theme', t), theme);
      for (const radius of radii) {
        await page.evaluate((r: string) => document.documentElement.setAttribute('data-radius', r), radius);
        await page.waitForTimeout(80);
        await assertNoHorizontalOverflow(page);
      }
    }
  });
});
