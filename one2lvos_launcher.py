#!/usr/bin/env python3
"""
One2lvOS System Launcher
Launches all One2lvOS services and provides system control
Can be compiled to .exe with PyInstaller
"""

import subprocess
import sys
import os
import time
import threading
import signal
from pathlib import Path
from typing import List, Tuple

# Detect if running as compiled executable
if getattr(sys, 'frozen', False):
    RUNNING_AS_EXE = True
    BASE_DIR = Path(os.path.expanduser('~/One2lvOS'))
else:
    RUNNING_AS_EXE = False
    BASE_DIR = Path(__file__).parent

# Configuration
SERVICES = [
    ("AI Arcade MCP", ["ai-arcade/server.py"], 8003),
    ("One2lvOS Core", ["-m", "flask", "run", "--host", "0.0.0.0", "--port", "3002", "--app", "One2lvos/core_service.py"], 3002),
    ("Sovereign Agentic Core", ["-m", "uvicorn", "main:app", "--host", "0.0.0.0", "--port", "3003", "--app-dir", "sovereign-agentic-core"], 3003),
    ("AI Lobby", ["-m", "uvicorn", "ai_lobby:app", "--host", "0.0.0.0", "--port", "8006"], 8006),
    ("Unified Gateway", ["-m", "uvicorn", "unified_gateway:app", "--host", "0.0.0.0", "--port", "8888"], 8888),
]

OPTIONAL_SERVICES = [
    ("Lumenis v7 Cosmic", "node", ["steamos_lumenis/lumenis-v7-cjs/server.js"], 8005),
    ("SteamOS Dashboard", "python", ["steamos_lumenis/one2lvos_dashboard/server.py"], 8080),
    ("Lumenis Space UI", "python", ["-m", "http.server", "9001", "--directory", "Lumenis/frontend"], 9001),
    ("LumenisOS API", "node", ["lumenis-os/artifacts/api-server/dist/index.mjs"], 9002),
    ("Aetherix Terminal", "python", ["Aetherix/server.py"], 9003),
]

processes: List[Tuple[str, subprocess.Popen]] = []
shutdown_requested = False


def clear_screen():
    """Clear console screen"""
    os.system('cls' if os.name == 'nt' else 'clear')


def print_banner():
    """Print startup banner"""
    clear_screen()
    print("=" * 72)
    print("   ONE2LVOS - Unified AI Operating System")
    print("=" * 72)
    print()


def check_port_available(port: int) -> bool:
    """Check if a port is available"""
    import socket
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.bind(('127.0.0.1', port))
            return True
    except OSError:
        return False


def kill_port(port: int):
    """Kill process using specified port"""
    if os.name == 'nt':
        try:
            result = subprocess.run(
                f'netstat -ano | findstr :{port}',
                shell=True,
                capture_output=True,
                text=True
            )
            if result.stdout:
                lines = result.stdout.strip().split('\n')
                for line in lines:
                    parts = line.split()
                    if len(parts) >= 5 and 'LISTENING' in line:
                        pid = parts[-1]
                        subprocess.run(f'taskkill /F /PID {pid}', shell=True, capture_output=True)
        except:
            pass


def start_service(name: str, args: List[str], port: int, cmd: str = "python") -> subprocess.Popen:
    """Start a single service"""
    # Kill any process on the port first
    if not check_port_available(port):
        print(f"   Port {port} in use, clearing...")
        kill_port(port)
        time.sleep(1)

    try:
        if cmd == "python":
            command = [sys.executable] + args
        else:
            command = [cmd] + args

        # Create process with no window on Windows
        if sys.platform == 'win32':
            proc = subprocess.Popen(
                command,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                creationflags=subprocess.CREATE_NO_WINDOW
            )
        else:
            proc = subprocess.Popen(
                command,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL
            )

        return proc
    except Exception as e:
        print(f"   Warning: Failed to start {name}: {e}")
        return None


def start_all_services():
    """Start all One2lvOS services"""
    print_banner()
    print("Starting services...\n")

    os.chdir(BASE_DIR)

    # Start core services
    for i, (name, args, port) in enumerate(SERVICES, 1):
        print(f"[{i}/{len(SERVICES)}] Starting {name} [port {port}]...")
        proc = start_service(name, args, port)
        if proc:
            processes.append((name, proc))
        time.sleep(1.5)

    # Start optional services if they exist
    print("\nStarting optional services...\n")
    for name, cmd, args, port in OPTIONAL_SERVICES:
        # Check if service directory/file exists
        service_file = Path(args[0]) if args else None
        if service_file and service_file.exists():
            print(f"   Starting {name} [port {port}]...")
            proc = start_service(name, args, port, cmd)
            if proc:
                processes.append((name, proc))
            time.sleep(1)

    print()
    print("=" * 72)
    print("   ONE2LVOS SYSTEM IS NOW RUNNING!")
    print("=" * 72)
    print()
    print("   Unified Gateway:  http://localhost:8888")
    print("   System Status:    http://localhost:8888/status")
    print("   AI Arcade MCP:    http://localhost:8003")
    print("   AI Lobby:         http://localhost:8006")
    print()
    print(f"   Running {len(processes)} services")
    print()
    print("   Press Ctrl+C to stop all services...")
    print("=" * 72)
    print()


def open_browser():
    """Open system dashboard in browser"""
    time.sleep(3)
    try:
        import webbrowser
        webbrowser.open('http://localhost:8888/status')
    except Exception as e:
        print(f"   Could not open browser: {e}")


def signal_handler(sig, frame):
    """Handle Ctrl+C gracefully"""
    global shutdown_requested
    if not shutdown_requested:
        shutdown_requested = True
        print("\n\nShutdown requested...")
        stop_all_services()
        sys.exit(0)


def stop_all_services():
    """Stop all running services"""
    print("\nStopping all services...\n")

    for name, proc in processes:
        try:
            print(f"   Stopping {name}...")
            proc.terminate()
            try:
                proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                proc.kill()
        except Exception as e:
            print(f"   Warning: Error stopping {name}: {e}")

    print("\nAll services stopped.")
    time.sleep(1)


def monitor_services():
    """Monitor services and restart if they crash"""
    while not shutdown_requested:
        time.sleep(5)
        for i, (name, proc) in enumerate(processes):
            if proc.poll() is not None:
                print(f"\n   Warning: {name} has stopped unexpectedly")
                # Could implement auto-restart here
        time.sleep(5)


def main():
    """Main entry point"""
    global shutdown_requested

    # Check if installation exists
    if not BASE_DIR.exists():
        print("=" * 72)
        print("   ERROR: One2lvOS installation not found!")
        print("=" * 72)
        print()
        print(f"   Expected location: {BASE_DIR}")
        print()
        print("   Please run the installer first:")
        print("   install-one2lvos-windows-auto.bat")
        print()
        input("   Press Enter to exit...")
        sys.exit(1)

    # Register signal handler
    signal.signal(signal.SIGINT, signal_handler)

    # Start services
    start_all_services()

    # Open browser in background
    browser_thread = threading.Thread(target=open_browser, daemon=True)
    browser_thread.start()

    # Monitor services in background
    monitor_thread = threading.Thread(target=monitor_services, daemon=True)
    monitor_thread.start()

    # Main loop
    try:
        while not shutdown_requested:
            time.sleep(1)
    except KeyboardInterrupt:
        pass
    finally:
        if not shutdown_requested:
            stop_all_services()


if __name__ == '__main__':
    main()
