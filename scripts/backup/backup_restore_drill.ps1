<#>
.SYNOPSIS
    Backup & Restore Drill Script for PlannedEducation (PowerShell/Windows)
.DESCRIPTION
    Runs monthly automated restore drill to staging environment
    Validates RPO < 24h, RTO < 4h
.NOTES
    Requires: PostgreSQL client tools (psql, pg_restore) in PATH
    Run as Administrator for scheduled task registration
#>

param(
    [string]$BackupDir = "D:\Backups\PlannedEducation",
    [string]$StagingDb = "plannededucation_staging",
    [string]$LogFile = "D:\Logs\backup_restore_drill.log",
    [int]$RtoThresholdSeconds = 14400  # 4 hours
)

$ErrorActionPreference = "Stop"

function Write-Log {
    param([string]$Message, [string]$Level = "INFO")
    $timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    $entry = "[$timestamp] [$Level] $Message"
    Add-Content -Path $LogFile -Value $entry
    Write-Host $entry
}

function Write-Success { param([string]$Message) Write-Log $Message "SUCCESS" }
function Write-ErrorLog { param([string]$Message) Write-Log $Message "ERROR" }
function Write-Warn { param([string]$Message) Write-Log $Message "WARN" }

# Start timer
$startTime = Get-Date

Write-Log "=== Starting Monthly Restore Drill ==="
Write-Log "Backup directory: $BackupDir"
Write-Log "Staging database: $StagingDb"

# 1. Find latest backup
$latestBackup = Get-ChildItem -Path $BackupDir -Filter "plannededucation_*.dump" | Sort-Object LastWriteTime -Descending | Select-Object -First 1

if (-not $latestBackup) {
    Write-ErrorLog "No backup files found in $BackupDir"
    exit 1
}

Write-Log "Using backup: $($latestBackup.FullName)"
$backupSizeMB = [math]::Round($latestBackup.Length / 1MB, 2)
Write-Log "Backup size: $backupSizeMB MB"

# 2. Verify backup integrity
Write-Log "Verifying backup integrity..."
try {
    pg_restore --list $latestBackup.FullName | Out-Null
    Write-Success "Backup integrity verified"
} catch {
    Write-ErrorLog "Backup file is corrupted or unreadable: $_"
    exit 1
}

# 3. Check backup age
$backupAgeHours = [math]::Round((Get-Date) - $latestBackup.LastWriteTime).TotalHours, 1
Write-Log "Backup age: $backupAgeHours hours"

if ($backupAgeHours -gt 36) {
    Write-Warn "Backup is $backupAgeHours hours old (exceeds 36h threshold)"
} else {
    Write-Success "Backup age: ${backupAgeHours}h (within RPO)"
}

# 4. Create staging database
Write-Log "Creating staging database: $StagingDb"
psql -U postgres -c "DROP DATABASE IF EXISTS $StagingDb;" *>&1 | Tee-Object -FilePath $LogFile -Append | Out-Null
psql -U postgres -c "CREATE DATABASE $StagingDb;" *>&1 | Tee-Object -FilePath $LogFile -Append | Out-Null
Write-Success "Staging database created"

# 5. Restore to staging
Write-Log "Restoring backup to staging database..."
$restoreStart = Get-Date

