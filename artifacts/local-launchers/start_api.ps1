$env:DATABASE_URL="postgresql://postgres:postgres@localhost:5433/plannededucation"
$env:PLANNED_EDUCATION_ENV="development"
$env:ALLOW_DEV_AUTH="true"
$env:JWT_SECRET_KEY="plannededucation-local-development-secret-only"
$env:CORS_ORIGINS="http://localhost:5173"
Set-Location "C:\dev\PlannedEducation"
Write-Host "Starting FastAPI Backend..." -ForegroundColor Green
& "C:\.venv\Scripts\python.exe" -m uvicorn src.plannededucation.api.main:app --reload --host 127.0.0.1 --port 8000
