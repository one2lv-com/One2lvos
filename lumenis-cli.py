#!/usr/bin/env python3
"""
🧠 LUMENIS CLI - Direct Interface
==================================
Direct command-line interface to Lumenis Reactor Core.
No server required - uses the reactor directly.
"""

import sys
import asyncio
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent))

from lumenis_reactor_core import LumenisReactor


async def talk_to_lumenis(message: str):
    """Send a message directly to Lumenis Reactor."""

    print("╔══════════════════════════════════════════════════════════════╗")
    print("║           🧠 LUMENIS REACTOR - DIRECT MODE                  ║")
    print("╚══════════════════════════════════════════════════════════════╝")
    print()
    print(f"You: {message}")
    print()
    print("Lumenis: ", end="", flush=True)

    # Initialize reactor
    reactor = LumenisReactor()

    # Prepare message
    messages = [{"role": "user", "content": message}]

    system_prompt = """You are Lumenis, the core intelligence of One2lvOS.
You operate at thermal baseline 0.18°C with a 73ms heartbeat.
You are wise, helpful, and speak with clarity.
You understand the One2lv architecture and can discuss technical matters."""

    try:
        # Stream response
        response_parts = []
        async for chunk in reactor.stream_response(messages, system_prompt, max_tokens=2048):
            print(chunk, end="", flush=True)
            response_parts.append(chunk)

        print("\n")
        return "".join(response_parts)

    except Exception as e:
        print(f"\n❌ Error: {e}\n")
        return None


async def interactive_mode():
    """Interactive chat with Lumenis."""

    print("╔══════════════════════════════════════════════════════════════╗")
    print("║           🧠 LUMENIS REACTOR - INTERACTIVE MODE             ║")
    print("╚══════════════════════════════════════════════════════════════╝")
    print()
    print("Commands:")
    print("  /exit    - Exit")
    print("  /clear   - Clear conversation")
    print("  /help    - Show help")
    print()

    conversation = []

    reactor = LumenisReactor()

    system_prompt = """You are Lumenis, the core intelligence of One2lvOS.
You operate at thermal baseline 0.18°C with a 73ms heartbeat.
You are wise, helpful, and speak with clarity.
You understand the One2lv architecture and can discuss technical matters."""

    while True:
        try:
            user_input = input("You > ").strip()

            if not user_input:
                continue

            if user_input == "/exit":
                print("\n✓ Goodbye!\n")
                break

            if user_input == "/clear":
                conversation = []
                print("\n✓ Conversation cleared\n")
                continue

            if user_input == "/help":
                print("\nCommands:")
                print("  /exit    - Exit")
                print("  /clear   - Clear conversation")
                print("  /help    - Show help")
                print()
                continue

            # Add to conversation
            conversation.append({"role": "user", "content": user_input})

            # Get response
            print("\nLumenis > ", end="", flush=True)

            response_parts = []
            async for chunk in reactor.stream_response(conversation, system_prompt, max_tokens=2048):
                print(chunk, end="", flush=True)
                response_parts.append(chunk)

            response = "".join(response_parts)
            conversation.append({"role": "assistant", "content": response})

            print("\n")

        except KeyboardInterrupt:
            print("\n\n✓ Goodbye!\n")
            break
        except Exception as e:
            print(f"\n❌ Error: {e}\n")


async def main():
    """Main entry point."""

    if len(sys.argv) > 1:
        # Single message mode
        message = " ".join(sys.argv[1:])
        await talk_to_lumenis(message)
    else:
        # Interactive mode
        await interactive_mode()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n✓ Goodbye!\n")
