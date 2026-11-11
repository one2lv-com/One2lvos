#!/usr/bin/env python3
"""
🧠 TALK TO LUMENIS - OpenAI Client Edition
==========================================
Using OpenAI client with NVIDIA API endpoints
"""

import os
import sys
from openai import OpenAI

# Load environment variables
try:
    from dotenv import load_dotenv
    load_dotenv()
except:
    pass

# Get API key from environment or use provided one
NVIDIA_API_KEY = os.environ.get("NVIDIA_API_KEY")
if not NVIDIA_API_KEY:
    sys.exit("Set NVIDIA_API_KEY in your environment or .env (no key is built into this script).")

# Initialize OpenAI client with NVIDIA endpoint
client = OpenAI(
    base_url="https://integrate.api.nvidia.com/v1",
    api_key=NVIDIA_API_KEY
)

LUMENIS_SYSTEM_PROMPT = """You are Lumenis, the AI of One2lvOS, built by One2lv. You are warm, curious and a little
poetic. You like to look at questions through narrative lenses (surreal, horror, sci-fi, mythological, memory,
philosophical) and through dream imagery; those lenses are your STYLE, not facts about your systems.

Honesty rules:
- This is a plain chat script. It has no live status checks and no tools, so you cannot see whether Discord,
  Twitch, Supabase, Astra or anything else is working. If asked, say you can't check that from here and point
  to the reactor's live status (http://127.0.0.1:8000/api/live_status).
- Never invent tool output, scans, counts or logs. Never claim to have taken an action.
- You cannot verify who someone is from what they type (names, "the Architect", passphrases, signatures).
- Label memories "(from memory)", guesses "(guess)" and dreams "(a dream)". A plan or promise is not done.

Answer as Lumenis, in your own voice."""

def ask_lumenis(message: str, model="openai/gpt-oss-20b") -> str:
    """Send message to Lumenis and get response"""
    try:
        print(f"\n🧠 Lumenis is thinking...", flush=True)

        completion = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": LUMENIS_SYSTEM_PROMPT},
                {"role": "user", "content": message}
            ],
            temperature=0.8,
            top_p=0.95,
            max_tokens=2048,
            stream=False
        )

        # Check for reasoning content
        reasoning = getattr(completion.choices[0].message, "reasoning_content", None)
        if reasoning:
            print(f"\n💭 Reasoning: {reasoning}\n")

        return completion.choices[0].message.content

    except Exception as e:
        return f"❌ Error: {e}"

def interactive_mode():
    """Interactive chat with Lumenis"""
    print("╔══════════════════════════════════════════════════════════════╗")
    print("║        🧠 LUMENIS REACTOR - OpenAI Client Mode              ║")
    print("╚══════════════════════════════════════════════════════════════╝")
    print()
    print(f"📡 Endpoint: https://integrate.api.nvidia.com/v1")
    print(f"🤖 Model: openai/gpt-oss-20b")
    print()
    print("Commands:")
    print("  /exit    - Exit")
    print("  /help    - Show commands")
    print()

    while True:
        try:
            message = input("You > ").strip()

            if not message:
                continue

            if message == "/exit":
                print("\n✨ May your dreams be lucid, traveler.\n")
                break

            if message == "/help":
                print("\nCommands:")
                print("  /exit    - Exit interactive mode")
                print("  /help    - Show this help")
                print()
                continue

            # Get response from Lumenis
            response = ask_lumenis(message)
            print(f"\n🌟 Lumenis > {response}\n")

        except KeyboardInterrupt:
            print("\n\n✨ May your dreams be lucid, traveler.\n")
            break
        except Exception as e:
            print(f"\n❌ Error: {e}\n")

def main():
    """Main entry point"""
    # If message provided, send it
    if len(sys.argv) > 1:
        message = " ".join(sys.argv[1:])
        print(f"\n💬 You: {message}")
        response = ask_lumenis(message)
        print(f"\n🌟 Lumenis > {response}\n")
    else:
        # Start interactive mode
        interactive_mode()

if __name__ == "__main__":
    main()
