#!/bin/bash

# PostgreSQL Backup Script for Synapse Production Infrastructure
# Implements automated backup with point-in-time recovery support

set -euo pipefail

# Configuration
POSTGRES_HOST="${POSTGRES_HOST:-postgres-primary}"
POSTGRES_PORT="${POSTGRES_PORT:-5432}"
POSTGRES_USER="${POSTGRES_USER:-postgres}"
POSTGRES_PASSWORD="${POSTGRES_PASSWORD:-synapse_secure_2024}"
BACKUP_DIR="/backups"
WAL_ARCHIVE_DIR="/var/lib/postgresql/wal-archive"
RETENTION_DAYS="${BACKUP_RETENTION_DAYS:-30}"
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")

# Logging function
log() {
    echo "[$(date +'%Y-%m-%d %H:%M:%S')] $1" | tee -a "${BACKUP_DIR}/backup.log"
}

# Error handling
error_exit() {
    log "ERROR: $1"
    exit 1
}

# Create backup directories
mkdir -p "${BACKUP_DIR}/full"
mkdir -p "${BACKUP_DIR}/incremental"
mkdir -p "${BACKUP_DIR}/wal"

# Check if PostgreSQL is available
log "Checking PostgreSQL connectivity..."
export PGPASSWORD="${POSTGRES_PASSWORD}"
pg_isready -h "${POSTGRES_HOST}" -p "${POSTGRES_PORT}" -U "${POSTGRES_USER}" || error_exit "PostgreSQL is not available"

# Function to perform full backup
perform_full_backup() {
    local db_name=$1
    local backup_file="${BACKUP_DIR}/full/${db_name}_${TIMESTAMP}.sql.gz"
    
    log "Starting full backup of database: ${db_name}"
    
    # Perform database dump with compression
    pg_dump -h "${POSTGRES_HOST}" -p "${POSTGRES_PORT}" -U "${POSTGRES_USER}" \
        --verbose --create --clean --if-exists \
        --format=custom --compress=9 \
        "${db_name}" | gzip > "${backup_file}" || error_exit "Full backup failed for ${db_name}"
    
    # Verify backup integrity
    gunzip -c "${backup_file}" | pg_restore --list > /dev/null || error_exit "Backup verification failed for ${db_name}"
    
    local size=$(du -h "${backup_file}" | cut -f1)
    log "Full backup completed: ${backup_file} (${size})"
    
    # Create backup metadata
    cat > "${backup_file}.meta" << EOF
{
    "database": "${db_name}",
    "backup_type": "full",
    "timestamp": "${TIMESTAMP}",
    "host": "${POSTGRES_HOST}",
    "size": "${size}",
    "created_at": "$(date -Iseconds)",
    "retention_until": "$(date -d '+30 days' -Iseconds)"
}
EOF
}

# Function to perform WAL archival
archive_wal_files() {
    log "Archiving WAL files..."
    
    if [[ -d "${WAL_ARCHIVE_DIR}" ]]; then
        # Copy WAL files to backup directory with compression
        find "${WAL_ARCHIVE_DIR}" -name "*.backup" -o -name "0*" | while read -r wal_file; do
            if [[ ! -f "${BACKUP_DIR}/wal/$(basename "${wal_file}").gz" ]]; then
                gzip -c "${wal_file}" > "${BACKUP_DIR}/wal/$(basename "${wal_file}").gz"
                log "Archived WAL file: $(basename "${wal_file}")"
            fi
        done
    fi
}

# Function to cleanup old backups
cleanup_old_backups() {
    log "Cleaning up backups older than ${RETENTION_DAYS} days..."
    
    # Remove old full backups
    find "${BACKUP_DIR}/full" -name "*.sql.gz" -mtime +${RETENTION_DAYS} -delete || true
    find "${BACKUP_DIR}/full" -name "*.meta" -mtime +${RETENTION_DAYS} -delete || true
    
    # Remove old WAL archives
    find "${BACKUP_DIR}/wal" -name "*.gz" -mtime +${RETENTION_DAYS} -delete || true
    
    # Clean up old logs
    find "${BACKUP_DIR}" -name "*.log" -mtime +7 -delete || true
    
    log "Cleanup completed"
}

# Function to test backup restoration
test_backup_restore() {
    local backup_file=$1
    log "Testing backup restoration: $(basename "${backup_file}")"
    
    # Create temporary test database
    local test_db="test_restore_${TIMESTAMP}"
    createdb -h "${POSTGRES_HOST}" -p "${POSTGRES_PORT}" -U "${POSTGRES_USER}" "${test_db}" || error_exit "Failed to create test database"
    
    # Attempt to restore backup
    if gunzip -c "${backup_file}" | pg_restore -h "${POSTGRES_HOST}" -p "${POSTGRES_PORT}" -U "${POSTGRES_USER}" -d "${test_db}" --verbose; then
        log "Backup restoration test PASSED"
    else
        error_exit "Backup restoration test FAILED"
    fi
    
    # Clean up test database
    dropdb -h "${POSTGRES_HOST}" -p "${POSTGRES_PORT}" -U "${POSTGRES_USER}" "${test_db}" || true
}

# Function to send backup notifications
send_notification() {
    local status=$1
    local message=$2
    
    # Send notification to monitoring system (webhook or API)
    if [[ -n "${BACKUP_WEBHOOK_URL:-}" ]]; then
        curl -X POST "${BACKUP_WEBHOOK_URL}" \
            -H "Content-Type: application/json" \
            -d "{\"status\":\"${status}\",\"message\":\"${message}\",\"timestamp\":\"$(date -Iseconds)\"}" || true
    fi
    
    log "Notification sent: ${status} - ${message}"
}

# Main backup execution
main() {
    log "Starting PostgreSQL backup process..."
    
    # Backup all critical databases
    perform_full_backup "synapse_core"
    perform_full_backup "synapse_analytics" 
    perform_full_backup "synapse_revenue"
    
    # Archive WAL files for point-in-time recovery
    archive_wal_files
    
    # Test the most recent backup
    latest_backup=$(ls -t "${BACKUP_DIR}/full/"*.sql.gz 2>/dev/null | head -1)
    if [[ -n "${latest_backup}" ]]; then
        test_backup_restore "${latest_backup}"
    fi
    
    # Cleanup old backups
    cleanup_old_backups
    
    # Calculate total backup size
    total_size=$(du -sh "${BACKUP_DIR}" | cut -f1)
    
    log "Backup process completed successfully. Total size: ${total_size}"
    send_notification "success" "PostgreSQL backup completed successfully. Total size: ${total_size}"
}

# Handle script interruption
trap 'error_exit "Backup interrupted by signal"' INT TERM

# Execute main function
main "$@"