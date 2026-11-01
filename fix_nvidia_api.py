#!/usr/bin/env python3
"""
NVIDIA API Fix
==============
Fixes the 404 error by updating to correct NVIDIA NIM endpoints
"""

import os
import httpx
import json

# Test working NVIDIA models and endpoints
WORKING_MODELS = [
    "meta/llama-3.1-8b-instruct",
    "meta/llama-3.1-70b-instruct",
    "nvidia/llama-3.1-nemotron-70b-instruct",
    "mistralai/mixtral-8x7b-instruct-v0.1",
]

API_KEY = os.environ.get("NVIDIA_API_KEY", "")

async def test_model(model: str):
    """Test if a model works with current API key"""
    url = "https://integrate.api.nvidia.com/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {API_KEY}",
        "Content-Type": "application/json"
    }
    payload = {
        "model": model,
        "messages": [{"role": "user", "content": "test"}],
        "max_tokens": 10,
        "temperature": 0.1,
        "stream": False
    }

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.post(url, headers=headers, json=payload)
            if resp.status_code == 200:
                print(f"✅ {model} - OK")
                return True
            else:
                print(f"❌ {model} - {resp.status_code}: {resp.text[:100]}")
                return False
    except Exception as e:
        print(f"⚠️  {model} - Error: {e}")
        return False

async def main():
    print("🔧 Testing NVIDIA API models...")
    print(f"API Key: {API_KEY[:20]}...{API_KEY[-10:]}")
    print("")

    working = []
    for model in WORKING_MODELS:
        if await test_model(model):
            working.append(model)

    print("")
    print(f"✅ Working models: {len(working)}/{len(WORKING_MODELS)}")
    if working:
        print(f"Recommended: {working[0]}")
        print("")
        print("Update your .env:")
        print(f'LLM_MODEL={working[0]}')

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
