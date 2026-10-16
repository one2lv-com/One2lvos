# SSH Embedded Path for Lumenis Reactor Core

## Overview

Secure SSH tunnel configuration for remote access to the One2lvOS Lumenis Reactor Core.

## Features

- **Secure SSH Tunneling**: Encrypted remote access
- **Port Forwarding**: Access all Reactor Core services
- **Auto-reconnect**: SystemD service for persistent tunnels
- **Key-based Auth**: RSA 4096-bit encryption

## Quick Setup

### 1. Generate SSH Configuration

```bash
cd /home/vercel-sandbox/steamos_lumenis/one2lvos/ssh-config
chmod +x reactor-ssh.sh
./reactor-ssh.sh
```

This will:
- Generate SSH key pair (`~/.ssh/one2lv_reactor_rsa`)
- Configure SSH client (`~/.ssh/config`)
- Display public key for remote server

### 2. Add Public Key to Remote Server

Copy the public key displayed and add it to the remote server:

```bash
# On remote server
mkdir -p ~/.ssh
echo "PASTE_PUBLIC_KEY_HERE" >> ~/.ssh/authorized_keys
chmod 600 ~/.ssh/authorized_keys
chmod 700 ~/.ssh
```

Or use `ssh-copy-id`:

```bash
ssh-copy-id -i ~/.ssh/one2lv_reactor_rsa.pub user@remote-host
```

### 3. Test Connection

```bash
# Direct SSH
ssh reactor-core

# With tunnel
ssh -N -f reactor-tunnel
```

## Port Forwarding

The SSH tunnel forwards these ports:

| Local Port | Remote Service | Description |
|-----------|----------------|-------------|
| 8100 | Reactor Core API | Main API endpoint |
| 4000 | UI Server | Web interface |
| 8787 | AI Lobby | Neural bridge |
| 5353 | DNS Gateway | Domain resolution |

## Usage Examples

### Direct SSH Access

```bash
# Connect to reactor core
ssh reactor-core

# Execute remote command
ssh reactor-core "curl http://localhost:8100/health"

# Copy files
scp file.txt reactor-core:/path/to/destination
```

### SSH Tunnel (Port Forwarding)

```bash
# Start tunnel in background
ssh -N -f reactor-tunnel

# Access services locally
curl http://localhost:8100/health
curl http://localhost:8100/dns/list

# Kill tunnel
pkill -f "ssh -N -f reactor-tunnel"
```

### Persistent Tunnel with SystemD

```bash
# Install service
sudo cp ssh-tunnel.service /etc/systemd/system/reactor-tunnel@.service
sudo systemctl daemon-reload

# Enable and start
sudo systemctl enable reactor-tunnel@$USER
sudo systemctl start reactor-tunnel@$USER

# Check status
sudo systemctl status reactor-tunnel@$USER

# View logs
journalctl -u reactor-tunnel@$USER -f
```

## Configuration

### Environment Variables

Set these before running `reactor-ssh.sh`:

```bash
export REACTOR_HOST="your-server.com"
export REACTOR_PORT="8100"
export SSH_PORT="22"
export SSH_USER="one2lv"

./reactor-ssh.sh
```

### SSH Config

Location: `~/.ssh/config`

```
Host reactor-core
    HostName reactor.one2lv.local
    User one2lv
    Port 22
    IdentityFile ~/.ssh/one2lv_reactor_rsa

Host reactor-tunnel
    HostName reactor.one2lv.local
    User one2lv
    Port 22
    IdentityFile ~/.ssh/one2lv_reactor_rsa
    LocalForward 8100 localhost:8100
    LocalForward 4000 localhost:4000
    LocalForward 8787 localhost:8787
    LocalForward 5353 localhost:5353
```

## Security

### Key Management

```bash
# View public key
cat ~/.ssh/one2lv_reactor_rsa.pub

# Verify key fingerprint
ssh-keygen -lf ~/.ssh/one2lv_reactor_rsa.pub

# Change key passphrase
ssh-keygen -p -f ~/.ssh/one2lv_reactor_rsa
```

### Firewall Rules

On remote server:

```bash
# Allow SSH
sudo ufw allow 22/tcp

# Allow Reactor Core (if direct access)
sudo ufw allow 8100/tcp
sudo ufw allow 4000/tcp
```

## Troubleshooting

### Connection Refused

```bash
# Check SSH service
sudo systemctl status sshd

# Test connection
ssh -v reactor-core
```

### Permission Denied

```bash
# Check key permissions
chmod 600 ~/.ssh/one2lv_reactor_rsa
chmod 644 ~/.ssh/one2lv_reactor_rsa.pub
chmod 700 ~/.ssh

# Verify authorized_keys on remote
ssh reactor-core "cat ~/.ssh/authorized_keys"
```

### Port Already in Use

```bash
# Find process using port
lsof -i :8100

# Kill existing tunnel
pkill -f "ssh -N -f reactor-tunnel"
```

### Tunnel Drops

```bash
# Use autossh for persistent connection
sudo apt install autossh

autossh -M 0 -N -f \
  -o "ServerAliveInterval 60" \
  -o "ServerAliveCountMax 3" \
  reactor-tunnel
```

## Advanced Usage

### Dynamic Port Forwarding (SOCKS Proxy)

```bash
# Create SOCKS proxy on port 1080
ssh -D 1080 -N -f reactor-core

# Configure browser to use localhost:1080 as SOCKS5 proxy
```

### Reverse Tunnel

Allow remote server to access local services:

```bash
ssh -R 8100:localhost:8100 reactor-core
```

### Multiple Tunnels

```bash
# Custom port forwarding
ssh -L 9000:localhost:8100 \
    -L 9001:localhost:4000 \
    -N -f reactor-core
```

## Integration with Reactor Core

### Access via Tunnel

```bash
# Start tunnel
ssh -N -f reactor-tunnel

# Use Reactor Core locally
curl http://localhost:8100/health
curl http://localhost:8100/dns/list

# Open UI
xdg-open http://localhost:4000
```

### Automated Deployment

```bash
#!/bin/bash
# Deploy script

# Create tunnel
ssh -N -f reactor-tunnel

# Wait for connection
sleep 2

# Deploy
curl -X POST http://localhost:8100/deploy \
  -H "Content-Type: application/json" \
  -d '{"version": "2.0.0"}'

# Close tunnel
pkill -f "ssh -N -f reactor-tunnel"
```

## Files

- `reactor-ssh.sh` - Setup script
- `ssh-tunnel.service` - SystemD service
- `README.md` - This file

## Status

✅ **CONFIGURED**

Version: 1.0.0
Part of: One2lvOS Reactor Core v2.0.0
