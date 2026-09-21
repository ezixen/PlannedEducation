# scripts/local/start.ps1

Write-Host "Starting PlannedEducation Local Environment..." -ForegroundColor Green

# 1. Install Backend Dependencies
Write-Host "Verifying Python dependencies..." -ForegroundColor Cyan
& "C:/.venv/Scripts/python.exe" -m pip install -r src/requirements.txt -q

# 2. Install Frontend Dependencies
Write-Host "Verifying Node.js dependencies..." -ForegroundColor Cyan
Set-Location -Path "web/apps/portal"
if (-not (Test-Path "node_modules")) {
    & npm install
}
Set-Location -Path "../../.."

# 3. Start the Backend API (using SQLite for local dev so we don't need Postgres installed)
Write-Host "Starting FastAPI Backend on port 8000..." -ForegroundColor Cyan
$env:DATABASE_URL="sqlite:///./plannededucation.db"
Start-Process -FilePath "C:/.venv/Scripts/python.exe" -ArgumentList "-m", "uvicorn", "src.plannededucation.api.main:app", "--reload", "--port", "8000" -NoNewWindow -PassThru -RedirectStandardOutput "scripts/local/backend.log" -RedirectStandardError "scripts/local/backend_error.log"

# 4. Start the React Frontend
Write-Host "Starting React Portal on port 5173..." -ForegroundColor Cyan
Set-Location -Path "web/apps/portal"
Start-Process -FilePath "npm.cmd" -ArgumentList "run", "dev" -NoNewWindow -PassThru -RedirectStandardOutput "../../../scripts/local/frontend.log" -RedirectStandardError "../../../scripts/local/frontend_error.log"
Set-Location -Path "../../.."

Write-Host "Local environment started successfully!" -ForegroundColor Green
Write-Host "Backend API: http://localhost:8000/docs"
Write-Host "Frontend Portal: http://localhost:5173"
Write-Host "Check scripts/local/ for logs. Run 'stop.ps1' to kill the processes."

