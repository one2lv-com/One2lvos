#!/usr/bin/env python3
"""
Auto-update NVIDIA model IDs in .env with latest available models
Queries NVIDIA API to get current model list and updates configuration

Environment Variables:
  ONE2LVOS_SKIP_MODEL_UPDATE=1    Skip model update entirely
  ONE2LVOS_MODEL_UPDATE_DRY_RUN=1 Show what would be updated without writing
  NVIDIA_API_KEY                  API key for fetching model list

Usage:
  python3 update_nvidia_models.py              # Update .env with latest models
  ONE2LVOS_MODEL_UPDATE_DRY_RUN=1 python3 ... # Preview changes
  ONE2LVOS_SKIP_MODEL_UPDATE=1 python3 ...    # Skip entirely

Note:
  - Prioritizes models accessible on free/basic NVIDIA API tiers
  - Falls back to known good models if API is unavailable
  - Automatically called by startos.sh during boot
  - Get API key from: https://build.nvidia.com/explore/discover
"""

import os
import sys
import json
import time
from pathlib import Path
from typing import Dict, List, Optional

try:
    import requests
except ImportError:
    print("⚠ requests module not installed - skipping NVIDIA model update", file=sys.stderr)
    sys.exit(0)


class NvidiaModelUpdater:
    """Fetch and update NVIDIA model IDs in .env"""

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.getenv("NVIDIA_API_KEY", "")
        self.base_url = "https://integrate.api.nvidia.com/v1"
        self.session = requests.Session()
        if self.api_key:
            self.session.headers.update({
                "Authorization": f"Bearer {self.api_key}",
                "Accept": "application/json"
            })

    def fetch_models(self) -> Dict[str, List[Dict]]:
        """Fetch available models from NVIDIA API"""
        try:
            response = self.session.get(
                f"{self.base_url}/models",
                timeout=10
            )

            if response.status_code == 401:
                print("⚠ NVIDIA API key invalid - using fallback models", file=sys.stderr)
                return self._fallback_models()

            if response.status_code != 200:
                print(f"⚠ NVIDIA API returned {response.status_code} - using fallback", file=sys.stderr)
                return self._fallback_models()

            data = response.json()
            models = data.get("data", [])

            # Categorize models
            categorized = {
                "chat": [],
                "vision": [],
                "embedding": [],
                "reasoning": []
            }

            for model in models:
                model_id = model.get("id", "")
                if not model_id:
                    continue

                # Skip deprecated/EOL models
                if model.get("deprecated", False):
                    continue

                # Categorize by type
                if "embed" in model_id.lower():
                    categorized["embedding"].append(model)
                elif "vision" in model_id.lower() or "vlm" in model_id.lower():
                    categorized["vision"].append(model)
                elif any(kw in model_id.lower() for kw in ["reasoning", "o1", "deepseek-r1"]):
                    categorized["reasoning"].append(model)
                else:
                    categorized["chat"].append(model)

            return categorized

        except requests.exceptions.Timeout:
            print("⚠ NVIDIA API timeout - using fallback models", file=sys.stderr)
            return self._fallback_models()
        except requests.exceptions.RequestException as e:
            print(f"⚠ NVIDIA API error: {e} - using fallback", file=sys.stderr)
            return self._fallback_models()
        except Exception as e:
            print(f"⚠ Unexpected error: {e} - using fallback", file=sys.stderr)
            return self._fallback_models()

    def _fallback_models(self) -> Dict[str, List[Dict]]:
        """Fallback model list when API is unavailable - using widely accessible models"""
        return {
            "chat": [
                {"id": "meta/llama-3.1-8b-instruct", "owned_by": "meta"},
                {"id": "mistralai/mistral-7b-instruct-v0.3", "owned_by": "mistralai"},
                {"id": "google/gemma-2b-it", "owned_by": "google"},
            ],
            "vision": [
                {"id": "microsoft/phi-3-vision-128k-instruct", "owned_by": "microsoft"},
                {"id": "nvidia/vila", "owned_by": "nvidia"},
            ],
            "embedding": [
                {"id": "nvidia/nv-embedqa-e5-v5", "owned_by": "nvidia"},
                {"id": "baai/bge-large-en-v1.5", "owned_by": "baai"},
            ],
            "reasoning": [
                {"id": "meta/llama-3.1-8b-instruct", "owned_by": "meta"},
            ]
        }

    def select_best_models(self, categorized: Dict[str, List[Dict]]) -> Dict[str, str]:
        """Select the best model from each category"""
        selected = {}

        # Primary chat model - prefer models that are widely accessible
        # Prioritize by: free tier > popularity > capability
        if categorized["chat"]:
            # Prioritize models known to work on free tier / basic access
            priority_keywords = [
                "llama-3.1",     # Meta Llama models (widely accessible)
                "llama-3",       # Meta Llama 3 family
                "mistral",       # Mistral models (often accessible)
                "gemma",         # Google Gemma (free tier friendly)
                "phi",           # Microsoft Phi (lightweight, accessible)
                "nemotron",      # NVIDIA Nemotron
                "llama",         # Any Llama model
            ]
            chat_models = categorized["chat"]

            best_chat = None
            for keyword in priority_keywords:
                for model in chat_models:
                    model_id_lower = model["id"].lower()
                    if keyword in model_id_lower:
                        # Skip very large models that often require special access
                        if any(size in model_id_lower for size in ["405b", "70b-instruct"]):
                            continue
                        best_chat = model
                        break
                if best_chat:
                    break

            # Fallback to any available chat model
            if not best_chat and chat_models:
                best_chat = chat_models[0]

            if best_chat:
                selected["LLM_MODEL"] = best_chat["id"]
                selected["LLM_PRIMARY_MODEL"] = best_chat["id"]

        # Vision model
        if categorized["vision"]:
            # Prefer phi-3-vision or llama-vision
            vision_priority = ["phi-3-vision", "llama", "nemotron"]
            best_vision = None

            for keyword in vision_priority:
                for model in categorized["vision"]:
                    if keyword in model["id"].lower():
                        best_vision = model
                        break
                if best_vision:
                    break

            if not best_vision and categorized["vision"]:
                best_vision = categorized["vision"][0]

            if best_vision:
                selected["LLM_VISION_MODEL"] = best_vision["id"]

        # Embedding model
        if categorized["embedding"]:
            # Prefer nv-embedqa or nemotron-embed
            embed_priority = ["embedqa-e5-v5", "nemotron-3-embed"]
            best_embed = None

            for keyword in embed_priority:
                for model in categorized["embedding"]:
                    if keyword in model["id"].lower():
                        best_embed = model
                        break
                if best_embed:
                    break

            if not best_embed and categorized["embedding"]:
                best_embed = categorized["embedding"][0]

            if best_embed:
                selected["EMBEDDING_MODEL"] = best_embed["id"]

        # Secondary/reasoning model
        if categorized["reasoning"]:
            selected["LLM_SECONDARY_MODEL"] = categorized["reasoning"][0]["id"]
        elif categorized["chat"] and len(categorized["chat"]) > 1:
            selected["LLM_SECONDARY_MODEL"] = categorized["chat"][1]["id"]

        return selected

    def update_env_file(self, env_path: Path, updates: Dict[str, str], dry_run: bool = False) -> bool:
        """Update .env file with new model IDs"""
        if not env_path.exists():
            print(f"⚠ .env file not found at {env_path}", file=sys.stderr)
            return False

        try:
            with open(env_path, 'r', encoding='utf-8') as f:
                lines = f.readlines()

            updated_lines = []
            updated_keys = set()

            for line in lines:
                stripped = line.strip()

                # Skip comments and empty lines
                if not stripped or stripped.startswith('#'):
                    updated_lines.append(line)
                    continue

                # Check if this line contains a key we want to update
                if '=' in line:
                    key = line.split('=')[0].strip()
                    if key in updates:
                        # Update this line
                        updated_lines.append(f"{key}={updates[key]}\n")
                        updated_keys.add(key)
                        continue

                updated_lines.append(line)

            # Add any keys that weren't in the file
            for key, value in updates.items():
                if key not in updated_keys:
                    updated_lines.append(f"\n# Auto-updated by NVIDIA model fetcher\n")
                    updated_lines.append(f"{key}={value}\n")
                    updated_keys.add(key)

            if dry_run:
                print("Would update:", file=sys.stderr)
                for key in updated_keys:
                    print(f"  {key}={updates[key]}", file=sys.stderr)
                return True

            # Write back
            with open(env_path, 'w', encoding='utf-8') as f:
                f.writelines(updated_lines)

            return True

        except Exception as e:
            print(f"⚠ Error updating .env: {e}", file=sys.stderr)
            return False


