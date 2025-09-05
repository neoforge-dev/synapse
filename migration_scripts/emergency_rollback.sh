#!/bin/bash
# Epic 10 Emergency Rollback Script
# CRITICAL: Restore $1.158M Epic 7 pipeline in case of consolidation failure
# 
# Usage: ./emergency_rollback.sh [options]
# Options:
#   --epic7-only        Restore only Epic 7 pipeline (fastest)
#   --restore-all       Restore all databases from backup
#   --verify-integrity  Verify data integrity after rollback
#   --force            Skip confirmation prompts

set -euo pipefail

# Configuration
BASE_DIR="/Users/bogdan/til/graph-rag-mcp"
BACKUP_DIR="$BASE_DIR/consolidation_backups"
LOG_FILE="$BASE_DIR/emergency_rollback.log"
EPIC7_DB="$BASE_DIR/business_development/epic7_sales_automation.db"
EXPECTED_PIPELINE_VALUE=1158000

# Logging function
log() {
    echo "[$(date +'%Y-%m-%d %H:%M:%S')] $1" | tee -a "$LOG_FILE"
}

# Error handling
error() {
    log "❌ ERROR: $1"
    exit 1
}

# Success logging
success() {
    log "✅ SUCCESS: $1"
}

# Warning logging
warn() {
    log "⚠️  WARNING: $1"
}

# Verify Epic 7 pipeline value
verify_epic7_pipeline() {
    local db_path="$1"
    
    if [[ ! -f "$db_path" ]]; then
        error "Epic 7 database not found: $db_path"
    fi
    
    local pipeline_value
    pipeline_value=$(sqlite3 "$db_path" "SELECT COALESCE(SUM(estimated_value), 0) FROM crm_contacts;" 2>/dev/null || echo "0")
    
    local contact_count
    contact_count=$(sqlite3 "$db_path" "SELECT COUNT(*) FROM crm_contacts;" 2>/dev/null || echo "0")
    
    log "Epic 7 Pipeline Verification:"
    log "  💰 Pipeline Value: \$$pipeline_value"
    log "  👥 Contact Count: $contact_count"
    
    if [[ "$pipeline_value" == "$EXPECTED_PIPELINE_VALUE" ]]; then
        success "Epic 7 pipeline value verified: \$$pipeline_value"
        return 0
    else
        error "Epic 7 pipeline value mismatch: Expected \$$EXPECTED_PIPELINE_VALUE, Found \$$pipeline_value"
        return 1
    fi
}

# Find latest Epic 7 backup
find_latest_epic7_backup() {
    local latest_backup
    latest_backup=$(find "$BACKUP_DIR" -name "epic7_sales_automation_PROTECTED_*.db" -type f -exec ls -t {} + | head -1)
    
    if [[ -z "$latest_backup" ]]; then
        error "No Epic 7 backup found in $BACKUP_DIR"
    fi
    
    echo "$latest_backup"
}

# Restore Epic 7 pipeline only
restore_epic7_pipeline() {
    log "🚨 EMERGENCY RESTORATION OF EPIC 7 PIPELINE"
    log "💰 Protecting \$1,158,000 sales pipeline"
    
    # Find latest backup
    local backup_file
    backup_file=$(find_latest_epic7_backup)
    
    log "📂 Latest backup found: $(basename "$backup_file")"
    
    # Create safety backup of current state
    local safety_backup="$BACKUP_DIR/epic7_pre_rollback_$(date +%Y%m%d_%H%M%S).db"
    if [[ -f "$EPIC7_DB" ]]; then
        cp "$EPIC7_DB" "$safety_backup"
        log "🛡️  Safety backup created: $(basename "$safety_backup")"
    fi
    
    # Restore from backup
    cp "$backup_file" "$EPIC7_DB"
    success "Epic 7 database restored from backup"
    
    # Verify restoration
    if verify_epic7_pipeline "$EPIC7_DB"; then
        success "Epic 7 pipeline restoration SUCCESSFUL"
        log "🛡️  Business continuity restored"
        return 0
    else
        error "Epic 7 pipeline restoration FAILED verification"
        return 1
    fi
}

