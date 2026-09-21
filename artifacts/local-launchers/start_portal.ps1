$env:PATH = "C:\Program Files\nodejs;" + $env:PATH
$env:VITE_API_URL="http://localhost:8000"
Set-Location "C:\dev\PlannedEducation\web\apps\portal"
Write-Host "Starting React Portal..." -ForegroundColor Green
& "C:\Program Files\nodejs\npm.cmd" run dev -- --host 127.0.0.1 --port 5173
