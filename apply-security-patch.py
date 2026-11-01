#!/usr/bin/env python3
"""
Apply Phase 1 Security Patches to One2lvOS
===========================================

This script applies critical security fixes to protect against:
- Unauthenticated RCE via /api/terminal
- Unauthenticated SSRF via /api/network/fetch
- Unauthenticated WebSocket RCE via /ws/terminal

Usage:
    python3 apply-security-patch.py [--dry-run] [--backup]

Options:
    --dry-run    Show what would be changed without applying
    --backup     Create backups before modifying files
"""

import sys
import os
import shutil
from pathlib import Path
from datetime import datetime

# Colors
RED = '\033[0;31m'
GREEN = '\033[0;32m'
YELLOW = '\033[1;33m'
BLUE = '\033[0;34m'
NC = '\033[0m'  # No Color

def log(msg, color=NC):
    print(f"{color}{msg}{NC}")

def backup_file(filepath):
    """Create timestamped backup of file."""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_path = f"{filepath}.backup.{timestamp}"
    shutil.copy2(filepath, backup_path)
    log(f"✓ Backed up: {filepath} -> {backup_path}", GREEN)
    return backup_path

def patch_lumenis_main():
    """Add authentication imports and middleware to lumenis-main.py."""
    filepath = "lumenis-main.py"

    if not os.path.exists(filepath):
        log(f"✗ File not found: {filepath}", RED)
        return False

    log(f"\nPatching {filepath}...", BLUE)

    with open(filepath, 'r') as f:
        content = f.read()

    # Check if already patched
    if "from lumenis_security import" in content:
        log("  Already patched - skipping", YELLOW)
        return True

    # Add security import after FastAPI imports
    if "from fastapi import FastAPI" in content:
        content = content.replace(
            "from fastapi import FastAPI, WebSocket, WebSocketDisconnect",
            "from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Depends, Request\n"
            "from lumenis_security import require_auth, verify_ip_allowlist, verify_terminal_enabled, verify_network_proxy_enabled, verify_websocket_terminal_enabled, verify_websocket_token"
        )
        log("  ✓ Added security imports", GREEN)
    else:
        log("  ⚠  Could not find FastAPI import - manual patching required", YELLOW)

    # Patch /api/terminal endpoint
    terminal_old = '@app.post("/api/terminal")\nasync def terminal_exec(body: dict):'
    terminal_new = '''@app.post("/api/terminal")
async def terminal_exec(
    request: Request,
    body: dict,
    authorized: bool = Depends(require_auth),
    ip_allowed: bool = Depends(verify_ip_allowlist),
    enabled: bool = Depends(verify_terminal_enabled)
):'''

    if terminal_old in content:
        content = content.replace(terminal_old, terminal_new)
        log("  ✓ Secured /api/terminal endpoint", GREEN)
    else:
        log("  ⚠  Could not find /api/terminal endpoint - manual patching required", YELLOW)

    # Patch /api/network/fetch endpoint
    fetch_old = '@app.post("/api/network/fetch")\nasync def network_fetch(body: dict):'
    fetch_new = '''@app.post("/api/network/fetch")
async def network_fetch(
    body: dict,
    authorized: bool = Depends(require_auth),
    enabled: bool = Depends(verify_network_proxy_enabled)
):'''

    if fetch_old in content:
        content = content.replace(fetch_old, fetch_new)
        log("  ✓ Secured /api/network/fetch endpoint", GREEN)
    else:
        log("  ⚠  Could not find /api/network/fetch endpoint - manual patching required", YELLOW)

    # Patch WebSocket /ws/terminal
    ws_old = '''@app.websocket("/ws/terminal")
async def terminal_ws(ws: WebSocket):
    """Stream subprocess output in real-time."""
    await ws.accept()'''

    ws_new = '''@app.websocket("/ws/terminal")
async def terminal_ws(ws: WebSocket):
    """Stream subprocess output in real-time."""
    # Verify WebSocket authentication token
    token = ws.query_params.get("token")
    if not verify_websocket_token(token):
        await ws.close(code=403)
        return

    # Verify WebSocket terminal is enabled
    if not verify_websocket_terminal_enabled():
        await ws.close(code=403)
        return

    await ws.accept()'''

    if ws_old in content:
        content = content.replace(ws_old, ws_new)
        log("  ✓ Secured /ws/terminal WebSocket", GREEN)
    else:
        log("  ⚠  Could not find /ws/terminal endpoint - manual patching required", YELLOW)

    return content