# Restore all databases from backup
restore_all_databases() {
    log "🔄 FULL SYSTEM ROLLBACK - Restoring all databases"
    
    # Epic 7 first (critical priority)
    restore_epic7_pipeline
    
    # Find and restore other backups
    local backup_files
    mapfile -t backup_files < <(find "$BACKUP_DIR" -name "*.db" -not -name "*epic7*" -type f)
    
    if [[ ${#backup_files[@]} -eq 0 ]]; then
        warn "No additional database backups found"
        return 0
    fi
    
    log "📋 Found ${#backup_files[@]} additional database backups"
    
    for backup_file in "${backup_files[@]}"; do
        local filename
        filename=$(basename "$backup_file")
        
        # Extract original database name (remove timestamp suffix)
        local original_name
        original_name=$(echo "$filename" | sed -E 's/_PROTECTED_[0-9]{8}_[0-9]{6}\.db$/\.db/')
        
        local target_path="$BASE_DIR/$original_name"
        
        # Skip if target directory doesn't exist
        local target_dir
        target_dir=$(dirname "$target_path")
        
        if [[ ! -d "$target_dir" ]]; then
            warn "Target directory doesn't exist: $target_dir - skipping $original_name"
            continue
        fi
        
        # Restore backup
        cp "$backup_file" "$target_path"
        log "  ✓ Restored: $original_name"
    done
    
    success "Full database rollback completed"
}

# Verify data integrity across all databases
verify_system_integrity() {
    log "🔍 VERIFYING SYSTEM INTEGRITY"
    
    local integrity_pass=true
    
    # Verify Epic 7 pipeline (most critical)
    if verify_epic7_pipeline "$EPIC7_DB"; then
        success "Epic 7 pipeline integrity verified"
    else
        integrity_pass=false
    fi
    
    # Check for other critical databases
    local critical_dbs=(
        "$BASE_DIR/business_development/linkedin_business_development.db"
        "$BASE_DIR/linkedin_business_development.db"
    )
    
    for db in "${critical_dbs[@]}"; do
        if [[ -f "$db" ]]; then
            local table_count
            table_count=$(sqlite3 "$db" "SELECT COUNT(*) FROM sqlite_master WHERE type='table';" 2>/dev/null || echo "0")
            
            if [[ "$table_count" -gt 0 ]]; then
                log "  ✓ Database OK: $(basename "$db") ($table_count tables)"
            else
                warn "Database appears empty: $(basename "$db")"
                integrity_pass=false
            fi
        else
            warn "Critical database missing: $(basename "$db")"
        fi
    done
    
    if [[ "$integrity_pass" == "true" ]]; then
        success "System integrity verification PASSED"
        return 0
    else
        error "System integrity verification FAILED"
        return 1
    fi
}

# Check system health after rollback
check_system_health() {
    log "🏥 CHECKING SYSTEM HEALTH"
    
    # Check if API server is responding
    local api_status
    if api_status=$(curl -sf "http://localhost:8000/health" 2>/dev/null); then
        success "API server responding: $api_status"
    else
        warn "API server not responding - may need restart"
    fi
    
    # Check critical files exist
    local critical_files=(
        "$BASE_DIR/graph_rag/api/main.py"
        "$BASE_DIR/pyproject.toml"
        "$BASE_DIR/Makefile"
    )
    
    for file in "${critical_files[@]}"; do
        if [[ -f "$file" ]]; then
            log "  ✓ Critical file exists: $(basename "$file")"
        else
            warn "Critical file missing: $(basename "$file")"
        fi
    done
    
    success "System health check completed"
}

# Main function
main() {
    local epic7_only=false
    local restore_all=false
    local verify_integrity=false
    local force=false
    
    # Parse command line arguments
    while [[ $# -gt 0 ]]; do
        case $1 in
            --epic7-only)
                epic7_only=true
                shift
                ;;
            --restore-all)
                restore_all=true
                shift
                ;;
            --verify-integrity)
                verify_integrity=true
                shift
                ;;
            --force)
                force=true
                shift
                ;;
            *)
                echo "Unknown option: $1"
                echo "Usage: $0 [--epic7-only] [--restore-all] [--verify-integrity] [--force]"
                exit 1
                ;;
        esac
    done
    
    # Default to Epic 7 only if no specific option provided
    if [[ "$epic7_only" == "false" && "$restore_all" == "false" ]]; then
        epic7_only=true
    fi
    
    log "🚨 EPIC 10 EMERGENCY ROLLBACK INITIATED"
    log "================================================"
    
    # Confirmation prompt unless forced
    if [[ "$force" == "false" ]]; then
        echo "⚠️  This will restore database(s) from backup."
        echo "   Current data may be lost."
        read -p "   Continue? (y/N): " -n 1 -r
        echo
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            log "Rollback cancelled by user"
            exit 0
        fi
    fi
    
    # Ensure backup directory exists
    if [[ ! -d "$BACKUP_DIR" ]]; then
        error "Backup directory not found: $BACKUP_DIR"
    fi
    
    # Execute requested operations
    local success_count=0
    local total_operations=0
    
    if [[ "$epic7_only" == "true" ]]; then
        ((total_operations++))
        log "Starting Epic 7 pipeline restoration..."
        if restore_epic7_pipeline; then
            ((success_count++))
        fi
    fi
    
    if [[ "$restore_all" == "true" ]]; then
        ((total_operations++))
        log "Starting full system restoration..."
        if restore_all_databases; then
            ((success_count++))
        fi
    fi
    
    if [[ "$verify_integrity" == "true" ]]; then
        ((total_operations++))
        log "Starting integrity verification..."
        if verify_system_integrity; then
            ((success_count++))
        fi
    fi
    
    # System health check (always run)
    check_system_health
    
    # Final status
    log "================================================"
    if [[ "$success_count" -eq "$total_operations" ]]; then
        log "✅ EMERGENCY ROLLBACK COMPLETED SUCCESSFULLY"
        log "💰 Epic 7 Pipeline: RESTORED AND PROTECTED"
        log "🛡️  Business Continuity: MAINTAINED"
        exit 0
    else
        log "❌ EMERGENCY ROLLBACK COMPLETED WITH ERRORS"
        log "🚨 Manual intervention may be required"
        exit 1
    fi
}

# Ensure backup directory exists
mkdir -p "$BACKUP_DIR"

# Run main function
main "$@"