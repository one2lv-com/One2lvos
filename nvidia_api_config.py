#!/usr/bin/env python3
"""
NVIDIA API Configuration with Auto-Fallback and Model Discovery
Fixes 404 and 410 errors with automatic key rotation and model selection
"""
import os
import json
import requests
from typing import List, Dict, Optional, Tuple

# Multiple NVIDIA API keys for fallback
NVIDIA_API_KEYS = [
    os.environ.get("NVIDIA_API_KEY"),
    os.environ.get("NVIDIA_API_KEY_SECONDARY"),
    os.environ.get("NVIDIA_API_KEY_NEMOTRON_SUPER"),
    os.environ.get("NVIDIA_API_KEY_MINIMAX"),
    os.environ.get("NVIDIA_API_KEY_STEPFUN"),
    os.environ.get("NVIDIA_API_KEY_KIMI"),
]

NVIDIA_BASE_URL = "https://integrate.api.nvidia.com/v1"

# Target embedding dimension for ASTRA DB
TARGET_EMBEDDING_DIM = 2048

class NVIDIAAPIManager:
    """Manages NVIDIA API keys and models with automatic fallback"""

    def __init__(self):
        self.api_keys = [k for k in NVIDIA_API_KEYS if k]
        self.current_key_index = 0
        self.working_embedding_model = None
        self.working_llm_model = None
        self.embedding_dimension = None

    def get_current_key(self) -> str:
        """Get current API key"""
        if not self.api_keys:
            raise ValueError("No NVIDIA API keys configured")
        return self.api_keys[self.current_key_index]

    def rotate_key(self) -> bool:
        """Rotate to next API key. Returns False if no more keys."""
        self.current_key_index += 1
        if self.current_key_index >= len(self.api_keys):
            self.current_key_index = 0
            return False
        return True

    def test_api_key(self, api_key: str) -> bool:
        """Test if an API key is valid"""
        try:
            response = requests.get(
                f"{NVIDIA_BASE_URL}/models",
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "Accept": "application/json"
                },
                timeout=10
            )
            return response.status_code == 200
        except:
            return False

    def list_available_models(self) -> List[Dict]:
        """List all available models with current key"""
        response = requests.get(
            f"{NVIDIA_BASE_URL}/models",
            headers={
                "Authorization": f"Bearer {self.get_current_key()}",
                "Accept": "application/json"
            },
            timeout=10
        )
        if response.status_code == 200:
            return response.json().get("data", [])
        return []

    def test_embedding_model(self, model_id: str) -> Optional[int]:
        """Test embedding model and return dimension. Returns None on failure."""
        try:
            response = requests.post(
                f"{NVIDIA_BASE_URL}/embeddings",
                headers={
                    "Authorization": f"Bearer {self.get_current_key()}",
                    "Content-Type": "application/json"
                },
                json={
                    "input": ["test"],
                    "model": model_id,
                    "encoding_format": "float",
                    "input_type": "query"
                },
                timeout=30
            )

            if response.status_code == 200:
                data = response.json()
                if "data" in data and len(data["data"]) > 0:
                    dim = len(data["data"][0]["embedding"])
                    print(f"✓ {model_id}: {dim} dimensions")
                    return dim
            else:
                error = response.json()
                print(f"✗ {model_id}: {error.get('status')} - {error.get('detail', error.get('message', 'Unknown error'))}")
        except Exception as e:
            print(f"✗ {model_id}: {e}")
        return None

    def find_working_embedding_model(self) -> Optional[Tuple[str, int]]:
        """Find a working embedding model, preferring 2048 dimensions"""
        print(f"\n🔍 Searching for working embedding models...")

        # Priority list of embedding models to try
        candidate_models = [
            "snowflake/arctic-embed-l",
            "nvidia/nemotron-3.5-embed-8b",
            "nvidia/nemotron-3.5-embed-1b",
            "nvidia/nemotron-3-embed-1b",
            "nvidia/llama-3.2-nv-embedqa-1b-v1",
            "nvidia/nv-embedqa-mistral-7b-v2",
            "nvidia/embed-qa-4",
        ]

        results = []
        for model_id in candidate_models:
            dim = self.test_embedding_model(model_id)
            if dim:
                results.append((model_id, dim))
                # If we find exactly 2048, use it immediately
                if dim == TARGET_EMBEDDING_DIM:
                    print(f"\n✅ Found perfect match: {model_id} ({dim} dimensions)")
                    self.working_embedding_model = model_id
                    self.embedding_dimension = dim
                    return (model_id, dim)

        # If no perfect match, use the closest one
        if results:
            # Prefer larger dimensions (can truncate) over smaller
            results.sort(key=lambda x: abs(x[1] - TARGET_EMBEDDING_DIM))
            model_id, dim = results[0]
            print(f"\n⚠️  Using closest match: {model_id} ({dim} dimensions, target: {TARGET_EMBEDDING_DIM})")
            self.working_embedding_model = model_id
            self.embedding_dimension = dim
            return (model_id, dim)

        return None

    def test_llm_model(self, model_id: str) -> bool:
        """Test if LLM model works"""
        try:
            response = requests.post(
                f"{NVIDIA_BASE_URL}/chat/completions",
                headers={
                    "Authorization": f"Bearer {self.get_current_key()}",
                    "Content-Type": "application/json"
                },
                json={
                    "model": model_id,
                    "messages": [{"role": "user", "content": "respond OK"}],
                    "max_tokens": 5,
                    "temperature": 0.1
                },
                timeout=30
            )

            if response.status_code == 200:
                print(f"✓ {model_id}: Working")
                return True
            else:
                error = response.json()
                print(f"✗ {model_id}: {error.get('status')} - {error.get('detail', error.get('message'))}")
        except Exception as e:
            print(f"✗ {model_id}: {e}")
        return False

    def find_working_llm_model(self) -> Optional[str]:
        """Find a working LLM model"""
        print(f"\n🔍 Searching for working LLM models...")

        # Priority list of LLM models
        candidate_models = [
            "nvidia/llama-3.3-nemotron-super-49b-v1",
            "nvidia/llama-3.1-nemotron-70b-instruct",
            "nvidia/nemotron-4-340b-instruct",
            "nvidia/nemotron-3-super-120b-a12b",
            "google/gemma-4-31b-it",
            "meta/llama-3.2-90b-vision-instruct",
        ]

        for model_id in candidate_models:
            if self.test_llm_model(model_id):
                self.working_llm_model = model_id
                return model_id

        return None

    def auto_configure(self) -> Dict[str, any]:
        """Automatically find working configuration"""
        print("🚀 NVIDIA API Auto-Configuration\n")
        print("=" * 60)

        # Test all API keys
        print(f"\n🔑 Testing {len(self.api_keys)} API keys...")
        working_keys = []
        for i, key in enumerate(self.api_keys):
            key_preview = f"{key[:10]}...{key[-4:]}" if key else "None"
            if self.test_api_key(key):
                print(f"  ✓ Key {i+1}: {key_preview} - Working")
                working_keys.append(i)
            else:
                print(f"  ✗ Key {i+1}: {key_preview} - Failed")

        if not working_keys:
            print("\n❌ No working API keys found!")
            return None

        # Use first working key
        self.current_key_index = working_keys[0]
        print(f"\n✅ Using Key {working_keys[0] + 1}")

        # Find working models
        embedding_result = self.find_working_embedding_model()
        llm_result = self.find_working_llm_model()

        config = {
            "api_key_index": self.current_key_index,
            "api_key": self.get_current_key(),
            "embedding_model": embedding_result[0] if embedding_result else None,
            "embedding_dimension": embedding_result[1] if embedding_result else None,
            "llm_model": llm_result if llm_result else None,
            "base_url": NVIDIA_BASE_URL,
        }

        print("\n" + "=" * 60)
        print("📋 FINAL CONFIGURATION")
        print("=" * 60)
        print(f"API Key: Key #{config['api_key_index'] + 1}")
        print(f"Embedding Model: {config['embedding_model']}")
        print(f"Embedding Dimension: {config['embedding_dimension']}")
        print(f"LLM Model: {config['llm_model']}")
        print(f"Base URL: {config['base_url']}")
        print("=" * 60)

        # Save to file
        with open(".env.nvidia_auto", "w") as f:
            f.write(f"# Auto-generated NVIDIA configuration\n")
            f.write(f"NVIDIA_API_KEY={config['api_key']}\n")
            f.write(f"EMBEDDING_MODEL={config['embedding_model']}\n")
            f.write(f"VECTOR_DIM={config['embedding_dimension']}\n")
            f.write(f"LLM_MODEL={config['llm_model']}\n")
            f.write(f"NVIDIA_BASE_URL={config['base_url']}\n")

        print(f"\n💾 Configuration saved to .env.nvidia_auto")

        return config

def main():
    manager = NVIDIAAPIManager()
    config = manager.auto_configure()

    if config:
        print("\n✅ Auto-configuration complete!")
        return 0
    else:
        print("\n❌ Auto-configuration failed!")
        return 1

if __name__ == "__main__":
    exit(main())
