#!/bin/bash
# One2lvOS GitHub Actions Deployment Fix Script
# This script helps you configure GitHub secrets and fix deployment workflows

set -e

echo "╔══════════════════════════════════════════════════════════════════════╗"
echo "║         One2lvOS GitHub Actions Deployment Fix Script               ║"
echo "╚══════════════════════════════════════════════════════════════════════╝"
echo ""

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}This script will help you:${NC}"
echo "  1. ✓ Generate SSH keys for deployment (already done)"
echo "  2. ✓ Create missing requirements.txt (already done)"
echo "  3. → Add GitHub secrets via gh CLI"
echo "  4. → Enable GitHub Pages"
echo "  5. → Test the deployment configuration"
echo ""

# Check if gh CLI is installed
if ! command -v gh &> /dev/null; then
    echo -e "${RED}✗ GitHub CLI (gh) is not installed${NC}"
    echo "  Install it from: https://cli.github.com/"
    echo ""
    echo "  Or use the manual method below to add secrets via web interface"
    echo ""
    exit 1
fi

# Check if authenticated
if ! gh auth status &> /dev/null; then
    echo -e "${YELLOW}! GitHub CLI is not authenticated${NC}"
    echo "  Run: gh auth login"
    echo ""
    exit 1
fi

echo -e "${GREEN}✓ GitHub CLI is authenticated${NC}"
echo ""

# Get repository info
REPO=$(gh repo view --json nameWithOwner -q .nameWithOwner 2>/dev/null || echo "")

if [ -z "$REPO" ]; then
    echo -e "${RED}✗ Not in a GitHub repository or unable to detect repo${NC}"
    exit 1
fi

echo -e "${BLUE}Repository: ${GREEN}$REPO${NC}"
echo ""

# Ask if they want to add secrets
echo -e "${YELLOW}════════════════════════════════════════════════════════════════${NC}"
echo -e "${YELLOW}STEP 1: Add GitHub Secrets${NC}"
echo -e "${YELLOW}════════════════════════════════════════════════════════════════${NC}"
echo ""
echo "I've generated SSH keys for you. Now we need to add them to GitHub."
echo ""
echo -e "${BLUE}First, add this public key to your deployment server:${NC}"
echo ""
cat deploy_key.pub
echo ""
echo -e "${YELLOW}On your server, run:${NC}"
echo "  mkdir -p ~/.ssh"
echo "  echo '$(cat deploy_key.pub)' >> ~/.ssh/authorized_keys"
echo "  chmod 600 ~/.ssh/authorized_keys"
echo ""

read -p "Press Enter once you've added the public key to your server..."

echo ""
echo -e "${BLUE}Now let's configure your deployment server details:${NC}"
echo ""

read -p "Enter your deployment server IP/hostname: " SERVER_HOST
read -p "Enter SSH username (e.g., ubuntu, deploy): " SERVER_USER
read -p "Enter deployment path (e.g., /var/www/one2lvos): " DEPLOY_PATH

echo ""
echo -e "${GREEN}Adding secrets to GitHub...${NC}"
echo ""

# Read private key
PRIVATE_KEY=$(cat deploy_key)

# Add secrets for "Deploy to Production" workflow
echo "  → Adding SSH_PRIVATE_KEY..."
echo "$PRIVATE_KEY" | gh secret set SSH_PRIVATE_KEY

echo "  → Adding SERVER_HOST..."
echo "$SERVER_HOST" | gh secret set SERVER_HOST

echo "  → Adding SERVER_USER..."
echo "$SERVER_USER" | gh secret set SERVER_USER

# Add secrets for "Deploy One2lvOS to Production" workflow
echo "  → Adding PRODUCTION_SSH_KEY..."
echo "$PRIVATE_KEY" | gh secret set PRODUCTION_SSH_KEY

echo "  → Adding PRODUCTION_HOST..."
echo "$SERVER_HOST" | gh secret set PRODUCTION_HOST

echo "  → Adding PRODUCTION_USER..."
echo "$SERVER_USER" | gh secret set PRODUCTION_USER

echo "  → Adding PRODUCTION_PATH..."
echo "$DEPLOY_PATH" | gh secret set PRODUCTION_PATH

# Add secrets for "One2lvOS Persistent Host Deploy" workflow (environment)
echo "  → Adding DEPLOY_SSH_KEY (production environment)..."
echo "$PRIVATE_KEY" | gh secret set DEPLOY_SSH_KEY --env production 2>/dev/null || {
    echo -e "${YELLOW}    ! Could not set environment secret. You may need to create the 'production' environment first.${NC}"
    echo -e "${YELLOW}    ! Go to: https://github.com/$REPO/settings/environments${NC}"
}

