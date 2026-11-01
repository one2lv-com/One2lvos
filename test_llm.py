import requests
import os

models = [
    "nvidia/nemotron-3.5-lightning-30b-a3b",
    "nvidia/nemotron-3.5-bolt-e4b",
    "mistralai/mistral-large-2-instruct",
    "meta/llama-3.2-11b-vision-instruct",
    "google/gemma-3-12b-it",
]

api_key = os.environ["NVIDIA_API_KEY"]

for model in models:
    try:
        print(f"Testing {model}...")
        resp = requests.post(
            "https://integrate.api.nvidia.com/v1/chat/completions",
            headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
            json={"model": model, "messages": [{"role": "user", "content": "say OK"}], "max_tokens": 5},
            timeout=15
        )
        if resp.status_code == 200:
            content = resp.json()["choices"][0]["message"]["content"]
            print(f"  ✓ {model}: {content}")
            break
        else:
            print(f"  ✗ {model}: {resp.json().get('status')} - {resp.json().get('detail', resp.json().get('message'))}")
    except Exception as e:
        print(f"  ✗ {model}: {e}")
