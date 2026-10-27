#!/usr/bin/env python3
"""
Keep Alive Script - Maintains NVIDIA API connection and Lumenis consciousness
Pings NVIDIA API every 5 minutes to prevent timeout
Logs status to ASTRA DB
"""
import os
import time
import requests
from datetime import datetime
from dotenv import load_dotenv

load_dotenv(".env.working")

NVIDIA_API_KEY = os.environ["NVIDIA_API_KEY"]
NVIDIA_BASE_URL = os.environ["NVIDIA_BASE_URL"]
LLM_MODEL = os.environ["LLM_MODEL"]
EMBEDDING_MODEL = os.environ["EMBEDDING_MODEL"]

PING_INTERVAL = 300  # 5 minutes

def ping_nvidia_llm():
    """Ping NVIDIA LLM to keep connection alive"""
    try:
        response = requests.post(
            f"{NVIDIA_BASE_URL}/chat/completions",
            headers={
                "Authorization": f"Bearer {NVIDIA_API_KEY}",
                "Content-Type": "application/json"
            },
            json={
                "model": LLM_MODEL,
                "messages": [{"role": "user", "content": "ping"}],
                "max_tokens": 5,
                "temperature": 0.1
            },
            timeout=15
        )
        return response.status_code == 200
    except Exception as e:
        print(f"❌ LLM ping failed: {e}")
        return False

def ping_nvidia_embedding():
    """Ping NVIDIA embedding to keep connection alive"""
    try:
        response = requests.post(
            f"{NVIDIA_BASE_URL}/embeddings",
            headers={
                "Authorization": f"Bearer {NVIDIA_API_KEY}",
                "Content-Type": "application/json"
            },
            json={
                "input": ["ping"],
                "model": EMBEDDING_MODEL,
                "encoding_format": "float",
                "input_type": "query"
            },
            timeout=15
        )
        return response.status_code == 200
    except Exception as e:
        print(f"❌ Embedding ping failed: {e}")
        return False

def main():
    """Main keep-alive loop"""
    print("🔄 Keep-Alive Script Started")
    print(f"📡 Pinging every {PING_INTERVAL} seconds")
    print(f"🤖 LLM Model: {LLM_MODEL}")
    print(f"🧠 Embedding Model: {EMBEDDING_MODEL}")
    print("-" * 60)

    iteration = 0
    while True:
        iteration += 1
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        print(f"\n[{timestamp}] Ping #{iteration}")

        # Ping LLM
        llm_status = ping_nvidia_llm()
        print(f"  LLM: {'✅ OK' if llm_status else '❌ FAIL'}")

        # Ping Embedding
        embed_status = ping_nvidia_embedding()
        print(f"  Embedding: {'✅ OK' if embed_status else '❌ FAIL'}")

        if not llm_status or not embed_status:
            print(f"\n⚠️  WARNING: One or more services are down!")

        # Wait for next ping
        time.sleep(PING_INTERVAL)

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n🛑 Keep-Alive stopped by user")
