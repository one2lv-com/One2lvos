# 🔴 GitHub Actions Deployment Failures - Root Cause Analysis

**Date**: 2026-10-27
**Status**: 4 workflows failing, 1 workflow succeeding
**Repository**: one2lv-com/One2lvos
**Branch**: main

---

## 📊 Current Status

| Workflow | Status | Root Cause |
|----------|--------|------------|
| **One2lvOS CI/CD** | ✅ **SUCCESS** | Working correctly |
| **Deploy to Production** | ❌ **FAILING** | Missing GitHub Secrets |
| **One2lvOS Persistent Host Deploy** | ❌ **FAILING** | Missing GitHub Secrets |
| **Deploy One2lvOS to Production** | ❌ **FAILING** | Missing directory + Missing secrets |
| **One2lvOS Build and Deploy** (Pages) | ❌ **FAILING** | GitHub Pages not enabled |

---

## 🔍 Detailed Analysis

### 1. ❌ Deploy to Production (deploy.yml)

**Error Message:**
```
usage: ssh-keyscan [-46cDHv] [-f file] [-O option] [-p port] [-T timeout]
##[error]Process completed with exit code 1.
```

**Root Cause:**
Missing GitHub Secrets. The workflow expects these secrets but they are not configured:

```yaml
SSH_PRIVATE_KEY: <empty>
SERVER_HOST: <empty>
SERVER_USER: <empty>
```

**Failing Step:**
```bash
ssh-keyscan -H $SERVER_HOST >> ~/.ssh/known_hosts
# Fails because $SERVER_HOST is empty
```

**Fix Required:**
Add the following secrets to GitHub repository settings:
- `SSH_PRIVATE_KEY` - Private SSH key for server access
- `SERVER_HOST` - Production server hostname/IP
- `SERVER_USER` - SSH username for server

---

### 2. ❌ One2lvOS Persistent Host Deploy (deploy-host.yml)

**Error Message:**
```
Missing production secret DEPLOY_SSH_KEY
##[error]Process completed with exit code 1.
```

**Root Cause:**
Missing GitHub Secrets in the `production` environment.

```yaml
DEPLOY_SSH_KEY: <empty>
DEPLOY_KNOWN_HOSTS: <empty>
DEPLOY_HOST: <empty>
DEPLOY_USER: <empty>
DEPLOY_PATH: <empty>
```

**Failing Step:**
```bash
test -n "$DEPLOY_SSH_KEY" || { echo "Missing production secret DEPLOY_SSH_KEY"; exit 1; }
# Fails because DEPLOY_SSH_KEY is not set
```

**Fix Required:**
Add the following secrets to the `production` environment in GitHub:
- `DEPLOY_SSH_KEY` - ED25519 private SSH key
- `DEPLOY_KNOWN_HOSTS` - SSH known_hosts entries
- `DEPLOY_HOST` - Deployment server hostname/IP
- `DEPLOY_USER` - SSH username
- `DEPLOY_PATH` - Deployment directory path on server

---

### 3. ❌ Deploy One2lvOS to Production (deploy-production.yml)

**Error Messages:**
```
ERROR: Could not open requirements file: [Errno 2] No such file or directory: 'requirements.txt'
##[error]Process completed with exit code 1.
```

```
##[error]The ssh-private-key argument is empty. Maybe the secret has not been configured.
```

**Root Causes:**
Two separate issues:

**Issue A - Missing Directory Structure:**
```bash
cd One2lvOS/Agentic_Control/ai-lobby/sovereign-council-bridge
pip install -r requirements.txt
```
The directory `One2lvOS/Agentic_Control/ai-lobby/sovereign-council-bridge` does not exist in the repository.

**Issue B - Missing GitHub Secrets:**
```yaml
PRODUCTION_SSH_KEY: <empty>
PRODUCTION_HOST: <empty>
PRODUCTION_USER: <empty>
PRODUCTION_PATH: <empty>
```

**Fix Required:**

**Part 1 - Fix Directory Structure:**
Either:
- Create the missing directory and add `requirements.txt`
- OR update the workflow to use the correct path
- OR remove this validation step if not needed

**Part 2 - Add GitHub Secrets:**
- `PRODUCTION_SSH_KEY` - Private SSH key for production server
- `PRODUCTION_HOST` - Production server hostname/IP
- `PRODUCTION_USER` - SSH username
- `PRODUCTION_PATH` - Deployment path on server

---

### 4. ❌ One2lvOS Build and Deploy (deploy-pages.yml)

**Error Message:**
```
##[error]Get Pages site failed. Please verify that the repository has Pages enabled
and configured to build using GitHub Actions, or consider exploring the `enablement`
parameter for this action.
Error: Not Found - https://docs.github.com/rest/pages/pages#get-a-apiname-pages-site
```

**Root Cause:**
GitHub Pages is not enabled for the repository.

**Fix Required:**
Enable GitHub Pages in the repository settings:

1. Go to **Settings** → **Pages**
2. Under **Source**, select **GitHub Actions**
3. Save the configuration

Alternatively, modify the workflow to set `enablement: true`:
```yaml
- name: Configure GitHub Pages
  uses: actions/configure-pages@v5
  with:
    enablement: true  # Add this line
```

