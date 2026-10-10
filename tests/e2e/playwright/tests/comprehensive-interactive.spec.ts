import { test, expect } from '@playwright/test';

// Test user credentials matching database seed (scratch/seed_visual_db.py)
const TEST_USERS = {
  student: { email: 'student@example.com', password: 'password123' },
  teacher: { email: 'teacher@example.com', password: 'password123' },
  parent: { email: 'parent@example.com', password: 'password123' },
  admin: { email: 'admin@yourschool.edu', password: 'ChangeMe123!' },
};

const SAMPLE_EXAM_ID = 'e8efa978-a1cd-481c-bd6b-83a1e05d8e00';
const LIVE_EXAM_ID = 'f9efa978-a1cd-481c-bd6b-83a1e05d8e01';

async function login(page: any, role: 'student' | 'teacher' | 'parent' | 'admin') {
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
      await page.goto('/', { waitUntil: 'domcontentloaded' });
      await page.waitForTimeout(400);
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
    await expect(page.locator('button[type="submit"]')).toBeVisible();
    await assertNoHorizontalOverflow(page);
  });

  test('Landing/Login page - mobile', async ({ page }) => {
    await page.setViewportSize({ width: 375, height: 667 });
    await page.goto('/login', { waitUntil: 'domcontentloaded' });
    await expect(page.locator('button[type="submit"]')).toBeVisible();
    await assertNoHorizontalOverflow(page);
  });

  test('Landing/Login page - tablet', async ({ page }) => {
    await page.setViewportSize({ width: 768, height: 1024 });
    await page.goto('/login', { waitUntil: 'domcontentloaded' });
    await expect(page.locator('button[type="submit"]')).toBeVisible();
    await assertNoHorizontalOverflow(page);
  });

  test('Register page - desktop', async ({ page }) => {
    await page.goto('/register', { waitUntil: 'domcontentloaded' });
    await expect(page.locator('button[type="submit"]')).toBeVisible();
    await assertNoHorizontalOverflow(page);
  });

  test('Register page - mobile', async ({ page }) => {
    await page.setViewportSize({ width: 375, height: 667 });
    await page.goto('/register', { waitUntil: 'domcontentloaded' });
    await expect(page.locator('button[type="submit"]')).toBeVisible();
    await assertNoHorizontalOverflow(page);
  });
});

test.describe('Student Dashboard Visual Tests', () => {
  test.beforeEach(async ({ page }) => {
    await login(page, 'student');
    await page.goto('/', { waitUntil: 'domcontentloaded' });
    await page.waitForTimeout(500);
  });

  test('Student Dashboard - desktop', async ({ page }) => {
    await expect(page.locator('h1')).toBeVisible();
    await assertNoHorizontalOverflow(page);
  });

  test('Student Dashboard - mobile', async ({ page }) => {
    await page.setViewportSize({ width: 375, height: 667 });
    await page.waitForTimeout(400);
    await expect(page.locator('h1')).toBeVisible();
    await assertNoHorizontalOverflow(page);
  });
});

