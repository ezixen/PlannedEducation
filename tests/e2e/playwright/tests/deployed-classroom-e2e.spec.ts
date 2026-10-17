import { test, expect } from '@playwright/test';

const API_URL = process.env.API_URL || 'http://127.0.0.1:8000';
const PORTAL_URL = process.env.PORTAL_URL || 'http://127.0.0.1:5173';

async function assertNoHorizontalOverflow(page: any) {
  const hasOverflow = await page.evaluate(() => {
    const docWidth = document.documentElement.clientWidth;
    return (
      document.documentElement.scrollWidth > docWidth + 4 ||
      document.body.scrollWidth > docWidth + 4
    );
  });
  expect(hasOverflow).toBe(false);
}

async function registerUserAndLoginUI(
  page: any,
  email: string,
  fullName: string,
  role: 'teacher' | 'student' | 'parent',
  password = 'StrongPassword123!'
): Promise<{ token: string; userId: string }> {
  const username = email.split('@')[0].replace(/[^a-zA-Z0-9_]/g, '_');

  const regRes = await page.request.post(`${API_URL}/auth/register`, {
    data: {
      email,
      username,
      password,
      full_name: fullName,
      role,
    },
  });
  expect([200, 201, 400, 409]).toContain(regRes.status());

  const tokRes = await page.request.post(`${API_URL}/auth/token`, {
    form: { username: email, password },
  });
  expect(tokRes.ok()).toBeTruthy();
  const tokData = await tokRes.json();

  const meRes = await page.request.get(`${API_URL}/auth/me`, {
    headers: { Authorization: `Bearer ${tokData.access_token}` },
  });
  expect(meRes.ok()).toBeTruthy();
  const meData = await meRes.json();

  await page.goto(`${PORTAL_URL}/login`, { waitUntil: 'domcontentloaded' });
  await page.evaluate(
    (t: string) => localStorage.setItem('access_token', t),
    tokData.access_token
  );
  await page.goto(`${PORTAL_URL}/`, { waitUntil: 'domcontentloaded' });
  await expect(page.locator(`text=${fullName}`)).toBeVisible({ timeout: 15000 });

  return { token: tokData.access_token, userId: meData.id };
}

