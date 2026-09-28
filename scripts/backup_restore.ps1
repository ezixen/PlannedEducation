<# 
.SYNOPSIS
    Backup/Restore Scripts for PlannedEducation - Free/Open-Source Only
    Uses pg_dump/pg_restore for PostgreSQL, sqlite3 for SQLite
    NO PAID SERVICES

.DESCRIPTION
    Provides backup and restore functionality for both PostgreSQL and SQLite databases.
    Supports automated backups with retention policies.

.PARAMETER Command
    backup | restore | list | cleanup

.PARAMETER BackupFile
    Path to backup file (required for restore)

.PARAMETER BackupDir
    Directory to store backups (default: ./backups)

.PARAMETER RetentionDays
    Days to retain backups (default: 30)

.EXAMPLE
    .\backup_restore.ps1 backup
    .\backup_restore.ps1 restore .\backups\plannededucation_pg_20260928_120000.sql.gz
    .\backup_restore.ps1 list
    .\backup_restore.ps1 cleanup
#>

param(
    [Parameter(Mandatory=$true, Position=0)]
    [ValidateSet('backup', 'restore', 'list', 'cleanup')]
    [string]$Command,

    [Parameter(Position=1)]
    [string]$BackupFile,

    [string]$BackupDir = ".\backups",

    [int]$RetentionDays = 30
)

$ErrorActionPreference = "Stop"

function Write-LogInfo { param([string]$Message) Write-Host "[INFO] $Message" -ForegroundColor Green }
function Write-LogWarn { param([string]$Message) Write-Host "[WARN] $Message" -ForegroundColor Yellow }
function Write-LogError { param([string]$Message) Write-Host "[ERROR] $Message" -ForegroundColor Red }

# Create backup directory
if (-not (Test-Path $BackupDir)) {
    New-Item -ItemType Directory -Path $BackupDir | Out-Null
}

$Timestamp = Get-Date -Format "yyyyMMdd_HHmmss"
$DatabaseUrl = $env:DATABASE_URL

function Get-DbType {
    param([string]$Url)
    if ($Url -like "postgresql*") { return "postgresql" }
    if ($Url -like "sqlite*") { return "sqlite" }
    return "unknown"
}

function Backup-PostgreSQL {
    param([string]$DbUrl, [string]$BackupFile)
    
    Write-LogInfo "Backing up PostgreSQL database..."
    
    # Parse postgresql://user:pass@host:port/dbname
    if ($DbUrl -match 'postgresql://([^:]+):([^@]+)@([^:]+):(\d+)/(.+)') {
        $user = $matches[1]
        $pass = $matches[2]
        $host = $matches[3]
        $port = $matches[4]
        $dbname = $matches[5]
        
        $env:PGPASSWORD = $pass
        $cmd = "pg_dump -h $host -p $port -U $user -d $dbname --no-owner --no-privileges --clean --if-exists | gzip > $BackupFile"
        Invoke-Expression $cmd
        
        if ($LASTEXITCODE -eq 0) {
            Write-LogInfo "PostgreSQL backup saved to: $BackupFile"
            return $BackupFile
        } else {
            Write-LogError "PostgreSQL backup failed"
            exit 1
        }
    } else {
        Write-LogError "Could not parse PostgreSQL URL"
        exit 1
    }
}

function Backup-SQLite {
    param([string]$DbUrl, [string]$BackupFile)
    
    Write-LogInfo "Backing up SQLite database..."
    
    $dbPath = $DbUrl -replace '^sqlite:///', '' -replace '^sqlite://', ''
    
    if (Test-Path $dbPath) {
        $cmd = "sqlite3 $dbPath .dump | gzip > $BackupFile"
        Invoke-Expression $cmd
        
        if ($LASTEXITCODE -eq 0) {
            Write-LogInfo "SQLite backup saved to: $BackupFile"
            return $BackupFile
        } else {
            Write-LogError "SQLite backup failed"
            exit 1
        }
    } else {
        Write-LogError "SQLite database file not found: $dbPath"
        exit 1
    }
}

