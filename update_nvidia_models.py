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
  - Never selects safety/guard/classifier models (nemoguard, content-safety, topic-control ...)
  - Keeps a current model that is listed and answers a live chat test; otherwise live-tests candidates
  - Keeps the existing configuration if the API is unavailable
  ONE2LVOS_MODEL_UPDATE_NO_LIVE_TEST=1  never change models (no live tests run)
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

# Shared rule with the reactor: lumenis_reactor_core/model_guard.py (loaded by path, no package import).
import importlib.util as _ilu
_mg_spec = _ilu.spec_from_file_location(
    "_model_guard", Path(__file__).resolve().parent / "lumenis_reactor_core" / "model_guard.py")
_mg = _ilu.module_from_spec(_mg_spec)
_mg_spec.loader.exec_module(_mg)
is_safety_model = _mg.is_safety_model
is_chat_candidate = _mg.is_chat_candidate


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
        """API unavailable: return nothing, so the existing configuration is kept. (The old canned list
        wrote models that were never tested, e.g. microsoft/phi-3-vision-128k-instruct, now gone.)"""
        return {"chat": [], "vision": [], "embedding": [], "reasoning": []}

    # Owner's rule (2026-11-16): no safety / guard / classifier model is ever picked for a chat seat.
    # The old picker took the first model whose id contained "llama-3.1"; in NVIDIA's list that was
    # nvidia/llama-3.1-nemoguard-8b-content-safety, later ...-topic-control (HTTP 500 on chat), and it
    # never tested a model before writing it (it also wrote microsoft/phi-3-vision-128k-instruct, gone: 410).
    PREFERRED = {
        "LLM_PRIMARY_MODEL": ["nvidia/nemotron-3.5-super-vl-120b-a12b", "nvidia/nemotron-3-ultra-550b-a55b",
                              "nvidia/nemotron-3.5-lightning-30b-a3b", "nvidia/nemotron-3.5-bolt-e4b"],
        "LLM_SECONDARY_MODEL": ["nvidia/nemotron-3-ultra-550b-a55b", "nvidia/nemotron-3.5-lightning-30b-a3b",
                                "nvidia/nemotron-3-nano-omni-30b-a3b-reasoning", "nvidia/nemotron-3.5-bolt-e4b"],
        "LLM_VISION_MODEL": ["nvidia/nemotron-3.5-super-vl-120b-a12b"],
    }
    KEYWORDS = ["nemotron", "llama-3.3", "llama-4", "mistral", "qwen", "gemma", "llama"]

    def live_chat_ok(self, model_id: str, timeout: float = 25.0) -> bool:
        """One tiny chat request; True only for HTTP 200 with a non-empty answer."""
        if not self.api_key or os.getenv("ONE2LVOS_MODEL_UPDATE_NO_LIVE_TEST") == "1":
            return False
        try:
            r = self.session.post(f"{self.base_url}/chat/completions", timeout=timeout, json={
                "model": model_id, "max_tokens": 300, "temperature": 0, "stream": False,
                "messages": [{"role": "user", "content": "Reply with the single word: ready"}]})
            if r.status_code != 200:
                return False
            msg = (r.json().get("choices") or [{}])[0].get("message") or {}
            return bool((msg.get("content") or "").strip())
        except Exception:
            return False

    def _candidates(self, key: str, listed: List[str], current: str) -> List[str]:
        out: List[str] = []
        def add(m):
            if m and m in listed and is_chat_candidate(m) and m not in out:
                out.append(m)
        add(current)
        for m in self.PREFERRED.get(key, []):
            add(m)
        for kw in self.KEYWORDS:
            for m in listed:
                if kw in m.lower() and not any(sz in m.lower() for sz in ("405b", "70b-instruct")):
                    add(m)
        return out

    def select_best_models(self, categorized: Dict[str, List[Dict]], current: Optional[Dict[str, str]] = None,
                           max_tries: int = 4) -> Dict[str, str]:
        """Pick a working model per setting. The current value is kept when it is listed, is not a safety
        model and answers a live test. Otherwise the first preferred/keyword candidate that answers wins.
        A setting is left alone when nothing passes (never replaced by an untested model)."""
        current = current or {}
        listed = [m["id"] for cat in ("chat", "reasoning", "vision") for m in categorized.get(cat, [])]
        selected: Dict[str, str] = {}
        tested: Dict[str, bool] = {}
        for key in ("LLM_PRIMARY_MODEL", "LLM_SECONDARY_MODEL", "LLM_VISION_MODEL"):
            for m in self._candidates(key, listed, current.get(key, ""))[:max_tries]:
                if m not in tested:
                    tested[m] = self.live_chat_ok(m)
                    print(f"    live test {m}: {'ok' if tested[m] else 'failed'}", file=sys.stderr)
                if tested[m]:
                    selected[key] = m
                    break
            else:
                print(f"  \u26a0 {key}: no candidate passed a live test - left unchanged", file=sys.stderr)
        if "LLM_PRIMARY_MODEL" in selected:
            selected["LLM_MODEL"] = selected["LLM_PRIMARY_MODEL"]
        # Embeddings: keep the current model (changing it would break stored Astra vectors); pick one only
        # when none is set.
        if not current.get("EMBEDDING_MODEL"):
            embeds = [m["id"] for m in categorized.get("embedding", []) if not is_safety_model(m["id"])]
            for kw in ("nemotron-3-embed", "embedqa-e5-v5"):
                hit = next((m for m in embeds if kw in m.lower()), None)
                if hit:
                    selected["EMBEDDING_MODEL"] = hit
                    break
        # Only report real changes
        return {k: v for k, v in selected.items() if current.get(k) != v}

    def update_env_file(self, env_path: Path, updates: Dict[str, str], dry_run: bool = False) -> bool:
        """Update .env file with new model IDs"""
        if not env_path.exists():
            print(f"⚠ .env file not found at {env_path}", file=sys.stderr)
            return False

        bad = {k: v for k, v in updates.items() if k != "EMBEDDING_MODEL" and is_safety_model(v)}
        if bad:
            print(f"  \u26a0 refusing to write safety/guard models: {bad}", file=sys.stderr)
            updates = {k: v for k, v in updates.items() if k not in bad}
        if not updates:
            return True
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
                        # Update this line, noting the old value
                        old = line.split('=', 1)[1].strip()
                        if old != updates[key]:
                            updated_lines.append(f"# {key} was {old} - replaced by the model fetcher "
                                                 f"{time.strftime('%Y-%m-%d')} (live-tested)\n")
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

            # Write back atomically, keeping the file's permissions
            tmp = env_path.with_name(env_path.name + ".tmp")
            with open(tmp, 'w', encoding='utf-8') as f:
                f.writelines(updated_lines)
            os.chmod(tmp, env_path.stat().st_mode & 0o777)
            os.replace(tmp, env_path)

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

    # Current values (kept when they are working chat models)
    current: Dict[str, str] = {}
    try:
        for line in env_path.read_text(encoding='utf-8').splitlines():
            if '=' in line and not line.lstrip().startswith('#'):
                k, v = line.split('=', 1)
                if k.strip() in ("LLM_MODEL", "LLM_PRIMARY_MODEL", "LLM_SECONDARY_MODEL", "LLM_VISION_MODEL",
                                 "EMBEDDING_MODEL"):
                    current[k.strip()] = v.strip()
    except Exception:
        pass

    # Select working, non-safety models (live-tested)
    selected = updater.select_best_models(categorized, current)

    if not selected:
        print("  ✓ Model settings unchanged (current models are working, non-safety models)", file=sys.stderr)
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