try {
    pg_restore `
        --username=postgres `
        --dbname=$StagingDb `
        --clean `
        --if-exists `
        --no-owner `
        --no-privileges `
        $latestBackup.FullName *>&1 | Tee-Object -FilePath $LogFile -Append | Out-Null
    Write-Success "Restore completed"
} catch {
    Write-ErrorLog "Restore failed: $_"
    psql -U postgres -c "DROP DATABASE IF EXISTS $StagingDb;" *>&1 | Out-Null
    exit 1
}

$restoreEnd = Get-Date
$restoreDuration = [math]::Round(($restoreEnd - $restoreStart).TotalSeconds)
Write-Success "Restore completed in ${restoreDuration}s"

# 6. Run migrations (if alembic available)
Write-Log "Running database migrations..."
$appPaths = @("D:\Dev\PlannedEducation", "C:\PlannedEducation", "D:\PlannedEducation")
$alembicFound = $false

foreach ($path in $appPaths) {
    if (Test-Path "$path\alembic.ini") {
        $alembicFound = $true
        $env:DATABASE_URL = "postgresql://postgres:postgres@localhost:5432/$StagingDb"
        Push-Location $path
        alembic upgrade head *>&1 | Tee-Object -FilePath $LogFile -Append | Out-Null
        Pop-Location
        Write-Success "Migrations applied"
        break
    }
}

if (-not $alembicFound) {
    Write-Warn "No alembic.ini found, skipping migrations"
}

# 7. Data integrity checks
Write-Log "Running data integrity checks..."

$criticalTables = @("users", "exams", "questions", "exam_submissions", "account_relationships")
foreach ($table in $criticalTables) {
    $count = psql -U postgres -d $StagingDb -t -c "SELECT COUNT(*) FROM $table;" 2>$null | ForEach-Object { $_.Trim() }
    if ($null -ne $count -and $count -match '^\d+$') {
        Write-Success "Table '$table': $count rows"
    } else {
        Write-ErrorLog "Table '$table' check failed or empty"
    }
}

# 8. Smoke tests
Write-Log "Running smoke tests..."
$smokeTests = @(
    "SELECT COUNT(*) FROM users WHERE is_active = true;",
    "SELECT COUNT(*) FROM exams;",
    "SELECT COUNT(*) FROM exam_submissions;"
)

foreach ($testSql in $smokeTests) {
    $result = psql -U postgres -d $StagingDb -t -c $testSql 2>$null | ForEach-Object { $_.Trim() }
    Write-Log "  $testSql => $result"
}

# 9. Cleanup staging database
Write-Log "Cleaning up staging database..."
psql -U postgres -c "DROP DATABASE IF EXISTS $StagingDb;" *>&1 | Tee-Object -FilePath $LogFile -Append | Out-Null
Write-Success "Staging database dropped"

# 10. Calculate total duration
$endTime = Get-Date
$totalDuration = [math]::Round(($endTime - $startTime).TotalSeconds)

Write-Log "=== Restore Drill Completed ==="
Write-Log "Total duration: ${totalDuration}s ($([math]::Floor($totalDuration/60))m $($totalDuration%60)s)"
Write-Log "Restore duration: ${restoreDuration}s"

# Check RTO compliance
if ($totalDuration -le $RtoThresholdSeconds) {
    Write-Success "RTO CHECK PASSED: ${totalDuration}s <= ${RtoThresholdSeconds}s (4h)"
    $rtoStatus = "PASSED"
} else {
    Write-ErrorLog "RTO CHECK FAILED: ${totalDuration}s > ${RtoThresholdSeconds}s (4h)"
    $rtoStatus = "FAILED"
}

# Check RPO compliance
if ($backupAgeHours -le 24) {
    Write-Success "RPO CHECK PASSED: ${backupAgeHours}h <= 24h"
    $rpoStatus = "PASSED"
} else {
    Write-ErrorLog "RPO CHECK FAILED: ${backupAgeHours}h > 24h"
    $rpoStatus = "FAILED"
}

# Summary
Write-Log ""
Write-Log "=== DRILL SUMMARY ==="
Write-Log "RPO Status: $rpoStatus (Backup age: ${backupAgeHours}h)"
Write-Log "RTO Status: $rtoStatus (Total time: ${totalDuration}s)"
Write-Log "Backup file: $($latestBackup.Name)"
Write-Log "Backup size: $backupSizeMB MB"
Write-Log "Restore time: ${restoreDuration}s"

# Exit with appropriate code
if ($rtoStatus -eq "PASSED" -and $rpoStatus -eq "PASSED") {
    Write-Success "DRILL PASSED"
    exit 0
} else {
    Write-ErrorLog "DRILL FAILED"
    exit 1
}