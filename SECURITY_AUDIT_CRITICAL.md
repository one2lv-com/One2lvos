# 🚨 CRITICAL SECURITY AUDIT - IMMEDIATE ACTION REQUIRED

**Date:** 2026-10-27
**Status:** REPOSITORY MADE PRIVATE (was public from ~1:00-1:45 UTC)
**Risk Level:** 🔴 CRITICAL

## ⚠️ What Happened

The repository was made PUBLIC with exposed credentials for approximately 45 minutes.
During this time, GitHub scanning bots and anyone who cloned the repo gained access to:
- 31+ different secrets and API keys
- SSH private keys
- Database credentials
- Service passwords

**Making the repo private again does NOT fix this** - anyone who cloned it keeps a copy.

## 🔥 EXPOSED CREDENTIALS (MUST REVOKE IMMEDIATELY)

### 1. NVIDIA API Keys (Multiple Exposed)

**Locations with REAL keys:**
```
./LUMENIS_INTEGRATION_COMPLETE.md
./NVIDIA_MIGRATION_COMPLETE.md
./One2lvOS/Agentic_Control/ai-lobby/config.defaults.json (4 keys)
./One2lvOS/Agentic_Control/ai-lobby/data/config.json (4 keys)
./One2lvOS/modules/ai-chat/ai-chat.js
```

**Real API keys found:**
- `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`
- `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`
- `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`
- `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`
- `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`
- `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`

**Action Required:**
1. Go to https://build.nvidia.com
2. Revoke ALL these keys immediately
3. Generate new keys
4. Store in environment variables ONLY

### 2. ASTRA DB Credentials

**Exposed in:**
- `LUMENIS_INTEGRATION_COMPLETE.md`
- Multiple setup guides
- Configuration files

**Action Required:**
1. Go to https://astra.datastax.com
2. Rotate application tokens
3. Update endpoint if possible
4. Store in environment variables ONLY

### 3. SSH Private Key

**File:** `.ssh_host_key`

This is a PRIVATE SSH key committed to the repository. Anyone with this can:
- SSH into servers using this key
- Impersonate the server
- Decrypt SSH traffic

**Action Required:**
1. Find all servers using this key
2. Generate NEW SSH keys on each server
3. Delete `.ssh_host_key` from repo
4. Add `*.ssh*` to `.gitignore`

### 4. Discord Bot Token

**Exposed in multiple locations**

**Action Required:**
1. Go to Discord Developer Portal
2. Regenerate bot token
3. Store in environment variables ONLY

### 5. Twitch OAuth Token

**Exposed in config files**

**Action Required:**
1. Go to Twitch Developer Portal
2. Revoke OAuth token
3. Generate new token
4. Store in environment variables ONLY

### 6. Supabase Keys

**Service keys and anon keys exposed**

**Action Required:**
1. Go to Supabase dashboard
2. Rotate service role key
3. Consider rotating anon key
4. Store in environment variables ONLY

### 7. GitHub Personal Access Token

**Token used for pushing exposed in git history**

**Action Required:**
1. Go to https://github.com/settings/tokens
2. Revoke the token
3. Generate new token with minimal permissions
4. NEVER commit tokens to git

### 8. Maton API Keys

**Multiple keys exposed**

**Action Required:**
1. Go to Maton dashboard
2. Rotate all API keys
3. Store in environment variables ONLY

### 9. Moltbook Credentials

**File:** `minimax/moltbook-registry/credentials.json`

**Action Required:**
1. Check what's in this file
2. Rotate credentials
3. Delete from repo
4. Add to `.gitignore`

### 10. Lobby Password

**Exposed in configuration files**

**Action Required:**
1. Change lobby password immediately
2. Remove from all config files

## 📂 Files That MUST Be Removed from Git History

These files contain real secrets:
```
.ssh_host_key
minimax/android/credentials.json
minimax/moltbook-registry/credentials.json
One2lvOS/Agentic_Control/ai-lobby/config.defaults.json
One2lvOS/Agentic_Control/ai-lobby/data/config.json
One2lvOS/modules/ai-chat/ai-chat.js
```

## 🔧 REMAINING HARDCODED PATHS (15 files)

These still have `/home/vercel-sandbox` hardcoded:

1. `deploy_semantic_to_onworks.py`
2. `ftp_server.py`
3. `lumenis_dream_state.py`
4. `lumenis_security_heartbeat.py`
5. `maton_gmail_alerter.py`
6. `maton_security_monitor.py`
7. `start_dream_session.py`
8. `talk-to-lumenis.py`
9. `webdav_server.py`
10. `start-security-monitor.sh`
11. `test-system.sh`

