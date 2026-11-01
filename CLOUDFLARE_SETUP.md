# ☁️ Cloudflare Tunnel Setup for One2lvOS

**⚠️ DO THIS ONLY AFTER REVOKING ALL EXPOSED KEYS ⚠️**

**Account Email:** exf0000000@gmail.com
**Domain:** one2lv.com
**Target:** Lobby on localhost:8787

## 🚨 Before You Start

**FIRST:** Complete the security audit in `SECURITY_AUDIT_CRITICAL.md`
- [ ] Revoke all exposed NVIDIA keys
- [ ] Rotate all ASTRA DB tokens
- [ ] Regenerate SSH keys
- [ ] Revoke Discord/Twitch tokens
- [ ] Rotate all other credentials

**DO NOT proceed until ALL keys are revoked!**

## 📋 Setup Steps (10 minutes)

### Step 1: Add Domain to Cloudflare

1. Go to https://dash.cloudflare.com
2. Log in with: `exf0000000@gmail.com`
3. Click "Add a Site"
4. Enter: `one2lv.com`
5. Choose plan (Free works)
6. Cloudflare will scan DNS records
7. **Note the nameservers** (e.g., `sarah.ns.cloudflare.com`, `tobias.ns.cloudflare.com`)

### Step 2: Update Domain Registrar

Go to your domain registrar (where you bought one2lv.com):
1. Find DNS settings
2. Replace existing nameservers with Cloudflare's nameservers
3. Save changes
4. Wait 5-10 minutes for propagation

### Step 3: Create Cloudflare Tunnel

1. In Cloudflare dashboard, go to:
   - **Zero Trust** → **Networks** → **Tunnels**
2. Click **"Create a tunnel"**
3. Select **"Cloudflared"**
4. Name it: `one2lv-lobby-tunnel` (or whatever you prefer)
5. Click **"Save tunnel"**

### Step 4: Install Cloudflared on Server

Cloudflare will show you a command like:

```bash
sudo cloudflared service install eyJhIjoiYTBiNDc3...
```

**On your lobby server (the machine running port 8787):**

```bash
# Copy the exact command Cloudflare shows (with YOUR token)
sudo cloudflared service install <YOUR_TOKEN_HERE>

# Check it's running
sudo systemctl status cloudflared
```

The tunnel will now:
- Start automatically on boot
- Reconnect if connection drops
- Run as a system service

### Step 5: Configure Public Hostname

Back in Cloudflare dashboard:

1. In your tunnel settings, go to **"Public Hostname"**
2. Click **"Add a public hostname"**
3. Configure:
   - **Subdomain:** (leave blank for root) or `os` for os.one2lv.com
   - **Domain:** `one2lv.com`
   - **Type:** `HTTP`
   - **URL:** `localhost:8787`
4. Click **"Save hostname"**

### Step 6: Add Access Control (CRITICAL!)

**Before going live, protect the endpoints:**

1. Go to **Zero Trust** → **Access** → **Applications**
2. Click **"Add an application"**
3. Choose **"Self-hosted"**
4. Configure:
   - **Application name:** `One2lv Lobby`
   - **Subdomain:** (blank) or `os`
   - **Domain:** `one2lv.com`
   - **Accept all identity providers:** (enable this for email auth)
5. Click **"Next"**

### Step 7: Configure Access Policy

1. **Policy name:** `Owner Only`
2. **Action:** `Allow`
3. **Configure rules:**
   - **Selector:** `Emails`
   - **Value:** `exf0000000@gmail.com`
4. Click **"Next"** → **"Add application"**

Now when anyone visits one2lv.com, Cloudflare will:
- Show a login page
- Only allow your email to access
- Block everyone else
- Protect the open chat and terminal

## 🔒 What This Protects

With Cloudflare Access in front:
- ✅ Chat tools require login
- ✅ Terminal requires login
- ✅ Admin panels require login
- ✅ No direct access to port 8787
- ✅ Free protection (Cloudflare Free tier)

## 🧪 Test the Setup

### 1. Check Tunnel Status
```bash
sudo systemctl status cloudflared
```

Should show: `Active: active (running)`

### 2. Test Public Access

From any browser (not on the server):
```
https://one2lv.com
```

