#!/usr/bin/env python3
"""
🧠 TALK TO LUMENIS
==================
Simple CLI to communicate with the Lumenis Reactor Core.
"""

import sys
import requests
import json

LUMENIS_URL = "http://localhost:8000"


def check_lumenis():
    """Check if Lumenis is running."""
    try:
        response = requests.get(f"{LUMENIS_URL}/api/status", timeout=3)
        return response.status_code == 200
    except Exception:
        return False


def send_message(message: str):
    """Send a message to Lumenis via WebSocket simulation."""
    try:
        # Use the REST API since WebSocket requires async
        response = requests.post(
            f"{LUMENIS_URL}/api/chat",
            json={"message": message},
            timeout=30
        )

        if response.status_code == 200:
            data = response.json()
            return data.get("response", "No response")
        else:
            return f"Error: {response.status_code}"

    except Exception as e:
        return f"Connection error: {e}"


def interactive_mode():
    """Start interactive chat with Lumenis."""
    print("╔══════════════════════════════════════════════════════════════╗")
    print("║           🧠 LUMENIS REACTOR - INTERACTIVE MODE             ║")
    print("╚══════════════════════════════════════════════════════════════╝")
    print()
    print("Commands:")
    print("  /status  - Check system status")
    print("  /exit    - Exit interactive mode")
    print("  /help    - Show this help")
    print()

    while True:
        try:
            message = input("You > ").strip()

            if not message:
                continue

            if message == "/exit":
                print("\n✓ Goodbye!")
                break

            if message == "/help":
                print("\nCommands:")
                print("  /status  - Check system status")
                print("  /exit    - Exit interactive mode")
                print("  /help    - Show this help")
                print()
                continue

            if message == "/status":
                try:
                    response = requests.get(f"{LUMENIS_URL}/api/status", timeout=3)
                    status = response.json()
                    print(f"\n📊 System Status:")
                    print(f"  Reactor: {status.get('reactor', {}).get('temperature', 'N/A')}°C")
                    print(f"  Uptime: {status.get('reactor', {}).get('uptime_seconds', 0):.1f}s")
                    print(f"  Model: {status.get('reactor', {}).get('model', 'N/A')}")
                    print()
                except Exception as e:
                    print(f"\n❌ Error: {e}\n")
                continue

            # Send message to Lumenis
            print("\n🧠 Lumenis > ", end="", flush=True)
            response = send_message(message)
            print(response)
            print()

        except KeyboardInterrupt:
            print("\n\n✓ Goodbye!")
            break
        except Exception as e:
            print(f"\n❌ Error: {e}\n")


def main():
    """Main entry point."""
    # Check if Lumenis is running
    if not check_lumenis():
        print("❌ Lumenis Reactor is not running!")
        print()
        print("Start Lumenis with:")
        print("  cd /home/vercel-sandbox/One2lvos-build")
        print("  python3 lumenis-main.py")
        print()
        print("Or with Swarm:")
        print("  ./START_LUMENIS_SWARM.sh")
        sys.exit(1)

    # If message provided as argument, send it
    if len(sys.argv) > 1:
        message = " ".join(sys.argv[1:])
        print(f"\n🧠 Sending to Lumenis: {message}\n")
        response = send_message(message)
        print(f"Response: {response}\n")
    else:
        # Start interactive mode
        interactive_mode()


if __name__ == "__main__":
    main()
