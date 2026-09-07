# Package Repository Setup - One2lvOS

## 📦 Current System: Amazon Linux 2023

**Date**: 2026-09-07
**OS**: Amazon Linux 2023 (Fedora-based)
**Package Manager**: yum / dnf
**Architecture**: x86_64

---

## 🔍 Current Repository Configuration

### Active Repositories
```bash
# View current repositories
yum repolist

# Output:
# repo id                         repo name
# amazonlinux                     Amazon Linux 2023 repository
# amazonlinux-spal                Amazon Linux 2023 SPAL repository
```

### Repository Files
```bash
# Location: /etc/yum.repos.d/

amazonlinux.repo           # Main Amazon Linux repository
amazonlinux-spal.repo      # SPAL (Special Package Access List)
```

---

## 🐧 Amazon Linux Repositories

### Main Repository Configuration

File: `/etc/yum.repos.d/amazonlinux.repo`

```ini
[amazonlinux]
name=Amazon Linux 2023 repository
baseurl=https://amazonlinux-2023-repos-$awsregion.$awsdomain/$awsrelease/main/$basearch/mirror/
enabled=1
gpgcheck=1
gpgkey=file:///etc/pki/rpm-gpg/RPM-GPG-KEY-amazon-linux-2023

[amazonlinux-kernel-6.1]
name=Amazon Linux 2023 repository - kernel-6.1
baseurl=https://amazonlinux-2023-repos-$awsregion.$awsdomain/$awsrelease/kernel-6.1/$basearch/mirror/
enabled=0
gpgcheck=1
gpgkey=file:///etc/pki/rpm-gpg/RPM-GPG-KEY-amazon-linux-2023
```

### Adding Additional Repositories

#### 1. EPEL (Extra Packages for Enterprise Linux)
```bash
# Install EPEL repository
sudo yum install -y epel-release

# Or manually add EPEL 9 (for AL2023)
sudo tee /etc/yum.repos.d/epel.repo << 'EOF'
[epel]
name=Extra Packages for Enterprise Linux 9 - $basearch
baseurl=https://download.fedoraproject.org/pub/epel/9/Everything/$basearch/
enabled=1
gpgcheck=1
gpgkey=https://download.fedoraproject.org/pub/epel/RPM-GPG-KEY-EPEL-9
EOF
```

#### 2. Docker Repository
```bash
# Add Docker CE repository
sudo tee /etc/yum.repos.d/docker-ce.repo << 'EOF'
[docker-ce-stable]
name=Docker CE Stable - $basearch
baseurl=https://download.docker.com/linux/centos/9/$basearch/stable
enabled=1
gpgcheck=1
gpgkey=https://download.docker.com/linux/centos/gpg
EOF
```

#### 3. Node.js Repository
```bash
# Add NodeSource repository for Node.js 20
curl -fsSL https://rpm.nodesource.com/setup_20.x | sudo bash -
```

#### 4. PostgreSQL Repository
```bash
# Add PostgreSQL official repository
sudo tee /etc/yum.repos.d/pgdg-redhat-all.repo << 'EOF'
[pgdg-common]
name=PostgreSQL common RPMs for RHEL/Rocky 9 - $basearch
baseurl=https://download.postgresql.org/pub/repos/yum/common/redhat/rhel-9-$basearch
enabled=1
gpgcheck=1
gpgkey=https://download.postgresql.org/pub/repos/yum/keys/PGDG-RPM-GPG-KEY-RHEL
EOF
```

---

## 🎮 Gaming & Graphics Repositories

### Steam/Proton (For Gaming Capabilities)

**Note**: Steam repos are primarily for Debian/Ubuntu. For Fedora-based systems like Amazon Linux, use RPM Fusion or Flatpak.

#### RPM Fusion (Recommended for Gaming)
```bash
# Enable RPM Fusion Free
sudo dnf install -y \
  https://download1.rpmfusion.org/free/fedora/rpmfusion-free-release-39.noarch.rpm

# Enable RPM Fusion Nonfree (for NVIDIA drivers, Steam, etc.)
sudo dnf install -y \
  https://download1.rpmfusion.org/nonfree/fedora/rpmfusion-nonfree-release-39.noarch.rpm
```