---

## ✅ Working Workflow

### One2lvOS CI/CD

**Status**: ✅ **SUCCESS**
**Why it works**: This workflow doesn't require any external secrets or GitHub Pages configuration. It only runs basic validation steps.

---

## 🔧 Complete Fix Checklist

### Priority 1: Add Missing GitHub Secrets

Go to **Settings** → **Secrets and variables** → **Actions** → **New repository secret**

#### For "Deploy to Production":
- [ ] `SSH_PRIVATE_KEY`
- [ ] `SERVER_HOST`
- [ ] `SERVER_USER`

#### For "Deploy One2lvOS to Production":
- [ ] `PRODUCTION_SSH_KEY`
- [ ] `PRODUCTION_HOST`
- [ ] `PRODUCTION_USER`
- [ ] `PRODUCTION_PATH`

#### For "One2lvOS Persistent Host Deploy" (in production environment):
Go to **Settings** → **Environments** → **production** → **Add secret**
- [ ] `DEPLOY_SSH_KEY`
- [ ] `DEPLOY_KNOWN_HOSTS`
- [ ] `DEPLOY_HOST`
- [ ] `DEPLOY_USER`
- [ ] `DEPLOY_PATH`

### Priority 2: Fix Directory Structure Issue

Choose one option:

**Option A**: Create the missing directory structure
```bash
mkdir -p One2lvOS/Agentic_Control/ai-lobby/sovereign-council-bridge
cd One2lvOS/Agentic_Control/ai-lobby/sovereign-council-bridge
touch requirements.txt
# Add necessary Python packages to requirements.txt
```

**Option B**: Update the workflow path to match actual structure
```yaml
# Change from:
cd One2lvOS/Agentic_Control/ai-lobby/sovereign-council-bridge

# To actual path (check your repo structure):
cd <actual-path-to-requirements.txt>
```

**Option C**: Remove the validation step if not needed
```yaml
# Comment out or remove these lines from deploy-production.yml:
# - name: Install Python dependencies
#   run: |
#     cd One2lvOS/Agentic_Control/ai-lobby/sovereign-council-bridge
#     pip install -r requirements.txt
```

### Priority 3: Enable GitHub Pages

Go to **Settings** → **Pages**:
- [ ] Under **Source**, select **GitHub Actions**
- [ ] Click **Save**

OR modify the workflow to auto-enable:
```yaml
- name: Configure GitHub Pages
  uses: actions/configure-pages@v5
  with:
    enablement: true
```

---

## 📋 Required Values for Secrets

When adding secrets, you'll need these values:

### SSH Keys
Generate a new SSH key pair if you don't have one:
```bash
ssh-keygen -t ed25519 -C "github-actions-deploy"
```
- Use the **private key** for `SSH_PRIVATE_KEY`, `DEPLOY_SSH_KEY`, `PRODUCTION_SSH_KEY`
- Add the **public key** to your server's `~/.ssh/authorized_keys`

### Known Hosts
Get the server's SSH fingerprint:
```bash
ssh-keyscan -H your-server-hostname-or-ip
```

### Server Details
- **HOST**: Your server's hostname or IP address (e.g., `192.168.1.100` or `server.example.com`)
- **USER**: SSH username (e.g., `deploy`, `ubuntu`, `root`)
- **PATH**: Deployment directory on server (e.g., `/var/www/one2lvos`, `/home/deploy/one2lvos`)

---

## 🎯 Quick Fix Priority

1. **HIGHEST**: Add all missing secrets (fixes 3 of 4 failing workflows)
2. **HIGH**: Fix directory structure issue in deploy-production.yml
3. **MEDIUM**: Enable GitHub Pages (only if you want to use Pages deployment)

---

## 🔄 After Fixing

Once secrets are added:
1. The workflows will automatically run on the next push to `main`
2. OR manually trigger them: **Actions** → Select workflow → **Run workflow**
3. Monitor the workflow runs to verify they succeed

---

## 💡 Alternative: Disable Unused Workflows

If you don't need all these deployment workflows, you can disable them:

1. Go to **Actions** tab
2. Click on the workflow name
3. Click **•••** (three dots) → **Disable workflow**

This will stop the failure notifications while you decide which deployments you actually need.

---

## 📝 Notes

- All 4 failing workflows are deployment-related
- The CI/CD workflow (tests/validation) is working fine
- No code issues - only configuration/secrets issues
- Once secrets are added, deployments should work

---

## 🔗 Useful Links

- [GitHub Actions Secrets Documentation](https://docs.github.com/en/actions/security-guides/encrypted-secrets)
- [GitHub Pages Configuration](https://docs.github.com/en/pages/getting-started-with-github-pages/configuring-a-publishing-source-for-your-github-pages-site)
- [SSH Key Generation Guide](https://docs.github.com/en/authentication/connecting-to-github-with-ssh/generating-a-new-ssh-key-and-adding-it-to-the-ssh-agent)

---

**Generated**: 2026-10-27
**Repository**: one2lv-com/One2lvos
**Analysis by**: Claude Sonnet 4.5
