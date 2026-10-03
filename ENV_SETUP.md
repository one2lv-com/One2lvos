# Environment Variables Setup Guide

## ⚠️ CRITICAL SECURITY NOTICE

**NEVER commit `.env` files to git!** They contain sensitive API keys, tokens, and credentials.

## Files

### `.env.master`
Master environment configuration with all credentials. This file:
- ✅ Stored locally only
- ✅ Already in `.gitignore`
- ❌ NEVER committed to git
- 🔐 Contains all API keys and tokens

### Runtime `.env` Files
The deployment script automatically copies `.env.master` to the appropriate locations:
- `∆Gemini_Root∆/core/.env` - Backend environment
- Other service-specific `.env` files as needed

## Quick Start

The deployment script handles environment setup automatically:

```bash
./deploy-sovereign.sh
```

This will:
1. Check if `.env.master` exists
2. Copy credentials to runtime locations
3. Start services with proper configuration

## Manual Setup (if needed)

If you need to manually set up environment files:

```bash
# Copy master to backend
cp .env.master ∆Gemini_Root∆/core/.env

# Verify it's not tracked by git
git status | grep .env
# Should show nothing (ignored)
```

## Environment Variables Reference

### L1 Memory (Astra DB)
- `ASTRA_DB_API_ENDPOINT` - Astra DB API endpoint
- `ASTRA_DB_APPLICATION_TOKEN` - Authentication token
- `ASTRA_DB_KEYSPACE` - Database keyspace (one2lvOS)
- `COLLECTION_NAME` - Vector collection (aria_memory)
- `VECTOR_DIM` - Vector dimensions (1024)

### L2 Skills (NVIDIA AI)
- `NVIDIA_BASE_URL` - NVIDIA API base URL
- `EMBEDDING_MODEL` - Embedding model (nv-embedqa-e5-v5)
- `LLM_MODEL` - Language model (llama-3.3-nemotron-super-49b-v1)
- `NVIDIA_API_KEY` - Primary API key
- `NVIDIA_API_KEY_*` - Additional API keys for different services

### External Gateways
- `DISCORD_BOT_TOKEN` - Discord bot authentication
- `DISCORD_CHANNEL_ID` - Target Discord channel
- `TWITCH_OAUTH_TOKEN` - Twitch OAuth token
- `TWITCH_CHANNEL` - Twitch channel name

### Database (Supabase)
- `SUPABASE_URL` - Supabase project URL
- `SUPABASE_ANON_KEY` - Anonymous public key
- `SUPABASE_SERVICE_KEY` - Service role key (sensitive!)
- `DATABASE_URL` - PostgreSQL connection string

### Other Services
- `MATON_API_KEY` - Maton automation platform
- `GITHUB_TOKEN` - GitHub personal access token

### Server Configuration
- `PORT` - Server port (default: 8000)
- `NODE_ENV` - Environment (development/production)
- `PYTHON_API_URL` - Python backend URL

## Security Best Practices

### ✅ DO
- Keep `.env.master` in a secure location
- Use different credentials for dev/staging/production
- Rotate API keys regularly (monthly recommended)
- Use environment-specific values
- Back up `.env.master` securely (encrypted)
- Use secrets management in production (Vault, AWS Secrets Manager)

### ❌ DON'T
- Commit `.env` files to git
- Share credentials in chat/email
- Hardcode credentials in code
- Use production keys in development
- Store credentials in plain text
- Expose `.env` files via web server

## Credential Rotation

When rotating credentials:

1. **Get new credentials** from service providers
2. **Update `.env.master`** with new values
3. **Redeploy** the system:
   ```bash
   ./shutdown-sovereign.sh
   ./deploy-sovereign.sh
   ```
4. **Test** all integrations
5. **Revoke old credentials** after verification

## Production Deployment

For production, use a secrets management service:

### AWS Secrets Manager
```bash
aws secretsmanager create-secret \
  --name one2lvos/production \
  --secret-string file://.env.master
```

### HashiCorp Vault
```bash
vault kv put secret/one2lvos @.env.master
```

### Docker Secrets
```bash
docker secret create one2lvos-env .env.master
```

Then update deployment scripts to fetch from secrets manager instead of local files.

## Troubleshooting

### Missing Environment Variables
```bash
# Check if .env.master exists
ls -la .env.master

# Verify content (be careful not to expose in logs)
cat .env.master | grep -E "^[A-Z]" | wc -l
# Should show number of variables
```

### Services Can't Find Credentials
```bash
# Check if .env was copied to runtime location
ls -la ∆Gemini_Root∆/core/.env

# If missing, copy manually
cp .env.master ∆Gemini_Root∆/core/.env
```

### Invalid Credentials
1. Check if API keys are still valid
2. Test each service endpoint individually
3. Look for expiration dates
4. Verify correct key format

### Git Accidentally Tracking .env
```bash
# Remove from git but keep locally
git rm --cached .env.master
git rm --cached .env

# Verify it's in .gitignore
grep "\.env" .gitignore

# Commit the removal
git commit -m "Remove sensitive .env files from git"
```

## Environment-Specific Configurations

### Development
```bash
NODE_ENV=development
PORT=8000
# Use test/sandbox API keys
```

### Staging
```bash
NODE_ENV=staging
PORT=8000
# Use staging credentials
```

### Production
```bash
NODE_ENV=production
PORT=8000
# Use production credentials
# Enable all security features
```

## Validation Script

Test if all required variables are set:

```bash
#!/bin/bash
# validate-env.sh

required_vars=(
    "ASTRA_DB_API_ENDPOINT"
    "ASTRA_DB_APPLICATION_TOKEN"
    "NVIDIA_API_KEY"
    "NVIDIA_BASE_URL"
)

source .env.master

for var in "${required_vars[@]}"; do
    if [ -z "${!var}" ]; then
        echo "❌ Missing: $var"
    else
        echo "✅ Found: $var"
    fi
done
```

## Getting Credentials

### NVIDIA API Key
1. Go to https://build.nvidia.com
2. Sign in or create account
3. Navigate to API Keys
4. Generate new key
5. Copy to `.env.master`

### Astra DB
1. Sign up at https://astra.datastax.com
2. Create Serverless Vector database
3. Deploy to AWS us-east-2 or GCP us-east1
4. Copy endpoint and generate token
5. Add to `.env.master`

### Discord Bot
1. Go to https://discord.com/developers
2. Create new application
3. Add bot
4. Copy bot token
5. Add to `.env.master`

### Supabase
1. Sign up at https://supabase.com
2. Create new project
3. Go to Settings > API
4. Copy URL and keys
5. Add to `.env.master`

## Support

If you need help with environment setup:
1. Check this guide
2. Review deployment logs
3. Verify credentials are valid
4. Check GitHub issues
5. Contact support

## Version History

- v1.0.0 - Initial environment setup
  - Master .env template
  - Automatic deployment integration
  - Security guidelines

---

**Security is paramount. Protect your credentials!** 🔐
