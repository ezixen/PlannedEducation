# PlannedEducation Deployment Issues Log

**Date:** 2026-10-18
**Environment:** Windows, PowerShell, C:\.venv (Python 3.14.6)
**Deployment Target:** C:\dev\PE

---

## Issues Found During First-Time Deploy Test

### 1. Backend Start Script Fails in PowerShell
**File:** `C:\dev\PE\start_backend.bat`
**Error:** `ParserError: Unexpected token '-m' in expression or statement.`
**Root Cause:** PowerShell doesn't parse `-m` flag correctly when running batch file in PowerShell context.
**Workaround:** Run manually: `C:\.venv\Scripts\python.exe -m uvicorn plannededucation.api.main:app --env-file C:\dev\PE\.env --host 0.0.0.0 --port 8000`

### 2. Frontend Start Script Same Issue
**File:** `C:\dev\PE\start_frontend.bat`
**Error:** Same PowerShell parsing issue with npm command redirection.
**Workaround:** Run manually: `cd C:\dev\PE\web\apps\portal && npm run preview -- --host 127.0.0.1 --port 5173`

### 3. Logs Directory Creation Order
**Issue:** Batch file creates logs directory AFTER attempting to redirect output to it.
**Result:** Log files not created on first run.

### 4. No Health Check / Verification
**Issue:** No automated way to verify services are running after start.
**Impact:** First-time user doesn't know if deploy succeeded.

---

## Uninstaller Test

**Status:** ✅ WORKS COMPLETELY (But check if the folder realy gets removed and no residual files remain.)

**Test:** Ran `uninstall.ps1 -InstallDir C:\dev\PE -AutoConfirm` as Administrator
**Result:** Successfully removed **entire** `C:\dev\PE` directory including:
- All project files
- SQLite database (`plannededucation.db`)
- Logs directory
- Start scripts
- Configuration files
- **The uninstaller script itself** (self-cleaning)

**Verification:** `dir C:\dev\PE` returns "Cannot find path" - directory fully removed.

**Caveats:**
1. Requires Administrator privileges (UAC prompt)
2. `-AutoConfirm` skips dependency review but keeps all external dependencies (Python, Node.js, PostgreSQL, Redis, Docker, Git) - this is by design
3. No scheduled tasks or Windows services were found to remove (clean install)
4. Process cleanup correctly protected the calling shell/agent

**Note:** The uninstaller defaults to `d:\Dev\PEserver` - must specify `-InstallDir C:\dev\PE` for this deployment.

---

## Expected First-Time User Experience (Current Reality)

1. User runs `install.ps1` → Appears successful ✅
2. User double-clicks `start_backend.bat` → Window flashes and closes ❌
3. User double-clicks `start_frontend.bat` → Window flashes and closes ❌
4. User opens browser to http://127.0.0.1:5173 → "Connection refused" ❌
5. User has no logs to diagnose → Stuck ❌

---

## Required Fixes for Production-Ready Deploy

1. Rewrite start scripts as `.ps1` (PowerShell native) or use `cmd /c` wrapper
2. Create logs directory BEFORE any redirection
3. Add health check endpoint verification after startup
4. Add clear success/failure messages to user
5. Consider using `Start-Process` with `-Wait` for proper background process management

---

## Resolutions Applied & Verified ✅ (2026-10-18)

All 5 reported deployment and startup issues have been resolved across both Windows (`install.ps1`, `uninstall.ps1`) and Linux/WSL (`install.sh`, `uninstall.sh`):

1. **Native PowerShell Start Scripts & Resilient Batch Wrappers (`start_backend.ps1` & `start_backend.bat`)**:
   - `start_backend.ps1` runs natively in PowerShell without parser errors or command escaping issues.
   - `start_backend.bat` invokes `start_backend.ps1` via `powershell.exe -ExecutionPolicy Bypass -NoProfile -File "%~dp0start_backend.ps1"`.
   - Removed aggressive `>> logs\backend_stdout.log 2>> logs\backend_stderr.log` suppression so startup output and python error tracebacks are clearly visible on screen.
   - Added `pause` on exit/error so the command prompt window stays open and never flashes and closes on error.

2. **Frontend Start Scripts (`start_frontend.ps1` & `start_frontend.bat`)**:
   - Created native `start_frontend.ps1` and matching `start_frontend.bat` with `pause` on error.
   - Standard console output is preserved with full error reporting.

3. **Unified Single-Click Platform Launcher (`start_all.ps1` & `start_all.bat`)**:
   - Starts both backend and frontend as background processes.
   - Automatically polls the backend health check endpoint (`http://127.0.0.1:<ApiPort>/health`) until healthy.
   - Displays clear status banner with active PIDs and URLs.
   - Opens the browser to the portal once healthy (unless `-NoBrowser` flag is set).
   - Paired with `stop_all.ps1` / `stop_all.bat` to cleanly terminate processes listening on the configured ports.

4. **Dedicated Health & Deployment Verification Tool (`verify.ps1` & `verify.bat`)**:
   - Tests installation directory, `config/deployment.json`, SQLite database file existence, Backend API health (`/health`), Package Engine health (`/packages/health`), and Frontend Portal port connectivity.
   - Reports clear green `[OK]` status for each component and troubleshooting hints for any failures.

5. **Logs Directory Creation Order**:
   - Both installer and all launcher scripts explicitly verify and create the `logs\` directory before any processes start or log files are touched.

6. **Uninstaller Path Auto-Detection (`uninstall.ps1` & `uninstall.sh`)**:
   - `uninstall.ps1` and `uninstall.sh` now automatically detect if they are running inside an installation directory (`$PSScriptRoot` containing `plannededucation.db`, `.env`, or `src/plannededucation`).
   - If detected, defaults to uninstalling that directory without requiring manual `-InstallDir` input.
   - Defaults to standard `C:\PlannedEducation` (Windows) and `/opt/plannededucation` (Linux) matching the installer defaults.