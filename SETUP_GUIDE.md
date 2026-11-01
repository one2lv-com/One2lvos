# One2lvOS Production Setup Guide

Complete step-by-step guide to deploy One2lvOS to production.

## Quick Start (5 Minutes)

```bash
# 1. Clone repository
git clone https://github.com/one2lv-com/One2lvos.git
cd One2lvos

# 2. Configure environment
cp .env.example .env
nano .env  # Add your credentials

# 3. Deploy
make setup
```

Your system will be running at `http://localhost`

## Detailed Setup

### Step 1: Server Preparation

#### Minimum Requirements
- OS: Ubuntu 20.04+ / Debian 11+ / CentOS 8+
- RAM: 4GB minimum, 8GB recommended
- Disk: 20GB free space
- CPU: 2 cores minimum, 4 cores recommended
- Ports: 80, 443, 3000, 3002, 8787 available

#### Install Dependencies

```bash
# Update system
sudo apt-get update && sudo apt-get upgrade -y

# Install Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh

# Install Docker Compose
sudo apt-get install -y docker-compose-plugin

# Add user to docker group
sudo usermod -aG docker $USER
newgrp docker

# Verify installation
docker --version
docker compose version
```

### Step 2: Clone and Configure

```bash
# Create deployment directory
sudo mkdir -p /opt/one2lvos
sudo chown $USER:$USER /opt/one2lvos

# Clone repository
cd /opt/one2lvos
git clone https://github.com/one2lv-com/One2lvos.git .

# Create environment file
cp .env.example .env
```

### Step 3: Configure Credentials

Edit `.env` file:

```bash
nano .env
```

**Required Settings:**

```ini
# Astra DB - Get from https://astra.datastax.com
ASTRA_DB_APPLICATION_TOKEN=AstraCS:xxxxx
ASTRA_DB_API_ENDPOINT=https://xxxxx-us-east-2.apps.astra.datastax.com
ASTRA_DB_KEYSPACE=one2lvos

# OpenAI - Get from https://platform.openai.com/api-keys
OPENAI_API_KEY=sk-xxxxx
OPENAI_MODEL=gpt-4

# Application
NODE_ENV=production
```

**Optional Settings:**

```ini
# NVIDIA (for enhanced embeddings)
NVIDIA_API_KEY=nvapi-xxxxx

# NASA API (for space data)
NASA_API_KEY=xxxxx
```

### Step 4: Initial Deployment

```bash
# Option 1: Using Makefile (Recommended)
make setup

# Option 2: Using script
./deploy.sh

# Option 3: Manual
docker compose build
docker compose up -d
```

### Step 5: Verify Deployment

```bash
# Check container status
docker compose ps

# Check health
make health

# View logs
make logs
```

Expected output:
```
✓ Nginx: healthy
✓ AI Lobby: healthy
✓ Core API: healthy
```

### Step 6: Set Up Automatic Start (Optional)

```bash
# Copy systemd service file
sudo cp one2lvos.service /etc/systemd/system/

# Enable and start service
sudo systemctl daemon-reload
sudo systemctl enable one2lvos
sudo systemctl start one2lvos

# Check status
sudo systemctl status one2lvos
```

Now One2lvOS will automatically start on system boot.

### Step 7: Configure GitHub Actions (For Auto-Deploy)

#### Generate SSH Key

```bash
# On your local machine
ssh-keygen -t ed25519 -C "deploy@one2lvos" -f ~/.ssh/one2lvos_deploy

# Copy public key to server
ssh-copy-id -i ~/.ssh/one2lvos_deploy.pub user@your-server
```

#### Add GitHub Secrets

1. Go to: `https://github.com/one2lv-com/One2lvos/settings/secrets/actions`
2. Add these secrets:
   - `SSH_PRIVATE_KEY`: Content of `~/.ssh/one2lvos_deploy`
   - `SERVER_HOST`: Your server IP or domain
   - `SERVER_USER`: SSH username

#### Test Auto-Deploy

```bash
# Make a change
echo "# Test" >> README.md

# Commit and push
git add README.md
git commit -m "Test auto-deploy"
git push origin main

# Watch GitHub Actions
# https://github.com/one2lv-com/One2lvos/actions
```

### Step 8: Set Up SSL (Production)

#### Using Let's Encrypt (Free)

```bash
# Install Certbot
sudo apt-get install -y certbot

# Stop containers temporarily
docker compose down

# Get certificate
sudo certbot certonly --standalone -d your-domain.com

# Copy to project
sudo mkdir -p /opt/one2lvos/ssl
sudo cp /etc/letsencrypt/live/your-domain.com/fullchain.pem /opt/one2lvos/ssl/cert.pem
sudo cp /etc/letsencrypt/live/your-domain.com/privkey.pem /opt/one2lvos/ssl/key.pem
sudo chown -R $USER:$USER /opt/one2lvos/ssl

# Update nginx.conf to enable HTTPS
nano nginx.conf
# Uncomment the HTTPS server block

# Restart containers
docker compose up -d
```

#### Auto-Renewal