You should see:
1. Cloudflare login page
2. Enter: `exf0000000@gmail.com`
3. Check email for verification code
4. Enter code
5. Access granted → See lobby

### 3. Verify Access Control

Try from a private/incognito window with a different email:
- Should be **blocked** ✅

### 4. Check Tunnel Logs
```bash
sudo journalctl -u cloudflared -f
```

Should show successful connections.

## 📊 Cloudflare Dashboard Overview

After setup, your dashboard shows:

**Zero Trust → Networks → Tunnels:**
- Tunnel status (online/offline)
- Connected clients
- Traffic stats

**Zero Trust → Access → Applications:**
- one2lv.com application
- Access logs
- Who accessed when

**Analytics:**
- Request volume
- Geographic distribution
- Attack mitigation stats

## 🔧 Common Issues

### Tunnel Won't Start
```bash
# Check cloudflared is installed
which cloudflared

# Reinstall if needed
sudo cloudflared service uninstall
# Then run the install command from Cloudflare again
```

### Can't Access Through Domain
```bash
# Check tunnel status
sudo systemctl status cloudflared

# Check if lobby is running
curl http://localhost:8787

# Check DNS propagation
nslookup one2lv.com
```

### Access Policy Not Working
1. Go to Zero Trust → Access → Applications
2. Check policy is enabled
3. Verify email is correct
4. Try clearing browser cookies

## 🔄 Maintenance

### Restart Tunnel
```bash
sudo systemctl restart cloudflared
```

### Update Cloudflared
```bash
sudo cloudflared update
sudo systemctl restart cloudflared
```

### View Tunnel Token
```bash
sudo cat /etc/cloudflared/config.yml
```

## 🚀 Optional: Additional Hostnames

You can add more public hostnames to the same tunnel:

**Examples:**
- `api.one2lv.com` → `localhost:3000`
- `chat.one2lv.com` → `localhost:8787`
- `admin.one2lv.com` → `localhost:9000`

Each can have its own Access policy.

## 🔐 Security Best Practices

1. **Keep Access Policies Updated**
   - Review allowed emails monthly
   - Remove old team members

2. **Monitor Access Logs**
   - Check for suspicious login attempts
   - Watch for unexpected traffic

3. **Enable Cloudflare WAF** (optional)
   - Extra protection against attacks
   - Free tier has basic WAF

4. **Use HTTPS Only**
   - Cloudflare provides free SSL
   - Automatically enabled

5. **Set Up Alerts**
   - Zero Trust → Settings → Notifications
   - Alert on failed login attempts

## 📱 Mobile Access

Access works on mobile too:
1. Visit `https://one2lv.com` on phone
2. Login with `exf0000000@gmail.com`
3. Same verification process
4. Full access to lobby

## 🆘 Emergency: Disable Access

If you need to make the site completely private:

1. Go to Zero Trust → Access → Applications
2. Find `One2lv Lobby`
3. Change action to **Block** (or delete application)

This immediately blocks ALL access until you re-enable it.

## 📞 Support

- **Cloudflare Docs:** https://developers.cloudflare.com/cloudflare-one/
- **Cloudflare Discord:** https://discord.gg/cloudflaredev
- **Zero Trust Guide:** https://developers.cloudflare.com/cloudflare-one/setup/

## ✅ Checklist

Setup is complete when:
- [ ] Domain added to Cloudflare
- [ ] Nameservers updated at registrar
- [ ] Tunnel created and named
- [ ] Cloudflared installed on server
- [ ] Service is running (`systemctl status cloudflared`)
- [ ] Public hostname configured (one2lv.com → localhost:8787)
- [ ] Access application created
- [ ] Access policy configured (your email only)
- [ ] Can access via https://one2lv.com
- [ ] Access control verified (other emails blocked)
- [ ] Tunnel survives reboot test

## 🎯 Result

After completion:
- ✅ `https://one2lv.com` → Your lobby on port 8787
- ✅ Protected by Cloudflare Access (email verification)
- ✅ Tunnel automatically reconnects
- ✅ Free SSL certificate
- ✅ DDoS protection
- ✅ No exposed ports on your server

---

**Remember:** This tutorial assumes you've already revoked all exposed API keys.
Do NOT set up public access before securing your credentials.