function Restore-PostgreSQL {
    param([string]$DbUrl, [string]$BackupFile)
    
    Write-LogInfo "Restoring PostgreSQL database from: $BackupFile"
    
    if (-not (Test-Path $BackupFile)) {
        Write-LogError "Backup file not found: $BackupFile"
        exit 1
    }
    
    if ($DbUrl -match 'postgresql://([^:]+):([^@]+)@([^:]+):(\d+)/(.+)') {
        $user = $matches[1]
        $pass = $matches[2]
        $host = $matches[3]
        $port = $matches[4]
        $dbname = $matches[5]
        
        Write-LogWarn "This will REPLACE the database '$dbname'. Continue? (y/N)"
        $confirm = Read-Host
        if ($confirm -notmatch '^[yY]$') {
            Write-LogInfo "Restore cancelled"
            return
        }
        
        $env:PGPASSWORD = $pass
        $cmd = "gunzip -c $BackupFile | psql -h $host -p $port -U $user -d $dbname"
        Invoke-Expression $cmd
        
        if ($LASTEXITCODE -eq 0) {
            Write-LogInfo "PostgreSQL restore completed successfully"
        } else {
            Write-LogError "PostgreSQL restore failed"
            exit 1
        }
    } else {
        Write-LogError "Could not parse PostgreSQL URL"
        exit 1
    }
}

function Restore-SQLite {
    param([string]$DbUrl, [string]$BackupFile)
    
    Write-LogInfo "Restoring SQLite database from: $BackupFile"
    
    if (-not (Test-Path $BackupFile)) {
        Write-LogError "Backup file not found: $BackupFile"
        exit 1
    }
    
    $dbPath = $DbUrl -replace '^sqlite:///', '' -replace '^sqlite://', ''
    
    Write-LogWarn "This will REPLACE the database '$dbPath'. Continue? (y/N)"
    $confirm = Read-Host
    if ($confirm -notmatch '^[yY]$') {
        Write-LogInfo "Restore cancelled"
        return
    }
    
    # Backup current database first
    if (Test-Path $dbPath) {
        $preRestore = "${dbPath}.pre_restore_$Timestamp"
        Copy-Item $dbPath $preRestore
        Write-LogInfo "Current database backed up to: $preRestore"
    }
    
    $cmd = "gunzip -c $BackupFile | sqlite3 $dbPath"
    Invoke-Expression $cmd
    
    if ($LASTEXITCODE -eq 0) {
        Write-LogInfo "SQLite restore completed successfully"
    } else {
        Write-LogError "SQLite restore failed"
        exit 1
    }
}

function List-Backups {
    param([string]$BackupDir)
    
    Write-LogInfo "Available backups in $BackupDir:"
    Get-ChildItem "$BackupDir\plannededucation_*.sql.gz" -ErrorAction SilentlyContinue | 
        Select-Object Name, Length, LastWriteTime | Format-Table -AutoSize
    
    if (-not (Get-ChildItem "$BackupDir\plannededucation_*.sql.gz" -ErrorAction SilentlyContinue)) {
        Write-LogWarn "No backups found"
    }
}

function Cleanup-Backups {
    param([string]$BackupDir, [int]$RetentionDays)
    
    Write-LogInfo "Cleaning backups older than $RetentionDays days..."
    $deleted = Get-ChildItem "$BackupDir\plannededucation_*.sql.gz" -ErrorAction SilentlyContinue | 
        Where-Object { $_.LastWriteTime -lt (Get-Date).AddDays(-$RetentionDays) } | 
        Remove-Item -Force -Verbose
    
    Write-LogInfo "Cleanup completed"
}

# Main
$DbType = Get-DbType $DatabaseUrl
Write-LogInfo "Detected database type: $DbType"

switch ($Command) {
    'backup' {
        $backupFile = "$BackupDir\plannededucation_${DbType}_${Timestamp}.sql.gz"
        switch ($DbType) {
            'postgresql' { Backup-PostgreSQL $DatabaseUrl $backupFile }
            'sqlite' { Backup-SQLite $DatabaseUrl $backupFile }
            default { Write-LogError "Unsupported database type: $DbType"; exit 1 }
        }
    }
    'restore' {
        if (-not $BackupFile) { Write-LogError "Backup file required for restore"; exit 1 }
        switch ($DbType) {
            'postgresql' { Restore-PostgreSQL $DatabaseUrl $BackupFile }
            'sqlite' { Restore-SQLite $DatabaseUrl $BackupFile }
            default { Write-LogError "Unsupported database type: $DbType"; exit 1 }
        }
    }
    'list' { List-Backups $BackupDir }
    'cleanup' { Cleanup-Backups $BackupDir $RetentionDays }
    default { Write-LogError "Unknown command: $Command"; exit 1 }
}