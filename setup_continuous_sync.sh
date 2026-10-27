#!/bin/bash
# Setup continuous sync cron job

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SYNC_SCRIPT="$SCRIPT_DIR/sync_to_one2mind.sh"

echo "Setting up continuous sync cron job..."

# Make sync script executable
chmod +x "$SYNC_SCRIPT"

# Add cron job to run every 15 minutes
CRON_CMD="*/15 * * * * $SYNC_SCRIPT >> $SCRIPT_DIR/logs/sync.log 2>&1"

# Check if cron job already exists
if crontab -l 2>/dev/null | grep -q "$SYNC_SCRIPT"; then
    echo "✓ Cron job already exists"
else
    # Add to crontab
    (crontab -l 2>/dev/null; echo "$CRON_CMD") | crontab -
    echo "✓ Cron job added: sync every 15 minutes"
fi

echo ""
echo "Manual sync: $SYNC_SCRIPT"
echo "Sync logs: $SCRIPT_DIR/logs/sync.log"
echo ""
echo "To remove cron job: crontab -e (then delete the line)"
