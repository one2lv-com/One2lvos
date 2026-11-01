#!/usr/bin/env python3
"""
Test NVIDIA API Configuration
==============================
Verifies that NVIDIA API key and models are configured correctly
"""

import os
from pathlib import Path
from dotenv import load_dotenv

# Load sovereign.env
sovereign_env = Path(__file__).parent / "sovereign_integration" / "config" / "sovereign.env"
if sovereign_env.exists():
    load_dotenv(sovereign_env)
    print(f"✓ Loaded: {sovereign_env}")
else:
    print(f"✗ Not found: {sovereign_env}")

print("\n" + "=" * 70)
print("NVIDIA API CONFIGURATION TEST")
print("=" * 70)

# Check API key
api_key = os.environ.get("NVIDIA_API_KEY", "")
if api_key:
    masked_key = api_key[:10] + "..." + api_key[-4:] if len(api_key) > 14 else "***"
    print(f"✓ NVIDIA_API_KEY: {masked_key}")
else:
    print("✗ NVIDIA_API_KEY: NOT SET")

# Check models
primary_model = os.environ.get("LLM_PRIMARY_MODEL", "NOT SET")
secondary_model = os.environ.get("LLM_SECONDARY_MODEL", "NOT SET")

print(f"\nConfigured Models:")
print(f"  Primary:   {primary_model}")
print(f"  Secondary: {secondary_model}")

# Check NVIDIA base URL
base_url = os.environ.get("NVIDIA_BASE_URL", "NOT SET")
print(f"\nNVIDIA Base URL: {base_url}")

# Test API connection
print("\n" + "=" * 70)
print("TESTING API CONNECTION")
print("=" * 70)

if not api_key:
    print("\n✗ Cannot test: NVIDIA_API_KEY not set")
    print("\nTo fix:")
    print("  1. Make sure sovereign_integration/config/sovereign.env exists")
    print("  2. Check that NVIDIA_API_KEY is set in that file")
    print("  3. Verify the API key is valid at https://build.nvidia.com")
    exit(1)

try:
    import httpx

    # Test with a simple request
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }

    payload = {
        "model": primary_model,
        "messages": [{"role": "user", "content": "test"}],
        "max_tokens": 10,
        "temperature": 0.18
    }

    print(f"\nTesting model: {primary_model}")
    print("Sending request to NVIDIA API...")

    with httpx.Client(timeout=30) as client:
        response = client.post(
            "https://integrate.api.nvidia.com/v1/chat/completions",
            headers=headers,
            json=payload
        )

        if response.status_code == 200:
            print(f"✓ SUCCESS: API responded with 200 OK")
            print(f"  Model: {primary_model}")
            print(f"  Status: Working correctly")
        elif response.status_code == 404:
            print(f"✗ ERROR 404: Model not found")
            print(f"  Model '{primary_model}' does not exist on NVIDIA API")
            print(f"\nSuggested models to try:")
            print(f"  - meta/llama-3.1-70b-instruct")
            print(f"  - meta/llama-3.1-8b-instruct")
            print(f"  - nvidia/llama-3.1-nemotron-70b-instruct")
            print(f"\nUpdate sovereign.env with: LLM_PRIMARY_MODEL=meta/llama-3.1-70b-instruct")
        else:
            print(f"✗ ERROR {response.status_code}: {response.text[:200]}")

except ImportError:
    print("✗ httpx not installed. Install with: pip install httpx")
except Exception as e:
    print(f"✗ ERROR: {e}")

print("\n" + "=" * 70)