test.describe('Teacher Dashboard Visual Tests', () => {
  test.beforeEach(async ({ page }) => {
    await login(page, 'teacher');
    await page.goto(`/teacher-dashboard/${SAMPLE_EXAM_ID}`, { waitUntil: 'domcontentloaded' });
    await page.waitForTimeout(600);
  });

  test('Teacher Dashboard - desktop', async ({ page }) => {
    await expect(page.locator('h1:has-text("AI Grading Dashboard")')).toBeVisible({ timeout: 10000 });
    await assertNoHorizontalOverflow(page);
  });

  test('Teacher Dashboard - mobile', async ({ page }) => {
    await page.setViewportSize({ width: 375, height: 667 });
    await page.waitForTimeout(400);
    await expect(page.locator('h1:has-text("AI Grading Dashboard")')).toBeVisible({ timeout: 10000 });
    await assertNoHorizontalOverflow(page);
  });

  test('Teacher Exams page - desktop', async ({ page }) => {
    await page.goto('/teacher-exams', { waitUntil: 'domcontentloaded' });
    await page.waitForTimeout(500);
    await expect(page.locator('h1:has-text("Manage Exams")')).toBeVisible();
    await assertNoHorizontalOverflow(page);
  });

  test('Exam Editor - desktop', async ({ page }) => {
    await page.goto(`/teacher-exams/${SAMPLE_EXAM_ID}`, { waitUntil: 'domcontentloaded' });
    await page.waitForTimeout(500);
    await expect(page.locator('h3:has-text("Add Question")')).toBeVisible();
    await assertNoHorizontalOverflow(page);
  });

  test('Settings page - desktop', async ({ page }) => {
    await page.goto('/settings', { waitUntil: 'domcontentloaded' });
    await page.waitForTimeout(500);
    await expect(page.locator('h1:has-text("Settings")')).toBeVisible();
    await assertNoHorizontalOverflow(page);
  });
});

test.describe('Exam Taking Visual Tests', () => {
  test.beforeEach(async ({ page }) => {
    await login(page, 'student');
    await page.goto(`/exam/${LIVE_EXAM_ID}`, { waitUntil: 'domcontentloaded' });
    await page.waitForTimeout(800);
  });

  test('Exam Taking - desktop', async ({ page }) => {
    await expect(page.getByRole('button', { name: 'Start Exam', exact: true })).toBeVisible({ timeout: 10000 });
    await assertNoHorizontalOverflow(page);
  });

  test('Exam Taking - mobile', async ({ page }) => {
    await page.setViewportSize({ width: 375, height: 667 });
    await page.waitForTimeout(400);
    await expect(page.getByRole('button', { name: 'Start Exam', exact: true })).toBeVisible({ timeout: 10000 });
    await assertNoHorizontalOverflow(page);
  });
});

test.describe('Settings Page Visual Tests', () => {
  test.beforeEach(async ({ page }) => {
    await login(page, 'teacher');
    await page.goto('/settings', { waitUntil: 'domcontentloaded' });
    await page.waitForTimeout(500);
  });

  test('Settings - desktop', async ({ page }) => {
    await expect(page.locator('h1:has-text("Settings")')).toBeVisible();
    await assertNoHorizontalOverflow(page);
  });

  test('Settings - mobile', async ({ page }) => {
    await page.setViewportSize({ width: 375, height: 667 });
    await page.waitForTimeout(400);
    await expect(page.locator('h1:has-text("Settings")')).toBeVisible();
    await assertNoHorizontalOverflow(page);
  });
});

test.describe('Exam Editor Visual Tests', () => {
  test.beforeEach(async ({ page }) => {
    await login(page, 'teacher');
    await page.goto(`/teacher-exams/${SAMPLE_EXAM_ID}`, { waitUntil: 'domcontentloaded' });
    await page.waitForTimeout(500);
  });

  test('Exam Editor - desktop', async ({ page }) => {
    await expect(page.locator('h3:has-text("Add Question")')).toBeVisible();
    await assertNoHorizontalOverflow(page);
  });

  test('Exam Editor - mobile', async ({ page }) => {
    await page.setViewportSize({ width: 375, height: 667 });
    await page.waitForTimeout(400);
    await expect(page.locator('h3:has-text("Add Question")')).toBeVisible();
    await assertNoHorizontalOverflow(page);
  });
});

test.describe('Parent Dashboard Visual Tests', () => {
  test.beforeEach(async ({ page }) => {
    await login(page, 'parent');
    await page.goto('/parent-dashboard', { waitUntil: 'domcontentloaded' });
    await page.waitForTimeout(500);
  });

  test('Parent Dashboard - desktop', async ({ page }) => {
    await expect(page.locator('h1')).toBeVisible();
    await assertNoHorizontalOverflow(page);
  });
});