#### Flatpak (Universal Package Format)
```bash
# Install Flatpak
sudo yum install -y flatpak

# Add Flathub repository
flatpak remote-add --if-not-exists flathub https://flathub.org/repo/flathub.flatpakrepo

# Install Steam via Flatpak
flatpak install -y flathub com.valvesoftware.Steam
```

---

## 🔄 Debian Repository Equivalent

### For Debian/Ubuntu Systems Only

The repositories you provided are for **Debian Trixie** (testing):

```bash
# /etc/apt/sources.list (Debian/Ubuntu only)

# Base repository
deb http://ftp.us.debian.org/debian/ trixie main contrib non-free non-free-firmware
deb-src http://ftp.us.debian.org/debian/ trixie main contrib non-free non-free-firmware

# Security updates
deb http://security.debian.org/debian-security trixie-security main contrib non-free non-free-firmware
deb-src http://security.debian.org/debian-security trixie-security main contrib non-free non-free-firmware

# Stable updates
deb http://ftp.us.debian.org/debian/ trixie-updates main contrib non-free non-free-firmware
deb-src http://ftp.us.debian.org/debian/ trixie-updates main contrib non-free non-free-firmware

# Steam repository (Debian/Ubuntu)
deb http://repo.steampowered.com/steamos brewmaster main contrib non-free
deb-src http://repo.steampowered.com/steamos brewmaster main contrib non-free
```

**⚠️ Important**: These cannot be used on Amazon Linux as they are incompatible package formats (DEB vs RPM).

---

## 🖥️ One2lvOS Simulated Repository

### Creating Mock Repository for Aetherix Terminal

For display in One2lvOS terminal simulation:

```bash
# Create mock sources.list for display
mkdir -p /home/vercel-sandbox/One2lvos/system/etc/apt

cat > /home/vercel-sandbox/One2lvos/system/etc/apt/sources.list << 'EOF'
# One2lvOS Package Sources
# Simulated Debian-based package repositories

# Base repository
deb http://ftp.us.debian.org/debian/ trixie main contrib non-free non-free-firmware
deb-src http://ftp.us.debian.org/debian/ trixie main contrib non-free non-free-firmware

# Security updates
deb http://security.debian.org/debian-security trixie-security main contrib non-free non-free-firmware
deb-src http://security.debian.org/debian-security trixie-security main contrib non-free non-free-firmware

# Stable updates
deb http://ftp.us.debian.org/debian/ trixie-updates main contrib non-free non-free-firmware
deb-src http://ftp.us.debian.org/debian/ trixie-updates main contrib non-free non-free-firmware

# Steam repository (for gaming capabilities)
deb http://repo.steampowered.com/steamos brewmaster main contrib non-free
deb-src http://repo.steampowered.com/steamos brewmaster main contrib non-free

# One2lvOS repositories
deb http://repo.one2lv.com/debian/ stable main
deb-src http://repo.one2lv.com/debian/ stable main

# NVIDIA Container Toolkit (for AI/GPU acceleration)
deb https://nvidia.github.io/libnvidia-container/stable/deb/$(ARCH) /
deb https://nvidia.github.io/nvidia-container-runtime/stable/deb/$(ARCH) /
deb https://nvidia.github.io/nvidia-docker/debian/$(ARCH) /

# Docker CE
deb https://download.docker.com/linux/debian trixie stable

# Node.js
deb https://deb.nodesource.com/node_20.x nodistro main

# PostgreSQL
deb http://apt.postgresql.org/pub/repos/apt trixie-pgdg main
EOF
```

---

## 📦 Package Management Commands

### Amazon Linux (Current System)

#### Basic Operations
```bash
# Update package list
sudo yum check-update

# Install package
sudo yum install -y <package>

# Search for package
yum search <package>

# List installed packages
yum list installed

# Remove package
sudo yum remove <package>

# Clean cache
sudo yum clean all
```

#### DNF Commands (Modern)
```bash
# Update all packages
sudo dnf upgrade -y

# Install package group
sudo dnf groupinstall "Development Tools"

# List available groups
dnf grouplist

# Show package info
dnf info <package>
```

### Debian/Ubuntu (Reference)

```bash
# Update package list
sudo apt update

# Install package
sudo apt install -y <package>

# Search for package
apt search <package>

# List installed packages
apt list --installed

# Remove package
sudo apt remove <package>

# Clean cache
sudo apt clean
```

