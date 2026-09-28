#!/usr/bin/env bash
# Backup/Restore Scripts - Free/Open-Source Only
# Uses pg_dump/pg_restore for PostgreSQL, sqlite3 for SQLite
# NO PAID SERVICES

set -euo pipefail

# Configuration
BACKUP_DIR="${BACKUP_DIR:-./backups}"
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
RETENTION_DAYS="${RETENTION_DAYS:-30}"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

log_info() { echo -e "${GREEN}[INFO]${NC} $1"; }
log_warn() { echo -e "${YELLOW}[WARN]${NC} $1"; }
log_error() { echo -e "${RED}[ERROR]${NC} $1"; }

# Create backup directory
mkdir -p "$BACKUP_DIR"

# Detect database type from DATABASE_URL
detect_db_type() {
    local db_url="${DATABASE_URL:-}"
    if [[ "$db_url" == postgresql* ]]; then
        echo "postgresql"
    elif [[ "$db_url" == sqlite* ]]; then
        echo "sqlite"
    else
        echo "unknown"
    fi
}

# PostgreSQL backup
backup_postgresql() {
    local db_url="$1"
    local backup_file="$BACKUP_DIR/plannededucation_pg_${TIMESTAMP}.sql.gz"
    
    log_info "Backing up PostgreSQL database..."
    
    # Extract connection parameters
    # postgresql://user:pass@host:port/dbname
    if [[ "$db_url" =~ postgresql://([^:]+):([^@]+)@([^:]+):([0-9]+)/(.+) ]]; then
        local user="${BASH_REMATCH[1]}"
        local pass="${BASH_REMATCH[2]}"
        local host="${BASH_REMATCH[3]}"
        local port="${BASH_REMATCH[4]}"
        local dbname="${BASH_REMATCH[5]}"
        
        PGPASSWORD="$pass" pg_dump -h "$host" -p "$port" -U "$user" -d "$dbname" \
            --no-owner --no-privileges --clean --if-exists | gzip > "$backup_file"
        
        if [[ $? -eq 0 ]]; then
            log_info "PostgreSQL backup saved to: $backup_file"
            echo "$backup_file"
        else
            log_error "PostgreSQL backup failed"
            return 1
        fi
    else
        log_error "Could not parse PostgreSQL URL"
        return 1
    fi
}

# SQLite backup
backup_sqlite() {
    local db_url="$1"
    local backup_file="$BACKUP_DIR/plannededucation_sqlite_${TIMESTAMP}.sql.gz"
    
    log_info "Backing up SQLite database..."
    
    # Extract file path from sqlite:///path/to/db
    local db_path="${db_url#sqlite:///}"
    db_path="${db_path#sqlite://}"
    
    if [[ -f "$db_path" ]]; then
        sqlite3 "$db_path" .dump | gzip > "$backup_file"
        
        if [[ $? -eq 0 ]]; then
            log_info "SQLite backup saved to: $backup_file"
            echo "$backup_file"
        else
            log_error "SQLite backup failed"
            return 1
        fi
    else
        log_error "SQLite database file not found: $db_path"
        return 1
    fi
}

# PostgreSQL restore
restore_postgresql() {
    local db_url="$1"
    local backup_file="$2"
    
    log_info "Restoring PostgreSQL database from: $backup_file"
    
    if [[ ! -f "$backup_file" ]]; then
        log_error "Backup file not found: $backup_file"
        return 1
    fi
    
    if [[ "$db_url" =~ postgresql://([^:]+):([^@]+)@([^:]+):([0-9]+)/(.+) ]]; then
        local user="${BASH_REMATCH[1]}"
        local pass="${BASH_REMATCH[2]}"
        local host="${BASH_REMATCH[3]}"
        local port="${BASH_REMATCH[4]}"
        local dbname="${BASH_REMATCH[5]}"
        
        log_warn "This will REPLACE the database '$dbname'. Continue? (y/N)"
        read -r confirm
        if [[ "$confirm" != "y" && "$confirm" != "Y" ]]; then
            log_info "Restore cancelled"
            return 0
        fi
        
        gunzip -c "$backup_file" | PGPASSWORD="$pass" psql -h "$host" -p "$port" -U "$user" -d "$dbname"
        
        if [[ $? -eq 0 ]]; then
            log_info "PostgreSQL restore completed successfully"
        else
            log_error "PostgreSQL restore failed"
            return 1
        fi
    else
        log_error "Could not parse PostgreSQL URL"
        return 1
    fi
}

# SQLite restore
restore_sqlite() {
    local db_url="$1"
    local backup_file="$2"
    
    log_info "Restoring SQLite database from: $backup_file"
    
    if [[ ! -f "$backup_file" ]]; then
        log_error "Backup file not found: $backup_file"
        return 1
    fi
    
    local db_path="${db_url#sqlite:///}"
    db_path="${db_path#sqlite://}"
    
    log_warn "This will REPLACE the database '$db_path'. Continue? (y/N)"
    read -r confirm
    if [[ "$confirm" != "y" && "$confirm" != "Y" ]]; then
        log_info "Restore cancelled"
        return 0
    fi
    
    # Backup current database first
    if [[ -f "$db_path" ]]; then
        cp "$db_path" "${db_path}.pre_restore_${TIMESTAMP}"
        log_info "Current database backed up to: ${db_path}.pre_restore_${TIMESTAMP}"
    fi
    
    gunzip -c "$backup_file" | sqlite3 "$db_path"
    
    if [[ $? -eq 0 ]]; then
        log_info "SQLite restore completed successfully"
    else
        log_error "SQLite restore failed"
        return 1
    fi
}

# List available backups
list_backups() {
    log_info "Available backups in $BACKUP_DIR:"
    ls -lh "$BACKUP_DIR"/plannededucation_*.sql.gz 2>/dev/null || log_warn "No backups found"
}

# Clean old backups
cleanup_backups() {
    log_info "Cleaning backups older than $RETENTION_DAYS days..."
    find "$BACKUP_DIR" -name "plannededucation_*.sql.gz" -mtime +$RETENTION_DAYS -delete
    log_info "Cleanup completed"
}

# Main
main() {
    local command="${1:-}"
    local backup_file="${2:-}"
    
    if [[ -z "$command" ]]; then
        echo "Usage: $0 {backup|restore|list|cleanup} [backup_file]"
        echo "  backup                    - Create a new backup"
        echo "  restore <backup_file>     - Restore from backup file"
        echo "  list                      - List available backups"
        echo "  cleanup                   - Remove backups older than $RETENTION_DAYS days"
        exit 1
    fi
    
    local db_type=$(detect_db_type)
    log_info "Detected database type: $db_type"
    
    case "$command" in
        backup)
            case "$db_type" in
                postgresql) backup_postgresql "${DATABASE_URL}" ;;
                sqlite) backup_sqlite "${DATABASE_URL}" ;;
                *) log_error "Unsupported database type: $db_type"; exit 1 ;;
            esac
            ;;
        restore)
            if [[ -z "$backup_file" ]]; then
                log_error "Backup file required for restore"
                exit 1
            fi
            case "$db_type" in
                postgresql) restore_postgresql "${DATABASE_URL}" "$backup_file" ;;
                sqlite) restore_sqlite "${DATABASE_URL}" "$backup_file" ;;
                *) log_error "Unsupported database type: $db_type"; exit 1 ;;
            esac
            ;;
        list)
            list_backups
            ;;
        cleanup)
            cleanup_backups
            ;;
        *)
            log_error "Unknown command: $command"
            exit 1
            ;;
    esac
}

main "$@"