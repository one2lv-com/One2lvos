# NVIDIA Model Auto-Update

**Automatic NVIDIA model ID updates integrated into One2lvOS startup**

## Overview

One2lvOS now automatically fetches and updates NVIDIA model IDs during system boot to ensure you're always using the latest available models from the NVIDIA API catalog.

## How It Works

1. **On Startup**: `startos.sh` calls `update_nvidia_models.py` during Step 2 (Environment Configuration)
2. **Fetch Models**: Script queries `https://integrate.api.nvidia.com/v1/models` for available models
3. **Smart Selection**: Selects best models from each category (chat, vision, embedding, reasoning)
4. **Update .env**: Automatically updates model IDs in `.env` file
5. **Reload**: Re-sources `.env` with fresh model configurations

## Updated Model Variables

The following `.env` variables are automatically updated:

| Variable | Purpose | Example Value |
|----------|---------|---------------|
| `LLM_MODEL` | Primary chat/completion model | `meta/llama-3.1-8b-instruct` |
| `LLM_PRIMARY_MODEL` | Same as LLM_MODEL | `meta/llama-3.1-8b-instruct` |
| `LLM_SECONDARY_MODEL` | Backup/reasoning model | `nvidia/nemotron-3-nano-omni-30b-a3b-reasoning` |
| `LLM_VISION_MODEL` | Image analysis model | `microsoft/phi-3-vision-128k-instruct` |
| `EMBEDDING_MODEL` | Text embedding model | `nvidia/nv-embedqa-e5-v5` |

## Selection Priority

The script prioritizes models that are:

1. **Widely Accessible**: Free tier and basic API access compatible
2. **Proven Reliable**: Well-tested in production environments
3. **Appropriately Sized**: Not too large (avoids 70B+ requiring special access)

### Model Selection Order

**Chat Models:**
1. Meta Llama 3.1 family (8B-70B)
2. Meta Llama 3 family
3. Mistral models
4. Google Gemma models
5. Microsoft Phi models
6. NVIDIA Nemotron models

**Vision Models:**
1. Microsoft Phi-3 Vision
2. Meta Llama Vision
3. NVIDIA Vision models

**Embedding Models:**
1. NVIDIA NV-EmbedQA-E5-V5
2. NVIDIA Nemotron Embed
3. Other embedding models

## Configuration

### Skip Auto-Update

To skip the model update on startup:

```bash
export ONE2LVOS_SKIP_MODEL_UPDATE=1
./startos.sh
```

### Dry-Run Mode

Preview what would be updated without making changes:

```bash
export ONE2LVOS_MODEL_UPDATE_DRY_RUN=1
python3 update_nvidia_models.py
```

### Manual Update

Run the updater manually anytime:

```bash
python3 update_nvidia_models.py
```

## Fallback Behavior

If the NVIDIA API is unavailable, the script falls back to known good models:

- **Chat**: `meta/llama-3.1-8b-instruct`, `mistralai/mistral-7b-instruct-v0.3`
- **Vision**: `microsoft/phi-3-vision-128k-instruct`
- **Embedding**: `nvidia/nv-embedqa-e5-v5`, `baai/bge-large-en-v1.5`

## Requirements

- **Python 3**: Required
- **requests module**: `pip install requests`
- **NVIDIA API Key**: Optional but recommended
  - Get from: https://build.nvidia.com/explore/discover
  - Without key: uses fallback models only

## Logs

The updater outputs status to stderr during `startos.sh`:

```
[2/10] ENVIRONMENT CONFIGURATION
────────────────────────────────────────────────────────────────
  ✓ Loaded .env configuration
  🔍 Fetching latest NVIDIA models...
  ✓ Found 84 available models
  ✓ Updated 5 model configurations
    • LLM_MODEL=meta/llama-3.1-8b-instruct
    • LLM_PRIMARY_MODEL=meta/llama-3.1-8b-instruct
    • LLM_VISION_MODEL=microsoft/phi-3-vision-128k-instruct
    • EMBEDDING_MODEL=nvidia/nv-embedqa-e5-v5
    • LLM_SECONDARY_MODEL=nvidia/nemotron-3-nano-omni-30b-a3b-reasoning
  ✓ NVIDIA API Key configured
```

## Benefits

✅ **Always Current**: No more 410 Gone (EOL) errors from deprecated models
✅ **Zero Maintenance**: Runs automatically on every boot
✅ **Smart Defaults**: Prioritizes accessible, reliable models
✅ **Graceful Fallback**: Works even if API is unavailable
✅ **Safe Updates**: Only updates model IDs, never removes other config

## Troubleshooting

### Issue: Models still return 403 Forbidden

**Cause**: API key doesn't have access to selected models
**Solution**:
1. Get a fresh API key from https://build.nvidia.com
2. Some models require upgraded access - the script prioritizes free-tier models

### Issue: Models return 410 Gone

**Cause**: Selected model reached end-of-life after the update
**Solution**: Run `python3 update_nvidia_models.py` manually to refresh

### Issue: Script fails with ImportError

**Cause**: `requests` module not installed
**Solution**: `pip install requests`

### Issue: Want to use specific models

**Cause**: Auto-update overrides your preferred models
**Solution**:
1. Skip auto-update: `export ONE2LVOS_SKIP_MODEL_UPDATE=1`
2. Or edit models in `.env` after boot completes

## Integration with One2lvOS

The auto-updater is integrated into:

- ✅ `startos.sh` - Runs during environment configuration
- ✅ `LLMTool` - Uses `LLM_MODEL` for chat completions
- ✅ `SwarmTool` - Can use any configured model
- ✅ `VisionTool` - Uses `LLM_VISION_MODEL` for image analysis
- ✅ `lumenis-main.py` - Reactor uses `LLM_PRIMARY_MODEL`

## API Rate Limits

The NVIDIA model list API has rate limits:

- **Free tier**: 100 requests/minute
- **Impact**: Model fetch happens once per boot only
- **Cache**: Models are cached in `.env` between boots

## Security Notes

- ✅ Script only updates model IDs, never API keys
- ✅ Reads `.env` but doesn't modify other configuration
- ✅ Outputs to stderr, doesn't log sensitive data
- ✅ Gracefully handles API failures

## Future Enhancements

Potential future improvements:

- [ ] Model performance benchmarking
- [ ] User-configurable model preferences
- [ ] Model cost optimization
- [ ] Automatic fallback testing
- [ ] Multi-region model selection

---

**Status**: ✅ Implemented and Active

**Location**: `/home/vercel-sandbox/One2lvos/update_nvidia_models.py`

**Integration**: `startos.sh` lines 204-212

**Last Updated**: 2026-11-07
