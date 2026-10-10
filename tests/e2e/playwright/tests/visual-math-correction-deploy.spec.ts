import { test, expect, chromium } from '@playwright/test';

const API_URL = process.env.API_URL || 'http://127.0.0.1:8002';
const PORTAL_URL = process.env.BASE_URL || 'http://127.0.0.1:5175';

async function registerAndLogin(
  page: any,
  email: string,
  fullName: string,
  role: 'teacher' | 'student'
): Promise<string> {
  const username = email.split('@')[0].replace(/[^a-zA-Z0-9_]/g, '_');
  const password = 'StrongPassword123!';

  await page.request.post(`${API_URL}/auth/register`, {
    data: {
      email,
      username,
      password,
      full_name: fullName,
      role,
    },
  });

  const tokRes = await page.request.post(`${API_URL}/auth/token`, {
    form: { username: email, password },
  });
  expect(tokRes.ok()).toBeTruthy();
  const tokData = await tokRes.json();

  await page.goto(`${PORTAL_URL}/login`, { waitUntil: 'domcontentloaded' });
  await page.evaluate((t: string) => localStorage.setItem('access_token', t), tokData.access_token);
  return tokData.access_token;
}

test.describe('Live Visual Deploy Test: Dual-Browser Math Exam & Side-by-Side Correction', () => {
  test.setTimeout(180_000);

  test('Teacher (Chrome Canary) & Student (Chrome) live Math exam, comfy correction, and side-by-side comparison', async () => {
    // Launch Teacher in Chrome Canary (left half of screen) and Student in Chrome (right half of screen)
    const isCI = Boolean(process.env.CI);
    const slowMo = isCI ? 0 : 550;
    let teacherBrowser;
    try {
      teacherBrowser = await chromium.launch({
        channel: 'chrome-canary',
        headless: isCI,
        slowMo,
        args: ['--window-position=0,0', '--window-size=960,1020'],
      });
    } catch {
      teacherBrowser = await chromium.launch({
        headless: isCI,
        slowMo,
        args: ['--window-position=0,0', '--window-size=960,1020'],
      });
    }

    let studentBrowser;
    try {
      studentBrowser = await chromium.launch({
        channel: 'chrome',
        headless: isCI,
        slowMo,
        args: ['--window-position=960,0', '--window-size=960,1020'],
      });
    } catch {
      studentBrowser = await chromium.launch({
        headless: isCI,
        slowMo,
        args: ['--window-position=960,0', '--window-size=960,1020'],
      });
    }

    try {
      const teacherContext = await teacherBrowser.newContext({ viewport: { width: 920, height: 880 } });
      const studentContext = await studentBrowser.newContext({ viewport: { width: 920, height: 880 } });

      const teacherPage = await teacherContext.newPage();
      const studentPage = await studentContext.newPage();

      const stamp = Date.now();
      const teacherEmail = `teacher_math_${stamp}@school.edu`;
      const studentEmail = `student_math_${stamp}@school.edu`;

      // 1. Authenticate Teacher & Student
      const teacherToken = await registerAndLogin(
        teacherPage,
        teacherEmail,
        'Ms. Ada Lovelace (Math Teacher)',
        'teacher'
      );
      await registerAndLogin(
        studentPage,
        studentEmail,
        'Alex Rivera (Algebra Student)',
        'student'
      );

      // 2. Teacher creates a Math Assessment with 2 questions
      const createExamRes = await teacherPage.request.post(`${API_URL}/exams/`, {
        headers: { Authorization: `Bearer ${teacherToken}` },
        data: {
          title: 'Algebra & Linear Equations Assessment',
          description: 'Solve each equation carefully and show your algebraic steps.',
          duration_minutes: 30,
        },
      });
      expect(createExamRes.status()).toBe(201);
      const exam = await createExamRes.json();
      const examId = exam.id;

      await teacherPage.request.post(`${API_URL}/exams/${examId}/questions`, {
        headers: { Authorization: `Bearer ${teacherToken}` },
        data: {
          question_type: 'multiple_choice',
          text: 'Solve for x:  3x - 7 = 14',
          points: 5,
          options_json: JSON.stringify(['x = 5', 'x = 7', 'x = 9', 'x = 11']),
          correct_answer: 'x = 7',
          rubric: 'Add 7 to both sides (3x = 21), then divide by 3 to get x = 7.',
        },
      });

      await teacherPage.request.post(`${API_URL}/exams/${examId}/questions`, {
        headers: { Authorization: `Bearer ${teacherToken}` },
        data: {
          question_type: 'essay',
          text: 'Solve 2(x + 5) = 24 and show your step-by-step algebraic work.',
          points: 10,
          correct_answer: 'Step 1: 2x + 10 = 24\nStep 2: 2x = 14\nStep 3: x = 7',
          rubric: '5 pts for proper distribution 2x + 10 = 24, 5 pts for solving x = 7.',
        },
      });

      // 3. Teacher opens the Live AI Grading & Proctoring Dashboard (Left Window)
      await teacherPage.goto(`${PORTAL_URL}/teacher-dashboard/${examId}`, { waitUntil: 'domcontentloaded' });
      await expect(teacherPage.locator('h1:has-text("AI Grading Dashboard")')).toBeVisible({ timeout: 15000 });
      await expect(teacherPage.getByTestId('chatgpt-panel')).toBeVisible();

      // 4. Student opens the Math Exam, starts timer, answers MC question (right) and Algebra question (with a mistake), and submits (Right Window)
      await studentPage.goto(`${PORTAL_URL}/exam/${examId}`, { waitUntil: 'domcontentloaded' });
      const startBtn = studentPage.getByRole('button', { name: 'Start Exam', exact: true });
      await expect(startBtn).toBeVisible({ timeout: 15000 });
      await startBtn.click();

      // Answer MC question: x = 7 (Correct)
      const q1Radio = studentPage.locator('input[type="radio"][value="x = 7"]');
      await expect(q1Radio).toBeVisible({ timeout: 10000 });
      await q1Radio.check();

      // Answer Essay Algebra question: Student forgets to multiply 5 by 2 when distributing 2(x + 5)
      const q2Textarea = studentPage.locator('textarea');
      await q2Textarea.fill(
        'Step 1: 2x + 5 = 24 (distributed 2 to x)\nStep 2: 2x = 19\nStep 3: x = 9.5'
      );

      await studentPage.waitForTimeout(1000);

      // Submit the Math Exam
      const submitBtn = studentPage.locator('button:has-text("Submit Exam")').first();
      await submitBtn.click();

      // Verify Student sees the Submitted Review screen awaiting teacher correction
      await expect(studentPage.getByTestId('student-submission-review')).toBeVisible({ timeout: 15000 });
      await expect(studentPage.getByTestId('student-grade-status-badge')).toContainText('Awaiting Teacher Correction');

      // 5. Teacher reloads submissions on the Teacher Dashboard, generates AI grades, and opens the Comfy Correction Modal
      await teacherPage.reload({ waitUntil: 'domcontentloaded' });
      const genBtn = teacherPage.locator('button:has-text("Generate AI Grades")');
      await expect(genBtn).toBeVisible({ timeout: 15000 });
      await genBtn.click();

      const reviewBtn = teacherPage.locator('button:has-text("Review")').first();
      await expect(reviewBtn).toBeVisible({ timeout: 15000 });
      await reviewBtn.click();

      // Verify Comfy Teacher Correction Modal is open
      await expect(teacherPage.getByTestId('teacher-correction-modal')).toBeVisible();

      // Locate the Algebra step-by-step question card in the Teacher Modal
      const algebraTeacherCard = teacherPage.locator('[data-testid^="teacher-question-card-"]', {
        hasText: 'Solve 2(x + 5) = 24',
      });
      await algebraTeacherCard.scrollIntoViewIfNeeded();

      // Teacher clicks "Annotate Student Work", writes a clear step-by-step correction,
      // selects 50% Partial Credit (5/10 pts), and adds constructive feedback
      await algebraTeacherCard.locator('button:has-text("📋 Annotate Student Work")').click();
      await algebraTeacherCard.locator('textarea[data-testid^="teacher-corrected-answer-input-"]').fill(
        'In your Step 1, you wrote "2x + 5 = 24" (forgot to multiply 5 by 2).\n' +
        'Corrected Step 1: 2(x + 5) = 2x + 10 = 24\n' +
        'Corrected Step 2: Subtract 10 from both sides -> 2x = 14\n' +
        'Corrected Step 3: Divide by 2 -> x = 7'
      );

      // Click the "50% Partial" quick score preset on the Algebra question
      await algebraTeacherCard.locator('button:has-text("50% Partial")').click();

      // Click a feedback chip and customize feedback
      await algebraTeacherCard.locator('button:has-text("+ Correct method, minor arithmetic error.")').click();
      await algebraTeacherCard.locator('textarea[data-testid^="teacher-feedback-input-"]').fill(
        'Good algebraic steps after Step 1! Remember to distribute the 2 to BOTH terms inside (x + 5) so 2 * 5 = 10.'
      );

      await teacherPage.waitForTimeout(1500);

      // Save & Approve All Corrections
      await teacherPage.getByTestId('apply-approved-grades-btn').click();
      await expect(teacherPage.locator('text=✓ Approved')).toBeVisible({ timeout: 10000 });

      // 6. Student clicks "Check Teacher Corrections" and compares their Original Answer next to the Teacher's Corrected Version!
      await studentPage.getByTestId('refresh-student-submission-btn').click();
      await expect(studentPage.getByTestId('student-grade-status-badge')).toContainText(
        'Graded & Corrected by Teacher',
        { timeout: 10000 }
      );
      await expect(studentPage.getByTestId('student-final-score')).toContainText('10 / 15 pts (67%)');

      // Locate the Algebra question comparison card on the Student side
      const algebraStudentCard = studentPage.locator('[data-testid^="student-comparison-card-"]', {
        hasText: 'Solve 2(x + 5) = 24',
      });
      await algebraStudentCard.scrollIntoViewIfNeeded();

      await expect(algebraStudentCard).toContainText('Step 1: 2x + 5 = 24');
      await expect(algebraStudentCard).toContainText('Corrected Step 1: 2(x + 5) = 2x + 10 = 24');
      await expect(algebraStudentCard).toContainText('distribute the 2 to BOTH terms');

      // Re-open the Teacher's Correction Modal on the left so both windows show the side-by-side comparison simultaneously
      await teacherPage.locator('button:has-text("Edit Correction")').click();
      await algebraTeacherCard.scrollIntoViewIfNeeded();

      // Pause for 5 seconds so the user can visually inspect both side-by-side windows
      await studentPage.waitForTimeout(5000);
    } finally {
      await teacherBrowser.close();
      await studentBrowser.close();
    }
  });
});

