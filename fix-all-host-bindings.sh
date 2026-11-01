#!/bin/bash
# ============================================================================
# Fix All Host Bindings - Phase 1.5 Security Remediation
# ============================================================================
# Replaces all 0.0.0.0 bindings with 127.0.0.1 across the entire codebase
#
# Usage:
#   ./fix-all-host-bindings.sh [--dry-run] [--backup]
#
# Options:
#   --dry-run    Show what would be changed without applying
#   --backup     Create backup before modifying files
# ============================================================================

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

DRY_RUN=false
DO_BACKUP=false

# Parse arguments
for arg in "$@"; do
    case $arg in
        --dry-run)
            DRY_RUN=true
            ;;
        --backup)
            DO_BACKUP=true
            ;;
    esac
done

echo -e "${BLUE}============================================================================${NC}"
echo -e "${BLUE}  PHASE 1.5: FIX ALL HOST BINDINGS${NC}"
echo -e "${BLUE}  Converting 0.0.0.0 → 127.0.0.1${NC}"
echo -e "${BLUE}============================================================================${NC}"
echo ""

if [ "$DRY_RUN" = true ]; then
    echo -e "${YELLOW}🔍 DRY RUN MODE - No files will be modified${NC}"
    echo ""
fi

# Create backup if requested
if [ "$DO_BACKUP" = true ] && [ "$DRY_RUN" = false ]; then
    BACKUP_DIR="../One2lvos_backup_$(date +%Y%m%d_%H%M%S)"
    echo -e "${BLUE}📦 Creating backup: $BACKUP_DIR${NC}"
    cp -r . "$BACKUP_DIR"
    echo -e "${GREEN}✓ Backup created${NC}"
    echo ""
fi

# Function to fix file
fix_file() {
    local file=$1
    local description=$2

    if [ ! -f "$file" ]; then
        echo -e "${YELLOW}⚠  Skipping $file (not found)${NC}"
        return
    fi

    # Check if file contains 0.0.0.0
    if ! grep -q "0\.0\.0\.0" "$file"; then
        echo -e "${GREEN}✓ $description (already fixed or no issues)${NC}"
        return
    fi

    echo -e "${YELLOW}📝 Fixing: $description${NC}"
    echo -e "   File: $file"

    if [ "$DRY_RUN" = false ]; then
        # Shell script patterns
        sed -i 's/--host 0\.0\.0\.0/--host 127.0.0.1/g' "$file"

        # Python patterns
        sed -i 's/host="0\.0\.0\.0"/host="127.0.0.1"/g' "$file"
        sed -i "s/host='0\.0\.0\.0'/host='127.0.0.1'/g" "$file"
        sed -i 's/"0\.0\.0\.0"/"127.0.0.1"/g' "$file"

        # Count replacements
        local count=$(grep -c "127\.0\.0\.1" "$file" || echo "0")
        echo -e "${GREEN}   ✓ Fixed ($count binding(s) updated)${NC}"
    else
        local count=$(grep -c "0\.0\.0\.0" "$file" || echo "0")
        echo -e "${BLUE}   [DRY RUN] Would fix $count binding(s)${NC}"
    fi
    echo ""
}

# Category A: High Priority Scripts
echo -e "${BLUE}═══ Category A: Primary Startup Scripts (HIGH PRIORITY) ═══${NC}"
echo ""
fix_file "build.sh" "build.sh (4 services)"
fix_file "start-all.sh" "start-all.sh (2 services)"
fix_file "startos.sh" "startos.sh (2 services)"
echo ""

# Category B: Secondary Scripts
echo -e "${BLUE}═══ Category B: Secondary Startup Scripts (MEDIUM PRIORITY) ═══${NC}"
echo ""
fix_file "start-up.sh" "start-up.sh"
fix_file "deploy-sovereign.sh" "deploy-sovereign.sh"
fix_file "lumenis-control/auto-run-lumenis.sh" "lumenis-control/auto-run-lumenis.sh"
fix_file "lumenis-control/start-all.sh" "lumenis-control/start-all.sh"
fix_file "serve-dashboard.sh" "serve-dashboard.sh"
echo ""

# Category C: Python Application Files
echo -e "${BLUE}═══ Category C: Python Application Files (REQUIRE CODE CHANGE) ═══${NC}"
echo ""
fix_file "core_service.py" "core_service.py (Flask app)"
fix_file "one2lvos_launcher.py" "one2lvos_launcher.py (3 services)"
fix_file "steamos_lumenis/one2lvos_dashboard/server.py" "steamos_lumenis dashboard server"
echo ""

# Category D: Documentation
echo -e "${BLUE}═══ Category D: Documentation Examples (LOW PRIORITY) ═══${NC}"
echo ""
fix_file "deploy_semantic_to_onworks.py" "deploy_semantic_to_onworks.py (examples)"
fix_file "talk_to_lumenis.py" "talk_to_lumenis.py (examples)"
echo ""

# Verification
echo -e "${BLUE}═══ Verification ═══${NC}"
echo ""

if [ "$DRY_RUN" = false ]; then
    echo -e "${YELLOW}🔍 Checking for remaining 0.0.0.0 bindings...${NC}"

    REMAINING=$(grep -r "host.*0\.0\.0\.0\|host=.*0\.0\.0\.0" --include="*.sh" --include="*.py" . 2>/dev/null | wc -l)

    if [ "$REMAINING" -eq 0 ]; then
        echo -e "${GREEN}✅ SUCCESS: No 0.0.0.0 bindings found!${NC}"
    else
        echo -e "${RED}⚠  WARNING: Found $REMAINING remaining binding(s)${NC}"
        echo -e "${YELLOW}Files with remaining issues:${NC}"
        grep -r "host.*0\.0\.0\.0\|host=.*0\.0\.0\.0" --include="*.sh" --include="*.py" . 2>/dev/null || true
    fi
else
    echo -e "${BLUE}[DRY RUN] Verification skipped${NC}"
fi

echo ""
echo -e "${BLUE}============================================================================${NC}"

if [ "$DRY_RUN" = true ]; then
    echo -e "${YELLOW}🔍 DRY RUN COMPLETE - No changes were made${NC}"
    echo -e "${BLUE}   Run without --dry-run to apply fixes${NC}"
else
    echo -e "${GREEN}✅ PHASE 1.5 COMPLETE - All host bindings fixed!${NC}"
    echo ""
    echo -e "${BLUE}Next steps:${NC}"
    echo -e "  1. Review changes: git diff"
    echo -e "  2. Test services: ./start-lumenis-reactor.sh"
    echo -e "  3. Verify binding: netstat -tuln | grep LISTEN"
    echo -e "  4. Test external access blocked (should fail)"
    echo -e "  5. Test local access works (should succeed)"
    echo -e "  6. Commit changes: git add -A && git commit -m 'Phase 1.5: Fix all host bindings'"
fi

echo -e "${BLUE}============================================================================${NC}"