test.describe('Admin Dashboard Visual Tests', () => {
  test.beforeEach(async ({ page }) => {
    await login(page, 'admin');
    await page.goto('/admin', { waitUntil: 'domcontentloaded' });
    await page.waitForTimeout(500);
  });

  test('Admin Dashboard - desktop', async ({ page }) => {
    await expect(page.locator('h1')).toBeVisible();
    await assertNoHorizontalOverflow(page);
  });
});

test.describe('Exam Taking Flow - Interactive', () => {
  test.beforeEach(async ({ page }) => {
    await login(page, 'student');
    await page.goto(`/exam/${LIVE_EXAM_ID}`, { waitUntil: 'domcontentloaded' });
    await page.waitForTimeout(800);
  });

  test('Full exam flow - start, answer, submit', async ({ page }) => {
    // Wait for exam to load
    const startBtn = page.getByRole('button', { name: 'Start Exam', exact: true });
    await expect(startBtn).toBeVisible({ timeout: 10000 });

    // Start exam
    await startBtn.click();
    await page.waitForTimeout(500);

    // Answer first question (multiple choice)
    const firstRadio = page.locator('input[type="radio"]').first();
    if (await firstRadio.isVisible()) {
      await firstRadio.check();
    }

    // Answer essay question if present
    const essayTextarea = page.locator('textarea[placeholder*="Type your answer"]').first();
    if (await essayTextarea.isVisible()) {
      await essayTextarea.fill('Ribosomes translate mRNA into polypeptide chains during protein synthesis.');
    }

    // Submit exam
    await page.locator('button:has-text("Submit Exam")').first().click();

    // Should show completion
    await expect(page.locator('h1:has-text("Exam Submitted Successfully")')).toBeVisible({ timeout: 10000 });
  });
});

test.describe('Teacher Dashboard - Interactive', () => {
  test.beforeEach(async ({ page }) => {
    await login(page, 'teacher');
    await page.goto(`/teacher-dashboard/${SAMPLE_EXAM_ID}`, { waitUntil: 'domcontentloaded' });
    await page.waitForTimeout(800);
  });

  test('Generate AI grades', async ({ page }) => {
    await expect(page.locator('h1:has-text("AI Grading Dashboard")')).toBeVisible({ timeout: 10000 });

    const generateButton = page.locator('button:has-text("Generate AI Grades")').first();
    await expect(generateButton).toBeVisible({ timeout: 5000 });
    await generateButton.click();

    // Should show generated grade summary and Pending Review status
    await expect(page.locator('text=Pending Review').first()).toBeVisible({ timeout: 10000 });
    await expect(page.locator('text=Q1:').first()).toBeVisible({ timeout: 10000 });
  });

  test('Review and approve grades', async ({ page }) => {
    await expect(page.locator('h1:has-text("AI Grading Dashboard")')).toBeVisible({ timeout: 10000 });

    // Generate AI grades first if not already generated in this session
    const generateButton = page.locator('button:has-text("Generate AI Grades")').first();
    if (await generateButton.isVisible()) {
      await generateButton.click();
      await expect(page.locator('button:has-text("Review")').first()).toBeVisible({ timeout: 10000 });
    }

    // Click Review on first submission
    const reviewButton = page.locator('button:has-text("Review")').first();
    await reviewButton.click();

    // Should show review modal with AI: badge
    await expect(page.locator('h2:has-text("Review AI Grades")')).toBeVisible({ timeout: 5000 });
    await expect(page.locator('text=AI:').first()).toBeVisible();

    // Open question-level review form inside modal
    const questionReviewBtn = page.locator('button:has-text("Review")').last();
    if (await questionReviewBtn.isVisible()) {
      await questionReviewBtn.click();
      const approveButton = page.locator('button:has-text("Approve & Save")').first();
      await expect(approveButton).toBeVisible();
      await approveButton.click();
      await expect(page.locator('text=✓ Teacher Approved').first()).toBeVisible();
    }

    // Close modal cleanly
    await page.locator('button:has-text("Close")').click();
    await expect(page.locator('h2:has-text("Review AI Grades")')).toBeHidden();
  });
});