**These need VFS integration or path auto-detection.**

## 🛠️ IMMEDIATE ACTION PLAN

### Phase 1: Revoke Everything (DO NOW)
- [ ] Revoke all 6+ NVIDIA API keys
- [ ] Rotate ASTRA DB tokens
- [ ] Regenerate SSH keys on all servers
- [ ] Revoke Discord bot token
- [ ] Revoke Twitch OAuth token
- [ ] Rotate Supabase keys
- [ ] Revoke GitHub token
- [ ] Rotate Maton API keys
- [ ] Change lobby password

### Phase 2: Clean Repository
- [ ] Delete credential files from current version
- [ ] Remove hardcoded keys from all files
- [ ] Update `.gitignore` to prevent future commits:
  ```
  *.ssh*
  *credentials*
  *key.json
  .env*
  config.json
  ```

### Phase 3: Fix Remaining Issues
- [ ] Fix 15 files with hardcoded `/home/vercel-sandbox` paths
- [ ] Use VFS for all file operations
- [ ] Store ALL secrets in environment variables
- [ ] Create template files without real values

### Phase 4: Create Clean Repository (Optional)
If you want to make it public again:

1. Create a NEW repository with clean history
2. Copy files WITHOUT secrets
3. Replace all hardcoded paths with VFS
4. Add comprehensive `.gitignore`
5. Add security scanning (GitHub secret scanning)
6. Document in README: "NEVER commit secrets"

## 📋 Files to Update

### Remove Real Keys From:
```
LUMENIS_INTEGRATION_COMPLETE.md
NVIDIA_MIGRATION_COMPLETE.md
One2lvOS/Agentic_Control/ai-lobby/config.defaults.json
One2lvOS/Agentic_Control/ai-lobby/data/config.json
One2lvOS/modules/ai-chat/ai-chat.js
```

### Fix Hardcoded Paths In:
```
deploy_semantic_to_onworks.py
ftp_server.py
lumenis_dream_state.py
lumenis_security_heartbeat.py
maton_gmail_alerter.py
maton_security_monitor.py
start_dream_session.py
talk-to-lumenis.py
webdav_server.py
start-security-monitor.sh
test-system.sh
```

## 🔒 Best Practices Going Forward

### 1. Environment Variables ONLY
```python
import os
NVIDIA_API_KEY = os.environ.get("NVIDIA_API_KEY")
# NEVER: NVIDIA_API_KEY = "nvapi-..."
```

### 2. Template Files
Create `.template` or `.example` files:
```
config.json.template  # No real values
config.json           # In .gitignore, has real values
```

### 3. Pre-commit Hooks
Use `git-secrets` or similar to scan for keys before commit.

### 4. Secret Scanning
Enable GitHub secret scanning (even for private repos).

### 5. Principle of Least Privilege
- Use read-only tokens where possible
- Separate production and development keys
- Rotate keys regularly

## ⚡ What to Do Right Now

```bash
# 1. Make sure repo is private (DONE)
# Already private

# 2. Revoke all keys (DO THIS FIRST)
# Go to each service dashboard and revoke

# 3. Delete secret files from current version
git rm .ssh_host_key
git rm minimax/android/credentials.json
git rm minimax/moltbook-registry/credentials.json

# 4. Update .gitignore
cat >> .gitignore << EOF
*.ssh*
*credentials*
*key.json
.env*
config.json
EOF

# 5. Commit removals
git commit -m "security: remove exposed credentials"

# 6. Generate new keys and store in environment
# DO NOT commit new keys!
```

## 📞 If You Need Help

- GitHub Security: https://github.com/security
- Report compromised keys to each service
- Consider security audit services

## 🔍 How to Check if Keys Were Used

- **NVIDIA:** Check API usage dashboard
- **ASTRA DB:** Check query logs
- **GitHub:** Check access logs
- **Discord:** Check bot activity
- **Twitch:** Check OAuth usage

## ⏰ Timeline

- **~1:00 UTC:** Repo made public
- **~1:45 UTC:** Repo made private
- **45 minutes:** Window of exposure
- **Action Window:** Next 24 hours critical

---

**Status:** Repository is PRIVATE but keys are COMPROMISED.
**Next Action:** REVOKE ALL KEYS IMMEDIATELY.

This is a critical security incident. Act now to minimize damage.
