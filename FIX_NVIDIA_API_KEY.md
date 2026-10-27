# Fix NVIDIA API Key Error (403 Forbidden)

## Problem
All NVIDIA API keys in `sovereign_integration/config/sovereign.env` are returning **403 Forbidden** errors, which means they are invalid, expired, or don't have access to the models.

## Solution

### Step 1: Get a New NVIDIA API Key

1. Go to: **https://build.nvidia.com/explore/discover**
2. Sign in or create an NVIDIA account
3. Navigate to any model page (e.g., Llama 3.2)
4. Click "Get API Key" or "Generate API Key"
5. Copy your new API key (format: `nvapi-XXXXXXXXXXXX`)

### Step 2: Update Configuration

Edit `sovereign_integration/config/sovereign.env` and replace the NVIDIA_API_KEY:

```bash
# Old (expired)
NVIDIA_API_KEY=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

# New (your fresh key)
NVIDIA_API_KEY=nvapi-YOUR_NEW_KEY_HERE
```

Or set it as an environment variable:

```bash
export NVIDIA_API_KEY="nvapi-YOUR_NEW_KEY_HERE"
```

### Step 3: Verify Configuration

Run the test to verify your new key works:

```bash
cd /home/vercel-sandbox/One2lvos-build
python3 test_nvidia_config.py
```

You should see:
```
✓ SUCCESS: API responded with 200 OK
```

### Step 4: Restart the Server

```bash
python3 lumenis-main-with-swarm.py
```

Or use the startup script:
```bash
./start-sovereign-reactor.sh
```

## Currently Configured Models

After getting a new key, these models will work:

- **Primary:** `meta/llama-3.2-90b-vision-instruct` (90B parameter vision model)
- **Secondary:** `meta/llama-3.2-11b-vision-instruct` (11B parameter vision model)

## Alternative: Use a Different Model

If you want to use a different model, check available models:

```bash
curl -H "Authorization: Bearer YOUR_API_KEY" https://integrate.api.nvidia.com/v1/models
```

Then update `LLM_PRIMARY_MODEL` and `LLM_SECONDARY_MODEL` in sovereign.env.

## Quick Test Command

```bash
# Test just the API key (not the full server)
python3 test_nvidia_config.py
```

## Why This Happened

NVIDIA API keys can expire or be revoked. The keys in your config were likely:
1. Generated for testing and have expired
2. Revoked or invalidated
3. Have rate limits exceeded
4. Are demo keys with limited access

**Solution:** Get a fresh API key from https://build.nvidia.com

---

**Next Steps:**
1. Get new API key from NVIDIA
2. Update `sovereign_integration/config/sovereign.env`
3. Run `python3 test_nvidia_config.py` to verify
4. Start server with `python3 lumenis-main-with-swarm.py`

The Sovereign Reactor will be operational once you have a valid API key. ⚡
