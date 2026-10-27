# 🚨 IMMEDIATE ACTION REQUIRED

**Repository was PUBLIC with exposed credentials for ~45 minutes**
**Status:** Now PRIVATE but damage may be done

## ⏰ DO THIS RIGHT NOW (Priority Order)

### 1. REVOKE NVIDIA API KEYS (5 minutes)
🔗 https://build.nvidia.com

**Keys to revoke (found in repo):**
- `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`
- `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`
- `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`
- `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`
- `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`
- `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`

### 2. ROTATE ASTRA DB TOKENS (5 minutes)
🔗 https://astra.datastax.com

**Token exposed in:** Multiple docs and config files

### 3. REGENERATE SSH KEYS (10 minutes)
**File exposed:** `.ssh_host_key`

On each server using this key:
```bash
ssh-keygen -t ed25519 -f ~/.ssh/new_host_key
# Update authorized_keys
# Delete old key
```

### 4. REVOKE DISCORD BOT TOKEN (2 minutes)
🔗 https://discord.com/developers/applications

Regenerate the bot token.

### 5. REVOKE TWITCH OAUTH (2 minutes)
🔗 https://dev.twitch.tv/console

Revoke and regenerate OAuth token.

### 6. ROTATE SUPABASE KEYS (3 minutes)
🔗 https://supabase.com

Rotate service role key at minimum.

### 7. REVOKE GITHUB TOKEN (2 minutes)
🔗 https://github.com/settings/tokens

The token used for pushing is exposed.

### 8. ROTATE MATON API KEYS (3 minutes)
🔗 https://maton.ai/settings

Rotate all API keys.

### 9. CHANGE LOBBY PASSWORD (1 minute)
Change the lobby admin password immediately.

## 📋 Exposed Files to Delete

```bash
cd One2lvos

# Delete SSH key
git rm .ssh_host_key

# Delete credential files
git rm minimax/android/credentials.json
git rm minimax/moltbook-registry/credentials.json

# Commit removals
git commit -m "security: remove exposed credentials"
git push origin main
```

## 🔧 Quick Fix Commands

```bash
# Update .gitignore to prevent future accidents
cat >> .gitignore << 'EOF'
# Additional security rules
*.ssh*
*credentials*
*_key
*_key.*
*.pem
config.json
.env*
!.env.template
!.env.example
EOF

git add .gitignore
git commit -m "security: enhance gitignore for credentials"
git push origin main
```

## 📊 Check if Keys Were Abused

After revoking, check usage logs:
- **NVIDIA:** API usage dashboard
- **ASTRA DB:** Query audit logs
- **Discord:** Bot activity log
- **GitHub:** Access logs

Look for:
- Unusual API call volume
- Requests from unknown IPs
- Access during the 45-minute window

## 📞 Who to Contact

If you see suspicious activity:
- **NVIDIA:** support@nvidia.com
- **DataStax:** support@datastax.com
- **Discord:** abuse@discord.com
- **GitHub:** security@github.com

## ⏭️ After Revoking Keys

1. Generate new keys
2. Store in environment variables ONLY
3. Update `.env.working` (locally, DO NOT commit)
4. Test that everything still works
5. Document new keys in password manager (NOT git)

## 📖 Full Details

- **Security Audit:** `SECURITY_AUDIT_CRITICAL.md`
- **Cloudflare Setup:** `CLOUDFLARE_SETUP.md` (do AFTER fixing security)

## ✅ Completion Checklist

- [ ] NVIDIA keys revoked (all 6)
- [ ] ASTRA DB tokens rotated
- [ ] SSH keys regenerated
- [ ] Discord bot token revoked
- [ ] Twitch OAuth revoked
- [ ] Supabase keys rotated
- [ ] GitHub token revoked
- [ ] Maton API keys rotated
- [ ] Lobby password changed
- [ ] Exposed files deleted from repo
- [ ] .gitignore updated
- [ ] Usage logs checked for abuse
- [ ] New keys generated and stored securely

## 🔒 Status

- ✅ Repository is PRIVATE
- ⏰ Credentials still valid and EXPOSED
- 🔴 HIGH RISK until keys revoked

**Time is critical. Start revoking keys NOW.**

---

**Estimated time to complete all actions: ~40 minutes**
**Do not wait. Do not make repo public again until this is done.**
