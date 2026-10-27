#!/usr/bin/env python3
"""Test all NVIDIA API keys to find a working one"""

import os
from pathlib import Path
from dotenv import load_dotenv
import httpx

# Load sovereign.env
sovereign_env = Path(__file__).parent / "sovereign_integration" / "config" / "sovereign.env"
load_dotenv(sovereign_env)

# Get all NVIDIA API keys
keys = {
    "PRIMARY": os.environ.get("NVIDIA_API_KEY", ""),
    "SECONDARY": os.environ.get("NVIDIA_API_KEY_SECONDARY", ""),
    "NEMOTRON_SUPER": os.environ.get("NVIDIA_API_KEY_NEMOTRON_SUPER", ""),
    "MINIMAX": os.environ.get("NVIDIA_API_KEY_MINIMAX", ""),
    "STEPFUN": os.environ.get("NVIDIA_API_KEY_STEPFUN", ""),
    "KIMI": os.environ.get("NVIDIA_API_KEY_KIMI", ""),
}

model = "meta/llama-3.2-90b-vision-instruct"

print("=" * 70)
print("TESTING ALL NVIDIA API KEYS")
print("=" * 70)

for name, key in keys.items():
    if not key:
        print(f"\n{name}: NOT SET")
        continue

    masked = key[:10] + "..." + key[-4:] if len(key) > 14 else "***"
    print(f"\n{name}: {masked}")

    try:
        headers = {
            "Authorization": f"Bearer {key}",
            "Content-Type": "application/json"
        }

        payload = {
            "model": model,
            "messages": [{"role": "user", "content": "Hello"}],
            "max_tokens": 10,
            "temperature": 0.18
        }

        with httpx.Client(timeout=10) as client:
            response = client.post(
                "https://integrate.api.nvidia.com/v1/chat/completions",
                headers=headers,
                json=payload
            )

            if response.status_code == 200:
                print(f"  ✓ WORKS! Status: 200 OK")
                print(f"  Use this key: NVIDIA_API_KEY={name}")
            elif response.status_code == 403:
                print(f"  ✗ Forbidden (403) - Key invalid or no access")
            elif response.status_code == 410:
                print(f"  ✗ Model end of life (410)")
            else:
                print(f"  ✗ Error {response.status_code}")

    except Exception as e:
        print(f"  ✗ Error: {e}")

print("\n" + "=" * 70)
