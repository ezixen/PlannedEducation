# scripts/local/stop.ps1

Write-Host "Stopping PlannedEducation Local Environment..." -ForegroundColor Yellow

function Kill-ProcessByPort {
    param([int]$Port)
    $connections = netstat -ano | findstr ":$Port"
    if ($connections) {
        $connections -split "`n" | ForEach-Object {
            $line = $_.Trim() -replace '\s+', ' '
            if ($line) {
                $pidStr = ($line -split ' ')[4]
                if ($pidStr -match '^\d+$' -and $pidStr -ne "0") {
                    Write-Host "Killing process $pidStr on port $Port..." -ForegroundColor Cyan
                    taskkill /F /PID $pidStr 2>$null
                }
            }
        }
    }
}

Kill-ProcessByPort 8000
Kill-ProcessByPort 5173

Write-Host "All processes stopped." -ForegroundColor Green
