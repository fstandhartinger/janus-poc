#!/bin/bash
# Ralph Loop Watchdog - Ensures ralph-loop-codex.sh keeps running
# This script is meant to be called by cron every hour
# It will self-disable after EXPIRY_TIMESTAMP

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
LOG_FILE="$PROJECT_DIR/logs/ralph-watchdog.log"
RALPH_SCRIPT="$SCRIPT_DIR/ralph-loop-codex.sh"

# Expiry: Mon Jan 27 18:00:00 CET 2026 (extended)
EXPIRY_TIMESTAMP=1769533200

# Ensure logs directory exists
mkdir -p "$PROJECT_DIR/logs"

log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" >> "$LOG_FILE"
}

# Check if we've expired
CURRENT_TIMESTAMP=$(date +%s)
if [ "$CURRENT_TIMESTAMP" -gt "$EXPIRY_TIMESTAMP" ]; then
    log "Watchdog expired. Removing cron job and exiting."
    # Remove our cron entry
    crontab -l 2>/dev/null | grep -v "ralph-watchdog.sh" | crontab -
    exit 0
fi

# Check if ralph-loop-codex.sh is running
RALPH_PID=$(ps aux | grep "[r]alph-loop-codex.sh" | awk '{print $2}' | head -1)
if [ -n "$RALPH_PID" ]; then
    log "Ralph loop (Codex) is running (PID: $RALPH_PID). No action needed."
    exit 0
fi

# Not running - start it
log "Ralph loop (Codex) NOT running. Starting..."

cd "$PROJECT_DIR"

# Start in background with nohup, redirect output to log
nohup "$RALPH_SCRIPT" >> "$PROJECT_DIR/logs/ralph-loop-codex.log" 2>&1 &

NEW_PID=$!
log "Started ralph-loop-codex.sh with PID: $NEW_PID"

# Verify it started
sleep 2
VERIFY_PID=$(ps aux | grep "[r]alph-loop-codex.sh" | awk '{print $2}' | head -1)
if [ -n "$VERIFY_PID" ]; then
    log "Verified: Ralph loop (Codex) is now running (PID: $VERIFY_PID)."
else
    log "ERROR: Failed to start ralph loop!"
    exit 1
fi
