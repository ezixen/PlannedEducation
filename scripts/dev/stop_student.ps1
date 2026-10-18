#!/usr/bin/env pwsh
<#
.SYNOPSIS
Stop Planned Education local stack: API, Portal, and Chrome Student
#>

Write-Host "Stopping Planned Education Local Stack..." -ForegroundColor Yellow

# Kill Canary
Write-Host "Killing Chrome Student instances..." -ForegroundColor Cyan
Get-WmiObject Win32_Process | Where-Object { $_.CommandLine -match "plannededucation-student-profile" -and $_.Name -match "chrome" } | ForEach-Object {
    Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue
}

# Kill terminals running our launchers
Write-Host "Killing launcher terminals..." -ForegroundColor Cyan
Get-WmiObject Win32_Process | Where-Object { ($_.CommandLine -match "start_api.ps1" -or $_.CommandLine -match "start_portal.ps1") -and $_.Name -match "pwsh" } | ForEach-Object {
    Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue
}

# Kill by port
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

Write-Host "Local stack fully stopped." -ForegroundColor Green
