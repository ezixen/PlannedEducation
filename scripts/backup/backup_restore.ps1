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
    
    # Parse postgresql://user:pass@host:port/dbname — never Invoke-Expression (F-032).
    if ($DbUrl -match 'postgresql://([^:]+):([^@]+)@([^:]+):(\d+)/(.+)') {
        $user = $matches[1]
        $pass = $matches[2]
        $pgHost = $matches[3]
        $port = $matches[4]
        $dbname = $matches[5]
        
        $env:PGPASSWORD = $pass
        $pgDump = Get-Command pg_dump -ErrorAction SilentlyContinue
        if (-not $pgDump) {
            Write-LogError "pg_dump not found on PATH"
            exit 1
        }
        $rawSql = "$BackupFile.tmp.sql"
        & $pgDump.Source -h $pgHost -p $port -U $user -d $dbname --no-owner --no-privileges --clean --if-exists -f $rawSql
        if ($LASTEXITCODE -ne 0) {
            Write-LogError "PostgreSQL backup failed"
            exit 1
        }
        if (Get-Command gzip -ErrorAction SilentlyContinue) {
            & gzip -f -c $rawSql | Set-Content -AsByteStream -Path $BackupFile
            Remove-Item $rawSql -Force -ErrorAction SilentlyContinue
        } else {
            # Fallback: keep uncompressed dump when gzip is unavailable
            Move-Item -Force $rawSql ($BackupFile -replace '\.gz$', '')
            $BackupFile = $BackupFile -replace '\.gz$', ''
        }
        Write-LogInfo "PostgreSQL backup saved to: $BackupFile"
        return $BackupFile
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
        $sqlite = Get-Command sqlite3 -ErrorAction SilentlyContinue
        if (-not $sqlite) {
            # Safe file copy fallback (no shell interpolation)
            Copy-Item -LiteralPath $dbPath -Destination ($BackupFile -replace '\.sql\.gz$', '.db')
            Write-LogInfo "SQLite file copied to backup location"
            return ($BackupFile -replace '\.sql\.gz$', '.db')
        }
        $rawSql = "$BackupFile.tmp.sql"
        & $sqlite.Source $dbPath ".dump" | Set-Content -Path $rawSql -Encoding utf8
        if ($LASTEXITCODE -ne 0) {
            Write-LogError "SQLite backup failed"
            exit 1
        }
        if (Get-Command gzip -ErrorAction SilentlyContinue) {
            & gzip -f -c $rawSql | Set-Content -AsByteStream -Path $BackupFile
            Remove-Item $rawSql -Force -ErrorAction SilentlyContinue
        } else {
            Move-Item -Force $rawSql ($BackupFile -replace '\.gz$', '')
            $BackupFile = $BackupFile -replace '\.gz$', ''
        }
        Write-LogInfo "SQLite backup saved to: $BackupFile"
        return $BackupFile
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
        $pgHost = $matches[3]
        $port = $matches[4]
        $dbname = $matches[5]
        
        Write-LogWarn "This will REPLACE the database '$dbname'. Continue? (y/N)"
        $confirm = Read-Host
        if ($confirm -notmatch '^[yY]$') {
            Write-LogInfo "Restore cancelled"
            return
        }
        
        $env:PGPASSWORD = $pass
        $psql = Get-Command psql -ErrorAction SilentlyContinue
        if (-not $psql) {
            Write-LogError "psql not found on PATH"
            exit 1
        }
        $sqlFile = $BackupFile
        if ($BackupFile -like "*.gz") {
            $sqlFile = "$BackupFile.decompressed.sql"
            if (Get-Command gunzip -ErrorAction SilentlyContinue) {
                & gunzip -c $BackupFile | Set-Content -Path $sqlFile -Encoding utf8
            } else {
                Write-LogError "gunzip not available to decompress backup"
                exit 1
            }
        }
        & $psql.Source -h $pgHost -p $port -U $user -d $dbname -f $sqlFile
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
        Copy-Item -LiteralPath $dbPath -Destination $preRestore
        Write-LogInfo "Current database backed up to: $preRestore"
    }
    
    if ($BackupFile -like "*.db" -or $BackupFile -like "*.sqlite*") {
        Copy-Item -LiteralPath $BackupFile -Destination $dbPath -Force
        Write-LogInfo "SQLite restore completed successfully"
        return
    }

    $sqlite = Get-Command sqlite3 -ErrorAction SilentlyContinue
    if (-not $sqlite) {
        Write-LogError "sqlite3 not found on PATH"
        exit 1
    }
    $sqlFile = $BackupFile
    if ($BackupFile -like "*.gz") {
        $sqlFile = "$BackupFile.decompressed.sql"
        & gunzip -c $BackupFile | Set-Content -Path $sqlFile -Encoding utf8
    }
    Get-Content -LiteralPath $sqlFile | & $sqlite.Source $dbPath
    
    if ($LASTEXITCODE -eq 0) {
        Write-LogInfo "SQLite restore completed successfully"
    } else {
        Write-LogError "SQLite restore failed"
        exit 1
    }
}

function List-Backups {
    param([string]$BackupDir)
    
    Write-LogInfo "Available backups in ${BackupDir}:"
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