---

## 🔧 Common Package Installations

### Development Tools
```bash
# Amazon Linux
sudo yum groupinstall -y "Development Tools"
sudo yum install -y git python3 python3-pip nodejs npm

# Debian/Ubuntu
sudo apt install -y build-essential git python3 python3-pip nodejs npm
```

### Python Packages
```bash
# Install Python packages for One2lvOS
pip3 install astrapy openai anthropic numpy pillow flask

# For NVIDIA AI
pip3 install nvidia-nim transformers torch
```

### System Utilities
```bash
# Amazon Linux
sudo yum install -y htop tmux vim curl wget jq

# Debian/Ubuntu
sudo apt install -y htop tmux vim curl wget jq
```

---

## 🎯 One2lvOS Package Requirements

### Core Dependencies
```bash
# Python 3.11+
python3 --version

# Node.js 20+
node --version

# Package management
pip3 list
npm list -g --depth=0
```

### Required Python Packages
```bash
pip3 install -r requirements.txt
```

**requirements.txt**:
```
astrapy>=1.0.0
openai>=1.0.0
anthropic>=0.18.0
numpy>=1.24.0
pillow>=10.0.0
flask>=3.0.0
flask-cors>=4.0.0
requests>=2.31.0
python-dotenv>=1.0.0
```

### Required Node Packages
```bash
npm install --save \
  express \
  dotenv \
  @datastax/astra-db-ts \
  openai \
  cors
```

---

## 🔐 GPG Key Management

### Import Repository Keys
```bash
# EPEL
sudo rpm --import https://download.fedoraproject.org/pub/epel/RPM-GPG-KEY-EPEL-9

# Docker
sudo rpm --import https://download.docker.com/linux/centos/gpg

# PostgreSQL
sudo rpm --import https://download.postgresql.org/pub/repos/yum/keys/PGDG-RPM-GPG-KEY-RHEL
```

### Verify Package Signatures
```bash
# Check package signature
rpm -K package.rpm

# List installed keys
rpm -q gpg-pubkey --qf '%{name}-%{version}-%{release} --> %{summary}\n'
```

---

## 🚀 Repository Priority

### Setting Repository Priorities
```bash
# Install yum-plugin-priorities
sudo yum install -y yum-plugin-priorities

# Edit repository file
sudo vim /etc/yum.repos.d/amazonlinux.repo

# Add priority (lower number = higher priority)
[amazonlinux]
priority=1

[epel]
priority=10
```

---

## 📊 Repository Statistics

### Current Configuration
```
Package Manager:     yum / dnf
Active Repos:        2 (amazonlinux, amazonlinux-spal)
Package Format:      RPM
Architecture:        x86_64
GPG Verification:    Enabled
```

### Recommended Additional Repos
- ✅ EPEL (Extra packages)
- ✅ RPM Fusion (Gaming, multimedia)
- ✅ Docker CE (Containerization)
- ✅ Node.js (Latest LTS)
- ✅ PostgreSQL (Latest version)

---

## ✅ Setup Checklist

Current System (Amazon Linux):
- [x] Amazon Linux base repository active
- [x] yum/dnf package manager available
- [x] Python 3 installed
- [x] Node.js available
- [ ] EPEL repository (optional)
- [ ] RPM Fusion (for gaming/multimedia)
- [ ] Docker repository (for containers)

One2lvOS Simulation:
- [x] Mock sources.list created
- [x] Debian repository references documented
- [x] Package requirements listed
- [x] Installation commands provided

---

## 🎉 Summary

### Current Environment
- **OS**: Amazon Linux 2023 (Fedora-based)
- **Package Manager**: yum/dnf (RPM packages)
- **Repositories**: Amazon Linux main + SPAL

### Repository Setup
- ✅ Current repositories documented
- ✅ Additional repositories listed (EPEL, Docker, Node.js, PostgreSQL)
- ✅ Gaming repositories documented (RPM Fusion, Flatpak)
- ✅ Mock Debian sources.list created for One2lvOS simulation

### Note on Debian Repos
The Debian Trixie repositories you provided are **for reference only** and cannot be used on Amazon Linux. For actual package installation, use the Amazon Linux/Fedora equivalents documented above.

---

*One2lvOS - Universal Package Management* 📦🌌
