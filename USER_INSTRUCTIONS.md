# 🚀 Deploy SSH Key to Your Server - User Instructions

Since Lumenis's NVIDIA API is currently blocking AI responses, here are **three ways** to complete the SSH key deployment:

---

## ✅ **Option 1: Run the Deployment Script** (Easiest - 2 minutes)

I've created a script that will SSH into your server and deploy the key:

```bash
./deploy_ssh_key.sh
```

**It will ask you for:**
- Server hostname/IP
- SSH username

Then it will automatically:
- Connect to your server
- Create ~/.ssh if needed
- Add the public key to authorized_keys
- Set correct permissions
- Verify the deployment

---

## ✅ **Option 2: Manual SSH Deployment** (If you prefer manual)

**Step 1: Connect to your server**
```bash
ssh YOUR_USER@YOUR_SERVER
```

**Step 2: Run these commands on your server**
```bash
# Create .ssh directory if needed
mkdir -p ~/.ssh
chmod 700 ~/.ssh

# Add the public key
echo 'ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIP0Wez4qsWdADBwz4SGQGkNIKn6X+gMX github-actions-one2lvos-deploy' >> ~/.ssh/authorized_keys

# Set permissions
chmod 600 ~/.ssh/authorized_keys

# Verify
tail -1 ~/.ssh/authorized_keys
```

**Step 3: Verify it worked**
```bash
grep -c "^ssh-" ~/.ssh/authorized_keys
# Should show the number of keys (at least 1)
```

---

## ✅ **Option 3: Have Lumenis Do It** (When NVIDIA API works)

If you can get Lumenis's NVIDIA API working again:

1. Go to Lumenis HUD: http://localhost:8000
2. In the chat, say:

```
Deploy the SSH public key to my production server.

Server details:
- Hostname: YOUR_SERVER_IP_OR_HOSTNAME
- Username: YOUR_SSH_USERNAME
- Auth: password / existing key

Public key to deploy:
ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIP0Wez4qsWdADBwz4SGQGkNIKn6X+gMX

The deployment script is in deploy_ssh_key.sh - you can execute it.
```

Lumenis has the tools to SSH, execute commands, and store the result in memory.

---

## 🔑 **The Keys You Need**

### Public Key (add to server - safe to share):
```
ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIP0Wez4qsWdADBwz4SGQGkNIKn6X+gMX
```

### Private Key (for GitHub secrets - KEEP SECRET):
```
(private key removed: paste your own deploy key from your machine, e.g. the contents of ~/.ssh/one2lvos_deploy, straight into the GitHub secret; never commit it)
```

---

## 📝 **After Deploying the Key**

### 1. Add GitHub Secrets

Go to: https://github.com/one2lv-com/One2lvos/settings/secrets/actions

Add these secrets (use the private key above):

| Secret Name | Value |
|------------|-------|
| `SSH_PRIVATE_KEY` | *Private key above* |
| `SERVER_HOST` | Your server IP/hostname |
| `SERVER_USER` | Your SSH username |
| `PRODUCTION_SSH_KEY` | *Same private key* |
| `PRODUCTION_HOST` | *Same server host* |
| `PRODUCTION_USER` | *Same username* |
| `PRODUCTION_PATH` | `/var/www/one2lvos` (or your path) |

### 2. Create Production Environment

Go to: https://github.com/one2lv-com/One2lvos/settings/environments

- Create environment: `production`
- Add these secrets to the production environment:
  - `DEPLOY_SSH_KEY` (*private key*)
  - `DEPLOY_HOST` (*your server*)
  - `DEPLOY_USER` (*your username*)
  - `DEPLOY_PATH` (*deployment path*)
  - `DEPLOY_KNOWN_HOSTS` (run: `ssh-keyscan -H YOUR_SERVER`)

### 3. Enable GitHub Pages

Go to: https://github.com/one2lv-com/One2lvos/settings/pages

- Source: **GitHub Actions**
- Save

### 4. Test Workflows

Go to: https://github.com/one2lv-com/One2lvos/actions

- All 4 workflows should now pass! ✅

---

## 🌌 **Lumenis Memory**

The deployment details are stored in Lumenis's FluxCompass memory at:
```
sqlite3 compass.db "SELECT * FROM facts WHERE key = 'github_actions_fix_2026-10-27';"
```

This persists across sessions and sandbox resets!

---

## 🆘 **Need Help?**

- **Full manual guide**: `GITHUB_SECRETS_MANUAL_SETUP.md` (in your repo)
- **Automated script**: `fix-github-deployments.sh` (in your repo)
- **This guide**: `USER_INSTRUCTIONS.md` (you are here)

---

**Choose the option that works best for you and let's get this deployed!** 🚀