echo "  → Adding DEPLOY_HOST (production environment)..."
echo "$SERVER_HOST" | gh secret set DEPLOY_HOST --env production 2>/dev/null

echo "  → Adding DEPLOY_USER (production environment)..."
echo "$SERVER_USER" | gh secret set DEPLOY_USER --env production 2>/dev/null

echo "  → Adding DEPLOY_PATH (production environment)..."
echo "$DEPLOY_PATH" | gh secret set DEPLOY_PATH --env production 2>/dev/null

# Generate known_hosts
echo "  → Generating DEPLOY_KNOWN_HOSTS..."
KNOWN_HOSTS=$(ssh-keyscan -H "$SERVER_HOST" 2>/dev/null || echo "")
if [ -n "$KNOWN_HOSTS" ]; then
    echo "$KNOWN_HOSTS" | gh secret set DEPLOY_KNOWN_HOSTS --env production 2>/dev/null
    echo -e "    ${GREEN}✓ Added${NC}"
else
    echo -e "    ${YELLOW}! Could not scan host. You may need to add this manually.${NC}"
fi

echo ""
echo -e "${GREEN}✓ GitHub secrets added successfully!${NC}"
echo ""

# GitHub Pages setup
echo -e "${YELLOW}════════════════════════════════════════════════════════════════${NC}"
echo -e "${YELLOW}STEP 2: Enable GitHub Pages${NC}"
echo -e "${YELLOW}════════════════════════════════════════════════════════════════${NC}"
echo ""
echo "To fix the 'One2lvOS Build and Deploy' workflow, enable GitHub Pages:"
echo ""
echo "  1. Go to: https://github.com/$REPO/settings/pages"
echo "  2. Under 'Source', select 'GitHub Actions'"
echo "  3. Click Save"
echo ""

read -p "Press Enter once you've enabled GitHub Pages..."

echo ""
echo -e "${GREEN}✓ All configuration steps complete!${NC}"
echo ""

# Trigger workflows
echo -e "${YELLOW}════════════════════════════════════════════════════════════════${NC}"
echo -e "${YELLOW}STEP 3: Test the Deployment${NC}"
echo -e "${YELLOW}════════════════════════════════════════════════════════════════${NC}"
echo ""
echo "Would you like to trigger the workflows now to test them?"
echo ""

read -p "Trigger workflows? (y/n): " TRIGGER

if [ "$TRIGGER" = "y" ] || [ "$TRIGGER" = "Y" ]; then
    echo ""
    echo "Triggering workflows..."

    gh workflow run "deploy.yml" 2>/dev/null && echo -e "  ${GREEN}✓${NC} Deploy to Production" || echo -e "  ${RED}✗${NC} Deploy to Production"
    gh workflow run "deploy-production.yml" 2>/dev/null && echo -e "  ${GREEN}✓${NC} Deploy One2lvOS to Production" || echo -e "  ${RED}✗${NC} Deploy One2lvOS to Production"
    gh workflow run "deploy-host.yml" 2>/dev/null && echo -e "  ${GREEN}✓${NC} One2lvOS Persistent Host Deploy" || echo -e "  ${RED}✗${NC} One2lvOS Persistent Host Deploy"
    gh workflow run "deploy-pages.yml" 2>/dev/null && echo -e "  ${GREEN}✓${NC} One2lvOS Build and Deploy" || echo -e "  ${RED}✗${NC} One2lvOS Build and Deploy"

    echo ""
    echo "Check workflow status at: https://github.com/$REPO/actions"
fi

echo ""
echo "╔══════════════════════════════════════════════════════════════════════╗"
echo "║                    🎉 Setup Complete! 🎉                             ║"
echo "╚══════════════════════════════════════════════════════════════════════╝"
echo ""
echo -e "${GREEN}What was fixed:${NC}"
echo "  ✓ Created missing requirements.txt file"
echo "  ✓ Generated SSH deployment keys"
echo "  ✓ Added all required GitHub secrets"
echo "  ✓ Configured deployment environments"
echo ""
echo -e "${BLUE}Next steps:${NC}"
echo "  • Monitor workflows at: https://github.com/$REPO/actions"
echo "  • If any still fail, check the logs for specific errors"
echo "  • Your deployment keys are in: deploy_key and deploy_key.pub"
echo ""
echo -e "${YELLOW}Security note:${NC}"
echo "  • Keep deploy_key private and secure"
echo "  • Consider deleting these keys from the sandbox after setup"
echo "  • Rotate keys periodically for security"
echo ""