test.describe('Settings Page - Interactive', () => {
  test.beforeEach(async ({ page }) => {
    await login(page, 'teacher');
    await page.goto('/settings', { waitUntil: 'domcontentloaded' });
    await page.waitForTimeout(600);
  });

  test('Passkeys registration flow', async ({ page }) => {
    await expect(page.locator('h3:has-text("Passkeys (WebAuthn)")')).toBeVisible({ timeout: 5000 });

    const registerButton = page.locator('button:has-text("Register Passkey")');
    await expect(registerButton).toBeVisible();
    await registerButton.click();

    // Should show registration modal
    await expect(page.locator('h2:has-text("Register Passkey")')).toBeVisible({ timeout: 5000 });
    await expect(page.locator('button:has-text("Create Passkey")')).toBeVisible();

    // Close modal
    await page.locator('button:has-text("Cancel")').click();
    await expect(page.locator('h2:has-text("Register Passkey")')).toBeHidden();
  });

  test('2FA setup flow', async ({ page }) => {
    await expect(page.locator('h3:has-text("Two-Factor Authentication (TOTP)")')).toBeVisible({ timeout: 5000 });

    const enableButton = page.locator('button:has-text("Enable 2FA")');
    if (await enableButton.isVisible()) {
      await enableButton.click();

      // Should show QR code and secret
      await expect(page.locator('img[alt="2FA QR Code"]')).toBeVisible({ timeout: 5000 });
      await expect(page.locator('h4:has-text("Step 1: Scan QR Code")')).toBeVisible();

      // Cancel setup
      await page.locator('button:has-text("Cancel")').click();
    }
  });

  test('AI Key management', async ({ page }) => {
    await expect(page.locator('h3:has-text("AI Provider Settings")')).toBeVisible({ timeout: 5000 });

    const providerSelect = page.locator('select:has(option[value="openrouter"])');
    await expect(providerSelect).toBeVisible();
    await providerSelect.selectOption('openrouter');
    await expect(providerSelect).toHaveValue('openrouter');

    const saveBtn = page.locator('button:has-text("Save AI Settings")');
    await expect(saveBtn).toBeVisible();
    await saveBtn.click();
  });
});

test.describe('Exam Editor - Interactive', () => {
  test.beforeEach(async ({ page }) => {
    await login(page, 'teacher');
    await page.goto('/teacher-exams', { waitUntil: 'domcontentloaded' });
    await page.waitForTimeout(600);
  });

  test('Create exam with questions', async ({ page }) => {
    const examTitle = 'Interactive Test Exam ' + Date.now();

    // Create new exam on /teacher-exams
    const titleInput = page.locator('input[placeholder="New Exam Title..."]');
    await expect(titleInput).toBeVisible();
    await titleInput.fill(examTitle);
    await page.locator('button:has-text("Create New Exam")').click();

    // Verify new exam card appears and open its Exam Editor
    const examHeading = page.locator(`h3:has-text("${examTitle}")`);
    await expect(examHeading).toBeVisible({ timeout: 5000 });

    await page.locator('a:has-text("Edit Editor")').last().click();

    // Verify Exam Editor loaded and add a question
    await expect(page.locator(`h1:has-text("${examTitle}")`)).toBeVisible({ timeout: 5000 });
    await page.locator('input[placeholder="Question text..."]').fill('What is 2+2?');
    await page.locator('button:has-text("Add")').click();

    // Verify question appears in Question Bank
    await expect(page.locator('strong:has-text("1. What is 2+2?")')).toBeVisible({ timeout: 5000 });
  });
});