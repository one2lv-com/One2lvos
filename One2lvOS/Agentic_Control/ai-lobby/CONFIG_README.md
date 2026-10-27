# AI Lobby Configuration

## ⚠️ API Keys Required

The `config.defaults.json` file contains **placeholder** API keys. You must replace them with your own.

### Get API Keys

1. **NVIDIA API Keys**
   - Visit: https://build.nvidia.com
   - Sign up/login
   - Get API key(s)
   - Replace `NVIDIA_API_KEY_1`, `NVIDIA_API_KEY_2`, etc.

2. **Google Gemini API Key** (optional)
   - Visit: https://makersuite.google.com/app/apikey
   - Get API key
   - Replace `GOOGLE_GEMINI_API_KEY`

### Setup

1. Copy the config file:
   ```bash
   cp config.defaults.json data/config.json
   ```

2. Edit `data/config.json`:
   ```bash
   nano data/config.json
   ```

3. Replace placeholders:
   - `NVIDIA_API_KEY_1` → Your real NVIDIA key
   - `NVIDIA_API_KEY_2` → Another NVIDIA key (or same)
   - `NVIDIA_API_KEY_3` → Another NVIDIA key (or same)
   - `NVIDIA_API_KEY_4` → Another NVIDIA key (or same)
   - `GOOGLE_GEMINI_API_KEY` → Your Gemini key
   - `CHANGE_THIS_PASSWORD` → Your admin password

4. **IMPORTANT:** `data/config.json` is in `.gitignore` and will NOT be committed to git.

### Security

- **Never commit real API keys to git**
- `config.defaults.json` should only have placeholders
- `data/config.json` contains your real keys (gitignored)
- Use environment variables for production

### Environment Variables (Alternative)

You can also use environment variables:
```bash
export NVIDIA_API_KEY="your_key_here"
export GOOGLE_GEMINI_API_KEY="your_key_here"
```

Then the lobby will use these instead of the config file.
