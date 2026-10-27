#!/usr/bin/env python3
"""Setup GitHub Secrets for One2lvOS CI/CD"""
import os
import sys
import base64
import requests
from nacl import encoding, public

# GitHub configuration - set via environment variables
GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN")
REPO = "one2lv-com/One2lvos"

# Secrets to add - loaded from environment variables
SECRETS = {
    "NVIDIA_API_KEY": os.environ.get("NVIDIA_API_KEY"),
    "ASTRA_DB_APPLICATION_TOKEN": os.environ.get("ASTRA_DB_APPLICATION_TOKEN"),
    "ASTRA_DB_API_ENDPOINT": os.environ.get("ASTRA_DB_API_ENDPOINT"),
    "DISCORD_BOT_TOKEN": os.environ.get("DISCORD_BOT_TOKEN"),
    "DISCORD_WEBHOOK_URL": os.environ.get("DISCORD_WEBHOOK_URL"),
    "SUPABASE_SERVICE_KEY": os.environ.get("SUPABASE_SERVICE_KEY"),
    "SUPABASE_URL": os.environ.get("SUPABASE_URL"),
    "MATON_API_KEY": os.environ.get("MATON_API_KEY"),
}

def encrypt_secret(public_key: str, secret_value: str) -> str:
    """Encrypt a secret using the repository public key."""
    public_key_bytes = base64.b64decode(public_key)
    sealed_box = public.SealedBox(public.PublicKey(public_key_bytes))
    encrypted = sealed_box.encrypt(secret_value.encode("utf-8"))
    return base64.b64encode(encrypted).decode("utf-8")

def get_public_key():
    """Get the repository's public key for encrypting secrets."""
    url = f"https://api.github.com/repos/{REPO}/actions/secrets/public-key"
    headers = {
        "Authorization": f"token {GITHUB_TOKEN}",
        "Accept": "application/vnd.github.v3+json"
    }
    response = requests.get(url, headers=headers)
    response.raise_for_status()
    return response.json()

def set_secret(secret_name: str, encrypted_value: str, key_id: str):
    """Set a repository secret."""
    url = f"https://api.github.com/repos/{REPO}/actions/secrets/{secret_name}"
    headers = {
        "Authorization": f"token {GITHUB_TOKEN}",
        "Accept": "application/vnd.github.v3+json"
    }
    data = {
        "encrypted_value": encrypted_value,
        "key_id": key_id
    }
    response = requests.put(url, headers=headers, json=data)
    return response.status_code in (201, 204)

def main():
    print("🔐 Setting up GitHub Secrets for One2lvOS...")

    # Validate required environment variables
    if not GITHUB_TOKEN:
        print("❌ Error: GITHUB_TOKEN environment variable not set")
        sys.exit(1)

    missing_secrets = [k for k, v in SECRETS.items() if not v]
    if missing_secrets:
        print(f"❌ Error: Missing environment variables: {', '.join(missing_secrets)}")
        sys.exit(1)

    # Get public key
    print("\n📡 Fetching repository public key...")
    key_data = get_public_key()
    public_key = key_data["key"]
    key_id = key_data["key_id"]
    print(f"✓ Got public key (ID: {key_id})")

    # Add each secret
    print(f"\n🔑 Adding {len(SECRETS)} secrets...")
    success_count = 0

    for secret_name, secret_value in SECRETS.items():
        try:
            encrypted = encrypt_secret(public_key, secret_value)
            if set_secret(secret_name, encrypted, key_id):
                print(f"  ✓ {secret_name}")
                success_count += 1
            else:
                print(f"  ✗ {secret_name} - Failed")
        except Exception as e:
            print(f"  ✗ {secret_name} - Error: {e}")

    print(f"\n✅ Successfully added {success_count}/{len(SECRETS)} secrets")
    print(f"\n🔗 View secrets at: https://github.com/{REPO}/settings/secrets/actions")

if __name__ == "__main__":
    main()