def main():
    """Main entry point"""
    # Check if we should skip
    if os.getenv("ONE2LVOS_SKIP_MODEL_UPDATE") == "1":
        print("⏭ NVIDIA model update skipped (ONE2LVOS_SKIP_MODEL_UPDATE=1)", file=sys.stderr)
        sys.exit(0)

    # Get paths
    root_dir = Path(__file__).parent.resolve()
    env_path = root_dir / ".env"

    # Load API key from .env if it exists
    api_key = os.getenv("NVIDIA_API_KEY")
    if not api_key and env_path.exists():
        try:
            with open(env_path, 'r') as f:
                for line in f:
                    if line.strip().startswith('NVIDIA_API_KEY='):
                        api_key = line.split('=', 1)[1].strip()
                        break
        except:
            pass

    # Initialize updater
    updater = NvidiaModelUpdater(api_key)

    # Fetch models
    print("  🔍 Fetching latest NVIDIA models...", file=sys.stderr)
    categorized = updater.fetch_models()

    # Count available models
    total_models = sum(len(models) for models in categorized.values())
    if total_models == 0:
        print("  ⚠ No models available - keeping existing configuration", file=sys.stderr)
        sys.exit(0)

    print(f"  ✓ Found {total_models} available models", file=sys.stderr)

    # Select best models
    selected = updater.select_best_models(categorized)

    if not selected:
        print("  ⚠ Could not select models - keeping existing configuration", file=sys.stderr)
        sys.exit(0)

    # Update .env
    dry_run = os.getenv("ONE2LVOS_MODEL_UPDATE_DRY_RUN") == "1"

    if updater.update_env_file(env_path, selected, dry_run=dry_run):
        if not dry_run:
            print(f"  ✓ Updated {len(selected)} model configurations", file=sys.stderr)
            for key, value in selected.items():
                print(f"    • {key}={value}", file=sys.stderr)
        sys.exit(0)
    else:
        print("  ⚠ Failed to update .env - keeping existing configuration", file=sys.stderr)
        sys.exit(0)


if __name__ == "__main__":
    main()