```bash
# Add cron job for certificate renewal
sudo crontab -e

# Add this line:
0 3 * * * certbot renew --quiet --deploy-hook "cd /opt/one2lvos && docker compose restart nginx"
```

### Step 9: Configure Firewall

```bash
# Install UFW (if not installed)
sudo apt-get install -y ufw

# Allow SSH (important!)
sudo ufw allow 22/tcp

# Allow HTTP/HTTPS
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp

# Enable firewall
sudo ufw enable

# Check status
sudo ufw status
```

### Step 10: Set Up Monitoring (Optional)

#### Install monitoring stack

```bash
# Add monitoring to docker-compose.yml
cat >> docker-compose.yml << 'EOF'

  prometheus:
    image: prom/prometheus
    container_name: prometheus
    volumes:
      - ./prometheus.yml:/etc/prometheus/prometheus.yml
      - prometheus-data:/prometheus
    ports:
      - "9090:9090"
    restart: always
    networks:
      - one2lvos-network

  grafana:
    image: grafana/grafana
    container_name: grafana
    ports:
      - "3001:3000"
    environment:
      - GF_SECURITY_ADMIN_PASSWORD=admin
    volumes:
      - grafana-data:/var/lib/grafana
    restart: always
    networks:
      - one2lvos-network
EOF
```

Access Grafana at `http://your-server:3001`

## Verification Checklist

- [ ] All containers are running (`docker compose ps`)
- [ ] Health checks pass (`make health`)
- [ ] UI accessible at `http://your-server`
- [ ] AI Lobby accessible at `http://your-server:8787`
- [ ] Core API accessible at `http://your-server:3002`
- [ ] Logs show no errors (`make logs`)
- [ ] Services restart automatically after server reboot
- [ ] SSL certificate installed (production)
- [ ] Firewall configured
- [ ] GitHub Actions deployment working
- [ ] Backup strategy in place

## Common Setup Issues

### Issue: Port Already in Use

```bash
# Find what's using the port
sudo lsof -i :80
sudo lsof -i :3002
sudo lsof -i :8787

# Stop the service or change ports in docker-compose.yml
```

### Issue: Permission Denied

```bash
# Add user to docker group
sudo usermod -aG docker $USER
newgrp docker
```

### Issue: Out of Memory

```bash
# Check memory usage
free -h
docker stats

# Increase swap space
sudo fallocate -l 4G /swapfile
sudo chmod 600 /swapfile
sudo mkswap /swapfile
sudo swapon /swapfile
```

### Issue: Cannot Connect to Astra DB

1. Verify token and endpoint in `.env`
2. Check network connectivity: `curl https://astra.datastax.com`
3. Ensure Astra DB is active in console
4. Check region matches (us-east-2 or us-east1)

### Issue: GitHub Actions Fails

1. Verify SSH connection: `ssh -i ~/.ssh/one2lvos_deploy user@server`
2. Check GitHub secrets are correct
3. Review GitHub Actions logs
4. Ensure deploy.sh is executable: `chmod +x deploy.sh`

## Useful Commands Reference

```bash
# Start/Stop
make up          # Start all services
make down        # Stop all services
make restart     # Restart all services

# Logs
make logs        # View all logs
make logs-ui     # View UI logs only
make logs-core   # View Core API logs only

# Maintenance
make health      # Check service health
make ps          # Show running containers
make stats       # Show resource usage
make clean       # Remove everything
make rebuild     # Rebuild from scratch

# Development
make dev         # Start local development
make test        # Run tests

# Backup
make backup      # Create configuration backup

# Updates
git pull origin main   # Get latest code
make rebuild          # Rebuild and restart
```

## Next Steps

1. **Domain Setup**: Point your domain to the server IP
2. **SSL Certificate**: Set up HTTPS for production
3. **Monitoring**: Configure Prometheus/Grafana
4. **Backups**: Set up automated backups
5. **Scaling**: Add load balancers if needed
6. **CI/CD**: Set up automated testing and deployment
7. **Documentation**: Customize for your use case

## Support

- Documentation: See `DEPLOYMENT.md` for detailed info
- Issues: https://github.com/one2lv-com/One2lvos/issues
- Community: Join our Discord
- Email: one2lv@one2lv.com

## Production Checklist

Before going live:

- [ ] Environment variables configured correctly
- [ ] SSL certificate installed and working
- [ ] Firewall rules configured
- [ ] Auto-start service enabled
- [ ] Monitoring set up
- [ ] Backup strategy implemented
- [ ] GitHub Actions tested
- [ ] Load testing completed
- [ ] Security audit performed
- [ ] DNS configured
- [ ] Error tracking enabled
- [ ] Documentation updated

## Performance Tuning

```bash
# Adjust Docker resources
# Edit /etc/docker/daemon.json
{
  "log-driver": "json-file",
  "log-opts": {
    "max-size": "10m",
    "max-file": "3"
  }
}

# Restart Docker
sudo systemctl restart docker
```

---

For more information, see:
- [DEPLOYMENT.md](./DEPLOYMENT.md) - Detailed deployment guide
- [README.md](./README.md) - Project overview
- [ARCHITECTURE.md](./ARCHITECTURE.md) - System architecture