test.describe('Deployed Platform Full Classroom E2E Verification (Admin, Teacher, Class of Students, Parents)', () => {
  test.setTimeout(180_000);

  test('End-to-End School Simulation: Admin -> Teacher -> Class of 3 Students -> Teacher Grading -> Student Review -> Parent Portal', async ({ browser }) => {
    const stamp = Date.now();

    // Create isolated browser contexts for each role to simulate simultaneous connections to the deployed server
    const ctxOpts = { viewport: { width: 1280, height: 860 }, serviceWorkers: 'block' as const };
    const adminContext = await browser.newContext(ctxOpts);
    const teacherContext = await browser.newContext(ctxOpts);
    const student1Context = await browser.newContext(ctxOpts);
    const student2Context = await browser.newContext(ctxOpts);
    const student3Context = await browser.newContext(ctxOpts);
    const parent1Context = await browser.newContext(ctxOpts);
    const parent2Context = await browser.newContext(ctxOpts);

    try {
      const adminPage = await adminContext.newPage();
      const teacherPage = await teacherContext.newPage();
      const student1Page = await student1Context.newPage();
      const student2Page = await student2Context.newPage();
      const student3Page = await student3Context.newPage();
      const parent1Page = await parent1Context.newPage();
      const parent2Page = await parent2Context.newPage();

      // =========================================================================
      // 1. SCHOOL ADMIN: Log in via UI using installer-created Admin account
      // =========================================================================
      await adminPage.goto(`${PORTAL_URL}/login`, { waitUntil: 'domcontentloaded' });
      await adminPage.fill('input[type="email"], input[name="email"]', 'admin@yourschool.edu');
      await adminPage.fill('input[type="password"], input[name="password"]', 'AdminPassword123!');
      await adminPage.click('button[type="submit"]');
      await adminPage.waitForURL(`${PORTAL_URL}/`, { timeout: 15000 });
      await expect(adminPage.locator('h1:has-text("Welcome, School Administrator")')).toBeVisible({ timeout: 10000 });
      await assertNoHorizontalOverflow(adminPage);

      // Navigate to Admin Dashboard via the Dashboard card
      await adminPage.click('button:has-text("Open Admin Dashboard")');
      await expect(adminPage.locator('h1:has-text("Teacher Admin Dashboard")')).toBeVisible({ timeout: 10000 });
      await assertNoHorizontalOverflow(adminPage);

      // =========================================================================
      // 2. TEACHER: Register, Log in, Create Class Group & Create Classroom Exam
      // =========================================================================
      const teacherInfo = await registerUserAndLoginUI(
        teacherPage,
        `teacher_${stamp}@school.edu`,
        'Dr. Alan Turing',
        'teacher'
      );

      // Teacher creates a new class in Class Groupings (/teacher-classes)
      await teacherPage.goto(`${PORTAL_URL}/teacher-classes`, { waitUntil: 'domcontentloaded' });
      await expect(teacherPage.locator('h1:has-text("Class Groupings")')).toBeVisible({ timeout: 10000 });
      await teacherPage.fill('input[placeholder*="Biology 101"]', 'Honors Mathematics & Logic - Section A');
      await teacherPage.click('button:has-text("Create")');
      await expect(teacherPage.locator('h3:has-text("Honors Mathematics & Logic - Section A")')).toBeVisible();
      await assertNoHorizontalOverflow(teacherPage);

      // Teacher creates the Midterm Exam with Multiple Choice + Step-by-Step Algebra Essay
      const createExamRes = await teacherPage.request.post(`${API_URL}/exams/`, {
        headers: { Authorization: `Bearer ${teacherInfo.token}` },
        data: {
          title: 'Midterm Mathematics & Logic Exam',
          description: 'Complete both questions and show your full algebraic reasoning.',
          duration_minutes: 45,
        },
      });
      expect(createExamRes.status()).toBe(201);
      const exam = await createExamRes.json();
      const examId = exam.id;

      await teacherPage.request.post(`${API_URL}/exams/${examId}/questions`, {
        headers: { Authorization: `Bearer ${teacherInfo.token}` },
        data: {
          question_type: 'multiple_choice',
          text: 'Solve for x: 4x - 8 = 20',
          points: 5,
          options_json: JSON.stringify(['x = 5', 'x = 7', 'x = 8', 'x = 9']),
          correct_answer: 'x = 7',
          rubric: 'Add 8 to both sides (4x = 28), then divide by 4 to get x = 7.',
        },
      });

      await teacherPage.request.post(`${API_URL}/exams/${examId}/questions`, {
        headers: { Authorization: `Bearer ${teacherInfo.token}` },
        data: {
          question_type: 'essay',
          text: 'Solve 3(x + 4) = 27 and show all algebraic steps.',
          points: 10,
          correct_answer: 'Step 1: 3x + 12 = 27\nStep 2: 3x = 15\nStep 3: x = 5',
          rubric: '5 pts for distributing 3(x + 4) = 3x + 12, 5 pts for solving x = 5.',
        },
      });

      // Teacher opens the Exam Editor & Live AI Grading Dashboard
      await teacherPage.goto(`${PORTAL_URL}/teacher-dashboard/${examId}`, { waitUntil: 'domcontentloaded' });
      await expect(teacherPage.locator('h1:has-text("AI Grading Dashboard")')).toBeVisible({ timeout: 15000 });
      await assertNoHorizontalOverflow(teacherPage);

      // =========================================================================
      // 3. CLASS OF 3 STUDENTS: Register, Log in, Take & Submit the Exam
      // =========================================================================
      const student1Info = await registerUserAndLoginUI(
        student1Page,
        `alex_rivera_${stamp}@school.edu`,
        'Alex Rivera',
        'student'
      );
      const student2Info = await registerUserAndLoginUI(
        student2Page,
        `maya_lin_${stamp}@school.edu`,
        'Maya Lin',
        'student'
      );
      const student3Info = await registerUserAndLoginUI(
        student3Page,
        `liam_oconnor_${stamp}@school.edu`,
        'Liam OConnor',
        'student'
      );

      // Helper for a student to take and submit the exam
      async function takeAndSubmitExam(page: any, mcAnswer: string, essayAnswer: string) {
        await page.goto(`${PORTAL_URL}/exam/${examId}`, { waitUntil: 'domcontentloaded' });
        const startBtn = page.getByRole('button', { name: 'Start Exam', exact: true });
        await expect(startBtn).toBeVisible({ timeout: 15000 });
        await startBtn.click();

        const radio = page.locator(`input[type="radio"][value="${mcAnswer}"]`);
        await expect(radio).toBeVisible({ timeout: 10000 });
        await radio.check();

        const textarea = page.locator('textarea');
        await textarea.fill(essayAnswer);

        const submitBtn = page.locator('button:has-text("Submit Exam")').first();
        await submitBtn.click();

        await expect(page.getByTestId('student-submission-review')).toBeVisible({ timeout: 15000 });
        await expect(page.getByTestId('student-grade-status-badge')).toContainText('Awaiting Teacher Correction');
        await assertNoHorizontalOverflow(page);
      }

      // Student 1 (Alex Rivera): Answers both questions accurately
      await takeAndSubmitExam(
        student1Page,
        'x = 7',
        'Step 1: Distribute 3 -> 3x + 12 = 27\nStep 2: Subtract 12 -> 3x = 15\nStep 3: Divide by 3 -> x = 5'
      );

      // Student 2 (Maya Lin): Gets MC right, makes distribution mistake on Essay
      await takeAndSubmitExam(
        student2Page,
        'x = 7',
        'Step 1: 3x + 4 = 27 (forgot to multiply 4 by 3)\nStep 2: 3x = 23\nStep 3: x = 7.67'
      );

      // Student 3 (Liam OConnor): Gets MC wrong, Essay right
      await takeAndSubmitExam(
        student3Page,
        'x = 5',
        'Step 1: 3x + 12 = 27\nStep 2: 3x = 15\nStep 3: x = 5'
      );

      // =========================================================================
      // 4. TEACHER: Grade & Correct All 3 Submissions in the Class
      // =========================================================================
      await teacherPage.goto(`${PORTAL_URL}/teacher-dashboard/${examId}`, { waitUntil: 'domcontentloaded' });
      const genBtns = teacherPage.locator('button:has-text("Generate AI Grades")');
      await expect(genBtns).toHaveCount(3, { timeout: 15000 });
      for (let i = 0; i < 3; i++) {
        await genBtns.first().click();
        await expect(genBtns).toHaveCount(2 - i, { timeout: 10000 });
      }

      const reviewBtns = teacherPage.locator('button:has-text("Review")');
      await expect(reviewBtns).toHaveCount(3, { timeout: 15000 });

      // Review each of the 3 submissions (each approval turns 'Review' into 'Edit Correction', so always click .first())
      for (let i = 0; i < 3; i++) {
        await reviewBtns.first().click();
        const modal = teacherPage.getByTestId('teacher-correction-modal');
        await expect(modal).toBeVisible({ timeout: 10000 });

        const modalText = await modal.textContent();
        const algebraCard = teacherPage.locator('[data-testid^="teacher-question-card-"]', {
          hasText: 'Solve 3(x + 4) = 27',
        });
        await algebraCard.scrollIntoViewIfNeeded();

        if (modalText?.includes('3x + 4 = 27')) {
          // Maya Lin's submission: annotate mistake, give 50% partial credit (5/10) + constructive feedback
          await algebraCard.locator('button:has-text("📋 Annotate Student Work")').click();
          await algebraCard.locator('textarea[data-testid^="teacher-corrected-answer-input-"]').fill(
            'In Step 1 you wrote 3x + 4 = 27.\nCorrected Step 1: 3(x + 4) = 3x + 12 = 27\nCorrected Step 2: 3x = 15\nCorrected Step 3: x = 5'
          );
          await algebraCard.locator('button:has-text("50% Partial")').click();
          await algebraCard.locator('textarea[data-testid^="teacher-feedback-input-"]').fill(
            'Great setup! Remember to distribute the 3 to both x and 4 inside the parentheses (3 * 4 = 12).'
          );
        } else {
          // Alex Rivera & Liam OConnor got the algebra essay completely right (100% Full = 10/10)
          await algebraCard.locator('button:has-text("100% Full")').click();
          await algebraCard.locator('textarea[data-testid^="teacher-feedback-input-"]').fill(
            'Excellent step-by-step algebraic solution!'
          );
        }

        await teacherPage.getByTestId('apply-approved-grades-btn').click();
        await expect(modal).toBeHidden({ timeout: 10000 });
        await expect(teacherPage.locator('text=✓ Approved')).toHaveCount(i + 1, { timeout: 10000 });
      }

      // =========================================================================
      // 5. STUDENTS: Verify What Each Student Sees After Teacher Approval
      // =========================================================================
      // Student 1 (Alex Rivera): 15 / 15 pts (100%)
      await student1Page.getByTestId('refresh-student-submission-btn').click();
      await expect(student1Page.getByTestId('student-grade-status-badge')).toContainText(
        'Graded & Corrected by Teacher',
        { timeout: 10000 }
      );
      await expect(student1Page.getByTestId('student-final-score')).toContainText('15 / 15 pts (100%)');

      // Student 2 (Maya Lin): 10 / 15 pts (67%) with side-by-side Teacher Corrected Version
      await student2Page.getByTestId('refresh-student-submission-btn').click();
      await expect(student2Page.getByTestId('student-grade-status-badge')).toContainText(
        'Graded & Corrected by Teacher',
        { timeout: 10000 }
      );
      await expect(student2Page.getByTestId('student-final-score')).toContainText('10 / 15 pts (67%)');
      const mayaComparisonCard = student2Page.locator('[data-testid^="student-comparison-card-"]', {
        hasText: 'Solve 3(x + 4) = 27',
      });
      await expect(mayaComparisonCard).toContainText('Step 1: 3x + 4 = 27');
      await expect(mayaComparisonCard).toContainText('Corrected Step 1: 3(x + 4) = 3x + 12 = 27');
      await expect(mayaComparisonCard).toContainText('Remember to distribute the 3 to both x and 4');
      await assertNoHorizontalOverflow(student2Page);

      // Student 3 (Liam OConnor): 10 / 15 pts (67%)
      await student3Page.getByTestId('refresh-student-submission-btn').click();
      await expect(student3Page.getByTestId('student-grade-status-badge')).toContainText(
        'Graded & Corrected by Teacher',
        { timeout: 10000 }
      );
      await expect(student3Page.getByTestId('student-final-score')).toContainText('10 / 15 pts (67%)');

      // =========================================================================
      // 6. PARENTS: Link to Students (3-Way Handshake) & View Parent Portal
      // =========================================================================
      const parent1Info = await registerUserAndLoginUI(
        parent1Page,
        `elena_rivera_${stamp}@family.org`,
        'Elena Rivera',
        'parent'
      );
      const parent2Info = await registerUserAndLoginUI(
        parent2Page,
        `david_lin_${stamp}@family.org`,
        'David Lin',
        'parent'
      );

      // Helper to establish 3-way verified relationship (Parent -> Student -> Teacher)
      async function linkParentToStudent(parentToken: string, studentToken: string, studentId: string) {
        const reqRes = await parent1Page.request.post(`${API_URL}/parents/relationships/request`, {
          headers: { Authorization: `Bearer ${parentToken}` },
          data: { student_id: studentId, teacher_id: teacherInfo.userId },
        });
        expect(reqRes.status()).toBe(201);
        const rel = await reqRes.json();

        // Student approves
        const stuApprove = await parent1Page.request.post(`${API_URL}/parents/relationships/${rel.id}/approve`, {
          headers: { Authorization: `Bearer ${studentToken}` },
        });
        expect(stuApprove.ok()).toBeTruthy();

        // Teacher approves -> becomes 'active'
        const tchApprove = await parent1Page.request.post(`${API_URL}/parents/relationships/${rel.id}/approve`, {
          headers: { Authorization: `Bearer ${teacherInfo.token}` },
        });
        expect(tchApprove.ok()).toBeTruthy();
        const tchData = await tchApprove.json();
        expect(tchData.status).toBe('active');
      }

      await linkParentToStudent(parent1Info.token, student1Info.token, student1Info.userId);
      await linkParentToStudent(parent2Info.token, student2Info.token, student2Info.userId);

      // Parent 1 (Elena Rivera) visits /parent-dashboard and sees Alex Rivera's exam score & feedback
      await parent1Page.goto(`${PORTAL_URL}/parent-dashboard`, { waitUntil: 'domcontentloaded' });
      await expect(parent1Page.locator('h1:has-text("Parent Portal")')).toBeVisible({ timeout: 10000 });
      await expect(parent1Page.locator('h2:has-text("Alex Rivera")')).toBeVisible({ timeout: 10000 });
      await expect(parent1Page.locator('h3:has-text("Midterm Mathematics & Logic Exam")')).toBeVisible();
      await expect(parent1Page.locator('text=100%')).toBeVisible();
      await expect(parent1Page.locator('text=Excellent step-by-step algebraic solution!')).toBeVisible();
      await assertNoHorizontalOverflow(parent1Page);

      // Parent 2 (David Lin) visits /parent-dashboard and sees Maya Lin's exam score & constructive feedback
      await parent2Page.goto(`${PORTAL_URL}/parent-dashboard`, { waitUntil: 'domcontentloaded' });
      await expect(parent2Page.locator('h1:has-text("Parent Portal")')).toBeVisible({ timeout: 10000 });
      await expect(parent2Page.locator('h2:has-text("Maya Lin")')).toBeVisible({ timeout: 10000 });
      await expect(parent2Page.locator('h3:has-text("Midterm Mathematics & Logic Exam")')).toBeVisible();
      await expect(parent2Page.locator('text=67%')).toBeVisible();
      await expect(parent2Page.locator('text=Remember to distribute the 3 to both x and 4')).toBeVisible();
      await assertNoHorizontalOverflow(parent2Page);

      // =========================================================================
      // 7. SCHOOL ADMIN: Inspect Users & Perform Direct Password Reset (No Email Needed)
      // =========================================================================
      await adminPage.reload({ waitUntil: 'domcontentloaded' });
      await adminPage.click('button:has-text("Users")');
      const liamEmail = `liam_oconnor_${stamp}@school.edu`;
      await expect(adminPage.locator('tr', { hasText: liamEmail })).toBeVisible({ timeout: 10000 });

      const liamRow = adminPage.locator('tr', { hasText: liamEmail });
      await liamRow.locator('button:has-text("Reset Password")').click();

      await expect(adminPage.locator('h3:has-text("Direct Password Reset")')).toBeVisible({ timeout: 10000 });
      await adminPage.click('button:has-text("Confirm Reset")');

      await expect(adminPage.locator('h3:has-text("Password Reset Successful")')).toBeVisible({ timeout: 10000 });
      const tempPassCode = adminPage.locator('code').filter({ hasText: 'TempPass#' }).first();
      await expect(tempPassCode).toBeVisible({ timeout: 10000 });
      const newTempPassword = (await tempPassCode.textContent())?.trim() || '';
      expect(newTempPassword.length).toBeGreaterThanOrEqual(8);

      // Verify Liam OConnor can immediately authenticate with the Admin-generated temporary password
      const verifyResetLogin = await adminPage.request.post(`${API_URL}/auth/token`, {
        form: { username: `liam_oconnor_${stamp}@school.edu`, password: newTempPassword },
      });
      expect(verifyResetLogin.ok()).toBeTruthy();
    } finally {
      await adminContext.close();
      await teacherContext.close();
      await student1Context.close();
      await student2Context.close();
      await student3Context.close();
      await parent1Context.close();
      await parent2Context.close();
    }
  });
});
