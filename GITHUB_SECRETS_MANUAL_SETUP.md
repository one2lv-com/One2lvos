# 🔐 GitHub Secrets Manual Setup Guide

If you can't run the automated script, follow these manual steps to fix your failing workflows.

---

## 📋 Step 1: Add the Public Key to Your Server

**On your deployment server, run:**

```bash
mkdir -p ~/.ssh
echo 'ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIP0Wez4qsWdADBwz4SGQGkNIKn6X+gMX github-actions-one2lvos-deploy' >> ~/.ssh/authorized_keys
chmod 600 ~/.ssh/authorized_keys
```

---

## 🔑 Step 2: Add Secrets via GitHub Web Interface

### Go to Your Repository Settings

**URL**: https://github.com/one2lv-com/One2lvos/settings/secrets/actions

Click **"New repository secret"** for each of these:

---

### For "Deploy to Production" Workflow:

**1. SSH_PRIVATE_KEY**
```
-----BEGIN OPENSSH PRIVATE KEY-----
b3BlbnNzaC1rZXktdjEAAAAABG5vbmUAAAAEbm9uZQAAAAAAAAABAAAAMwAAAAtzc2gtZW
QyNTUxOQAAACD9Fns+KrFnQAwcM+DIpibJSpzoM+EhkBpDSCp+l/oDFwAAAKgmhOLyJoTi
8gAAAAtzc2gtZWQyNTUxOQAAACD9Fns+KrFnQAwcM+DIpibJSpzoM+EhkBpDSCp+l/oDFw
AAAEA036Te1SfwC7kHi1lhwjA+JS6kmAUe/LJVjXO05DHU8P0Wez4qsWdADBwz4MimJslK
nOgz4SGQGkNIKn6X+gMXAAAAHmdpdGh1Yi1hY3Rpb25zLW9uZTJsdm9zLWRlcGxveQECAw
QFBgc=
-----END OPENSSH PRIVATE KEY-----
```

**2. SERVER_HOST**
```
YOUR_SERVER_IP_OR_HOSTNAME
```
*Example: `192.168.1.100` or `server.example.com`*

**3. SERVER_USER**
```
YOUR_SSH_USERNAME
```
*Example: `ubuntu`, `deploy`, or `root`*

---

### For "Deploy One2lvOS to Production" Workflow:

**4. PRODUCTION_SSH_KEY**
```
(Same as SSH_PRIVATE_KEY above - copy the entire private key)
```

**5. PRODUCTION_HOST**
```
(Same as SERVER_HOST above)
```

**6. PRODUCTION_USER**
```
(Same as SERVER_USER above)
```

**7. PRODUCTION_PATH**
```
YOUR_DEPLOYMENT_DIRECTORY_PATH
```
*Example: `/var/www/one2lvos` or `/home/deploy/one2lvos`*

---

### For "One2lvOS Persistent Host Deploy" Workflow:

**First, create a "production" environment:**

1. Go to: https://github.com/one2lv-com/One2lvos/settings/environments
2. Click **"New environment"**
3. Name it: `production`
4. Click **"Configure environment"**

**Then add these secrets to the production environment:**

**8. DEPLOY_SSH_KEY**
```
(Same as SSH_PRIVATE_KEY above - copy the entire private key)
```

**9. DEPLOY_HOST**
```
(Same as SERVER_HOST above)
```

**10. DEPLOY_USER**
```
(Same as SERVER_USER above)
```

**11. DEPLOY_PATH**
```
(Same as PRODUCTION_PATH above)
```

**12. DEPLOY_KNOWN_HOSTS**
```
To get this value, run on YOUR LOCAL MACHINE:
ssh-keyscan -H YOUR_SERVER_IP_OR_HOSTNAME

Then copy the entire output here.
```

---

## 📄 Step 3: Enable GitHub Pages

**For "One2lvOS Build and Deploy" workflow:**

1. Go to: https://github.com/one2lv-com/One2lvos/settings/pages
2. Under **"Source"**, select **"GitHub Actions"**
3. Click **"Save"**

---

## ✅ Step 4: Test the Workflows

### Option A: Push a commit to trigger them
```bash
git commit --allow-empty -m "Test deployment workflows"
git push
```

### Option B: Manually trigger them

1. Go to: https://github.com/one2lv-com/One2lvos/actions
2. Click on each workflow name
3. Click **"Run workflow"** → **"Run workflow"**

---

## 📊 Summary Table

| Secret Name | Where to Add | Example Value |
|------------|--------------|---------------|
| `SSH_PRIVATE_KEY` | Repository secrets | *(private key above)* |
| `SERVER_HOST` | Repository secrets | `192.168.1.100` |
| `SERVER_USER` | Repository secrets | `ubuntu` |
| `PRODUCTION_SSH_KEY` | Repository secrets | *(same as SSH_PRIVATE_KEY)* |
| `PRODUCTION_HOST` | Repository secrets | *(same as SERVER_HOST)* |
| `PRODUCTION_USER` | Repository secrets | *(same as SERVER_USER)* |
| `PRODUCTION_PATH` | Repository secrets | `/var/www/one2lvos` |
| `DEPLOY_SSH_KEY` | **Production** environment | *(same as SSH_PRIVATE_KEY)* |
| `DEPLOY_HOST` | **Production** environment | *(same as SERVER_HOST)* |
| `DEPLOY_USER` | **Production** environment | *(same as SERVER_USER)* |
| `DEPLOY_PATH` | **Production** environment | *(same as PRODUCTION_PATH)* |
| `DEPLOY_KNOWN_HOSTS` | **Production** environment | `ssh-keyscan -H YOUR_HOST` |

---

## 🔒 Security Notes

1. **Never commit these keys to your repository**
2. **Keep the private key (`deploy_key`) secure**
3. **Only add the public key (`deploy_key.pub`) to your server**
4. **Rotate keys periodically**
5. **Use different keys for different environments if possible**

---

## ❓ Troubleshooting

### If workflows still fail after adding secrets:

1. **Check secret names are exact** (case-sensitive)
2. **Verify no extra spaces** in secret values
3. **Test SSH connection** manually from your machine:
   ```bash
   ssh -i deploy_key YOUR_USER@YOUR_HOST
   ```
4. **Check deployment path exists** on your server
5. **Ensure your server allows SSH key authentication**

### Common errors:

- **"Permission denied"** → Public key not added to server correctly
- **"Host key verification failed"** → DEPLOY_KNOWN_HOSTS not set correctly
- **"Directory not found"** → PRODUCTION_PATH/DEPLOY_PATH doesn't exist on server

---

## 📞 Need Help?

If you're still having issues:
1. Check workflow logs at: https://github.com/one2lv-com/One2lvos/actions
2. Verify your server is accessible via SSH
3. Test the SSH connection manually first

---

**Generated**: 2026-10-27
**Repository**: one2lv-com/One2lvos
