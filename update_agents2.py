with open('d:/Dev/PlannedEducation/AGENTS.md', 'r', encoding='utf-8') as f:
    content = f.read()

idx = content.find('## 6. Testing')
end_idx = content.find('## 7. Documentation')
old_section = content[idx:end_idx]

new_section = """## 6. Testing & Verification System (MANDATORY)

- **Python interpreter**: Always invoke via `C:/.venv/Scripts/python.exe`.
- **Source-Aware Pytest Cache Helper (`scripts/testing/update_test_cache.py`)**:
  - **MANDATORY FOR EVERY PYTEST RUN**: Every python test invocation MUST run through `scripts/testing/update_test_cache.py`.
  - **No Pointless Retests**: Uses `--skip-if-clean` to skip re-running tests for unmodified suites when the source files and dependencies haven't changed since the last clean test run.
  - Maintains run history, git state, and SHA-256 source file signatures in `artifacts/test_cache/source_test_results.json`.
  - **Standard Invocations**:
    ```powershell
    # Run full test suite with change tracking:
    C:/.venv/Scripts/python.exe scripts/testing/update_test_cache.py --skip-if-clean --suite-name "backend-all" -- C:/.venv/Scripts/python.exe -m pytest tests/ -q

    # Run focused tests with change tracking:
    C:/.venv/Scripts/python.exe scripts/testing/update_test_cache.py --skip-if-clean --suite-name "backend-auth" -- C:/.venv/Scripts/python.exe -m pytest tests/test_auth.py -q

    # Check cache status without running tests:
    C:/.venv/Scripts/python.exe scripts/testing/update_test_cache.py --status --suite-name "backend-all"
    ```
- **Pytest Configuration (`pytest.ini`)**:
  - Logging enabled by default: `log_cli = true`, `log_cli_level = INFO`
  - Log file output to `artifacts/test_run.log` with DEBUG level
  - Test markers for categorization (tracked, slow, integration, unit, ui, auth, exam, ai, proctoring, chat, ocr, stt, archive, anonymizer, parent, admin, chatgpt)
  - Filterwarnings to suppress known deprecation warnings
- **Logged Testing Enforcement (MANDATORY)**:
  - **ALWAYS** use `scripts/testing/update_test_cache.py --skip-if-clean` wrapper for pytest runs
  - **NEVER** run raw `pytest` directly -- always wrap with the cache helper
  - Check cache status first: `scripts/testing/update_test_cache.py --status --suite-name "backend-all"`
  - If suite is clean, tests are skipped automatically -- no wasted time
  - After changes, only affected suites re-run based on SHA-256 source file signatures
  - Cache stores: run history, git state, SHA-256 source file signatures in `artifacts/test_cache/source_test_results.json`
- **Test Tracker Logger (`run_tests.py` / `test_tracker.py` / `conftest_tracker.py`)**:
  - Project test runner integrating incremental test skipping with summary reporting:
    ```powershell
    C:/.venv/Scripts/python.exe run_tests.py --summary
    ```
- **Visual Testing & Artifact Cleanup Rule**:
  - All visual testing workflows (Playwright, visual regression tests) must automatically clean up temporary files, screenshots, traces, and test databases (`test-results/`, `playwright-report/`, `artifacts/visual-test-screenshots/`, `test_visual.db`) via `globalTeardown` and cleanup scripts after runs are complete and all issues are fixed, preserving a clean workspace.
- **Never claim "done"** without stating what was run and the observed result.

---"""

if old_section in content:
    content = content.replace(old_section, new_section)
    with open('d:/Dev/PlannedEducation/AGENTS.md', 'w', encoding='utf-8') as f:
        f.write(content)
    print('SUCCESS: Section replaced')
else:
    print('FAILED: Old section not found')
    print('Old section starts with:', repr(old_section[:50]))
    print('Old section ends with:', repr(old_section[-30:]))