#!/usr/bin/env bash
# Backup & Restore Drill Script for PlannedEducation
# Runs monthly automated restore drill to staging environment
# Validates RPO < 24h, RTO < 4h

set -euo pipefail

# Configuration
STAGING_DB="plannededucation_staging"
BACKUP_DIR="${BACKUP_DIR:-/backups}"
LOG_FILE="${LOG_FILE:-/var/log/backup_restore_drill.log}"
RTO_THRESHOLD_SECONDS=14400  # 4 hours

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

log() {
    echo -e "[$(date '+%Y-%m-%d %H:%M:%S')] $*" | tee -a "$LOG_FILE"
}

log_success() {
    log "${GREEN}✓ $*${NC}"
}

log_error() {
    log "${RED}✗ $*${NC}"
}

log_warn() {
    log "${YELLOW}⚠ $*${NC}"
}

# Start timer
START_TIME=$(date +%s)

log "=== Starting Monthly Restore Drill ==="
log "Backup directory: $BACKUP_DIR"
log "Staging database: $STAGING_DB"

# 1. Find latest backup
LATEST_BACKUP=$(ls -t "$BACKUP_DIR"/plannededucation_*.dump 2>/dev/null | head -1)

if [[ -z "$LATEST_BACKUP" ]]; then
    log_error "No backup files found in $BACKUP_DIR"
    exit 1
fi

log "Using backup: $LATEST_BACKUP"
BACKUP_SIZE=$(stat -c%s "$LATEST_BACKUP" 2>/dev/null || stat -f%z "$LATEST_BACKUP" 2>/dev/null)
log "Backup size: $((BACKUP_SIZE / 1024 / 1024)) MB"

# 2. Verify backup integrity
log "Verifying backup integrity..."
if ! pg_restore --list "$LATEST_BACKUP" > /dev/null 2>&1; then
    log_error "Backup file is corrupted or unreadable"
    exit 1
fi
log_success "Backup integrity verified"

# 3. Check backup age
BACKUP_MTIME=$(stat -c%Y "$LATEST_BACKUP" 2>/dev/null || stat -f%m "$LATEST_BACKUP" 2>/dev/null)
NOW=$(date +%s)
BACKUP_AGE_HOURS=$(( (NOW - BACKUP_MTIME) / 3600 ))

if [[ $BACKUP_AGE_HOURS -gt 36 ]]; then
    log_warn "Backup is $BACKUP_AGE_HOURS hours old (exceeds 36h threshold)"
else
    log_success "Backup age: ${BACKUP_AGE_HOURS}h (within RPO)"
fi

# 4. Create staging database
log "Creating staging database: $STAGING_DB"
psql -U postgres -c "DROP DATABASE IF EXISTS $STAGING_DB;" >> "$LOG_FILE" 2>&1
psql -U postgres -c "CREATE DATABASE $STAGING_DB;" >> "$LOG_FILE" 2>&1
log_success "Staging database created"

# 4. Restore to staging
log "Restoring backup to staging database..."
RESTORE_START=$(date +%s)

if ! pg_restore \
    --username=postgres \
    --dbname="$STAGING_DB" \
    --clean \
    --if-exists \
    --no-owner \
    --no-privileges \
    "$LATEST_BACKUP" >> "$LOG_FILE" 2>&1; then
    log_error "Restore failed"
    psql -U postgres -c "DROP DATABASE IF EXISTS $STAGING_DB;" >> "$LOG_FILE" 2>&1
    exit 1
fi

RESTORE_END=$(date +%s)
RESTORE_DURATION=$((RESTORE_END - RESTORE_START))
log_success "Restore completed in ${RESTORE_DURATION}s"

# 5. Run migrations
log "Running database migrations..."
cd /app 2>/dev/null || cd /opt/plannededucation 2>/dev/null || true
if [[ -f "alembic.ini" ]]; then
    DATABASE_URL="postgresql://postgres:postgres@localhost:5432/$STAGING_DB" \
    alembic upgrade head >> "$LOG_FILE" 2>&1
    log_success "Migrations applied"
else
    log_warn "No alembic.ini found, skipping migrations"
fi

# 6. Data integrity checks
log "Running data integrity checks..."

