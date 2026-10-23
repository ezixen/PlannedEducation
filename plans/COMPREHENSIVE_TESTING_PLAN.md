# PlannedEducation — Comprehensive Testing Plan

## Overview
This plan covers comprehensive testing of all functions, buttons, pages, roles, languages, and workflows in the PlannedEducation system.

## Testing Phases

### Phase 1: Deployment & Installation
- [ ] Deploy from GitHub using install.ps1 / install.sh
- [ ] Verify fresh installation works
- [ ] Login as superadmin, admin, teacher, student, parent
- [ ] Verify role-based access control

### Phase 2: All Buttons & Functions (Non-Destructive)
- [ ] Test all navigation menu items per role
- [ ] Test all Settings submenu sections
- [ ] Test all exam creation functions
- [ ] Test all test-taking functions
- [ ] Test all chat functions
- [ ] Test all AI grading functions
- [ ] Test all anonymizer functions
- [ ] Test all archive functions
- [ ] Test all notification functions
- [ ] Test all 2FA/passkey functions
- [ ] Test all language switching (28 locales)

### Phase 3: Role-Based Access Control
- [ ] Student: Can only see student-appropriate buttons
- [ ] Teacher: Can see teacher-appropriate buttons
- [ ] Admin: Can see admin-appropriate buttons
- [ ] Superadmin: Can see all buttons including user management
- [ ] Verify unauthorized access is blocked

### Phase 4: i18n / Language Testing
- [ ] Test all 28 languages on every page
- [ ] Verify all strings are translated
- [ ] Verify no hardcoded English text
- [ ] Verify date/time formatting per locale

### Phase 5: Test Creation System
- [ ] Create exam with multiple question types
- [ ] Create dynamic math questions
- [ ] Create essay questions with rubrics
- [ ] Test question bank functionality
- [ ] Test class groupings

### Phase 6: AI Grading & Anonymizer Workflow
- [ ] Submit test with PII in answers
- [ ] Verify Presidio PII scrubbing works
- [ ] Verify AI grading suggestions
- [ ] Verify teacher review/approval workflow
- [ ] Verify sealed archive encryption
- [ ] Verify re-open/re-correct functionality

### Phase 7: Test Module Verification
- [ ] Read all test modules in plans/test-modules/modules/
- [ ] Verify module JSON files are valid
- [ ] Verify module structure matches schema

### Phase 8: Documentation Review
- [ ] Verify docs are available for correct roles
- [ ] Verify FAQ chatbot has correct content per role
- [ ] Update documentation as needed

## Success Criteria
- All buttons work for authorized roles
- All languages display correctly
- No hardcoded English text in UI
- AI grading + anonymizer workflow works end-to-end
- All test modules are valid
- Documentation is role-appropriate