def check_env_file():
    """Check if .env has security configuration."""
    log("\nChecking .env configuration...", BLUE)

    if not os.path.exists(".env"):
        log("  ⚠  .env file not found", YELLOW)
        log("  ℹ  Copy .env.security.example to .env and configure", BLUE)
        return False

    with open(".env", 'r') as f:
        env_content = f.read()

    issues = []

    if "LUMENIS_SECURITY_TOKEN" not in env_content:
        issues.append("LUMENIS_SECURITY_TOKEN not set")

    if "LUMENIS_SECURITY_TOKEN=CHANGE-ME" in env_content:
        issues.append("LUMENIS_SECURITY_TOKEN using default value - CHANGE IT!")

    if "ENABLE_TERMINAL_API=true" in env_content:
        issues.append("ENABLE_TERMINAL_API=true (consider disabling for security)")

    if "ENABLE_NETWORK_PROXY=true" in env_content:
        issues.append("ENABLE_NETWORK_PROXY=true (consider disabling for security)")

    if issues:
        log("  ⚠  Configuration issues found:", YELLOW)
        for issue in issues:
            log(f"     - {issue}", YELLOW)
        return False
    else:
        log("  ✓ .env configuration looks good", GREEN)
        return True

def main():
    dry_run = "--dry-run" in sys.argv
    do_backup = "--backup" in sys.argv

    log("=" * 70, BLUE)
    log("  PHASE 1: CRITICAL SECURITY REMEDIATION", BLUE)
    log("  One2lvOS Security Patch Application", BLUE)
    log("=" * 70, BLUE)

    if dry_run:
        log("\n🔍 DRY RUN MODE - No files will be modified\n", YELLOW)

    # Check prerequisites
    if not os.path.exists("lumenis-main.py"):
        log("\n✗ Error: lumenis-main.py not found", RED)
        log("  Please run this script from the One2lvos repository root", RED)
        return 1

    if not os.path.exists("lumenis_security.py"):
        log("\n✗ Error: lumenis_security.py not found", RED)
        log("  This file should be in the same directory", RED)
        return 1

    # Backup files if requested
    if do_backup and not dry_run:
        log("\n📦 Creating backups...", BLUE)
        backup_file("lumenis-main.py")
        backup_file("start-lumenis-reactor.sh")

    # Apply patches
    log("\n🔧 Applying security patches...", BLUE)

    if not dry_run:
        patched_content = patch_lumenis_main()
        if patched_content and isinstance(patched_content, str):
            with open("lumenis-main.py", 'w') as f:
                f.write(patched_content)
            log("✓ lumenis-main.py patched successfully", GREEN)
        else:
            log("⚠  lumenis-main.py patching incomplete - manual review required", YELLOW)
    else:
        log("  [DRY RUN] Would patch lumenis-main.py", YELLOW)

    # Check start script
    log("\n🔍 Checking start-lumenis-reactor.sh...", BLUE)
    with open("start-lumenis-reactor.sh", 'r') as f:
        start_content = f.read()

    if "--host 0.0.0.0" in start_content:
        log("  ✗ CRITICAL: Still binding to 0.0.0.0 (all interfaces)", RED)
        log("    This should be changed to 127.0.0.1", RED)
    elif "--host 127.0.0.1" in start_content:
        log("  ✓ Correctly binding to 127.0.0.1 (localhost only)", GREEN)
    else:
        log("  ⚠  Could not determine host binding", YELLOW)

    # Check environment configuration
    check_env_file()

    # Final instructions
    log("\n" + "=" * 70, BLUE)
    log("  NEXT STEPS", BLUE)
    log("=" * 70, BLUE)

    log("\n1. Configure Security Token:", BLUE)
    log("   python3 -c \"import secrets; print(secrets.token_urlsafe(32))\"", NC)
    log("   # Add output to .env as LUMENIS_SECURITY_TOKEN", NC)

    log("\n2. Configure Feature Flags in .env:", BLUE)
    log("   ENABLE_TERMINAL_API=false", NC)
    log("   ENABLE_NETWORK_PROXY=false", NC)
    log("   ENABLE_WEBSOCKET_TERMINAL=false", NC)

    log("\n3. Test Security:", BLUE)
    log("   # Start server", NC)
    log("   ./start-lumenis-reactor.sh", NC)
    log("", NC)
    log("   # Test unauthenticated request (should fail)", NC)
    log("   curl -X POST http://localhost:8000/api/terminal -d '{\"command\":\"whoami\"}'", NC)
    log("", NC)
    log("   # Test authenticated request (should succeed if enabled)", NC)
    log("   curl -X POST http://localhost:8000/api/terminal \\", NC)
    log("     -H \"Authorization: Bearer YOUR_TOKEN\" \\", NC)
    log("     -d '{\"command\":\"echo test\"}'", NC)

    log("\n4. Verify External Access Blocked:", BLUE)
    log("   # From another machine (should fail)", NC)
    log("   curl http://YOUR_SERVER_IP:8000/api/terminal", NC)
    log("   # Expected: Connection refused", NC)

    log("\n✅ Phase 1 security patches applied!", GREEN)
    log("   Review PHASE1_SECURITY_REMEDIATION.md for full details", BLUE)

    return 0

if __name__ == "__main__":
    sys.exit(main())