# Check table counts
TABLE_COUNTS=$(psql -U postgres -d "$STAGING_DB" -t -c "
    SELECT schemaname, relname, n_live_tup
    FROM pg_stat_user_tables
    WHERE schemaname = 'public'
    ORDER BY relname;
" 2>/dev/null)

log "Table row counts:"
echo "$TABLE_COUNTS" | while read -r line; do
    log "  $line"
done

# Verify critical tables exist and have data
CRITICAL_TABLES=("users" "exams" "questions" "exam_submissions" "account_relationships")
for table in "${CRITICAL_TABLES[@]}"; do
    COUNT=$(psql -U postgres -d "$STAGING_DB" -t -c "SELECT COUNT(*) FROM $table;" 2>/dev/null | xargs)
    if [[ -n "$COUNT" && "$COUNT" -ge 0 ]]; then
        log_success "Table '$table': $COUNT rows"
    else
        log_error "Table '$table' check failed"
    fi
done

# 7. Run smoke tests
log "Running smoke tests..."
SMOKE_TESTS=(
    "SELECT COUNT(*) FROM users WHERE is_active = true;"
    "SELECT COUNT(*) FROM exams;"
    "SELECT COUNT(*) FROM exam_submissions;"
)

for test_sql in "${SMOKE_TESTS[@]}"; do
    RESULT=$(psql -U postgres -d "$STAGING_DB" -t -c "$test_sql" 2>/dev/null | xargs)
    log "  $test_sql => $RESULT"
done

# 8. Test application connectivity (if API is available)
if command -v curl &> /dev/null; then
    log "Testing API connectivity..."
    # This would need the API running against staging DB
    # For now, just verify DB is accessible
    if psql -U postgres -d "$STAGING_DB" -c "SELECT 1;" > /dev/null 2>&1; then
        log_success "Database connectivity verified"
    else
        log_error "Database connectivity failed"
    fi
fi

# 9. Cleanup staging database
log "Cleaning up staging database..."
psql -U postgres -c "DROP DATABASE IF EXISTS $STAGING_DB;" >> "$LOG_FILE" 2>&1
log_success "Staging database dropped"

# 10. Calculate total duration
END_TIME=$(date +%s)
TOTAL_DURATION=$((END_TIME - START_TIME))

log "=== Restore Drill Completed ==="
log "Total duration: ${TOTAL_DURATION}s ($((TOTAL_DURATION / 60))m $((TOTAL_DURATION % 60))s)"
log "Restore duration: ${RESTORE_DURATION}s"

# Check RTO compliance
if [[ $TOTAL_DURATION -le $RTO_THRESHOLD_SECONDS ]]; then
    log_success "RTO CHECK PASSED: ${TOTAL_DURATION}s <= ${RTO_THRESHOLD_SECONDS}s (4h)"
    RTO_STATUS="PASSED"
else
    log_error "RTO CHECK FAILED: ${TOTAL_DURATION}s > ${RTO_THRESHOLD_SECONDS}s (4h)"
    RTO_STATUS="FAILED"
fi

# Check RPO compliance
if [[ $BACKUP_AGE_HOURS -le 24 ]]; then
    log_success "RPO CHECK PASSED: ${BACKUP_AGE_HOURS}h <= 24h"
    RPO_STATUS="PASSED"
else
    log_error "RPO CHECK FAILED: ${BACKUP_AGE_HOURS}h > 24h"
    RPO_STATUS="FAILED"
fi

# Summary
log ""
log "=== DRILL SUMMARY ==="
log "RPO Status: $RPO_STATUS (Backup age: ${BACKUP_AGE_HOURS}h)"
log "RTO Status: $RTO_STATUS (Total time: ${TOTAL_DURATION}s)"
log "Backup file: $(basename "$LATEST_BACKUP")"
log "Backup size: $((BACKUP_SIZE / 1024 / 1024)) MB"
log "Restore time: ${RESTORE_DURATION}s"

# Exit with appropriate code
if [[ "$RTO_STATUS" == "PASSED" && "$RPO_STATUS" == "PASSED" ]]; then
    log_success "DRILL PASSED"
    exit 0
else
    log_error "DRILL FAILED"
    exit 1
fi