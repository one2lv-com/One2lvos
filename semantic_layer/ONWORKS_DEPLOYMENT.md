# OnWorks Deployment Guide - Semantic Layer

Complete guide for deploying the One2lvOS semantic layer to OnWorks.

## Overview

This guide will help you deploy the semantic layer to an OnWorks Ubuntu instance where Lumenis can use RDF ontologies and knowledge graphs.

## Prerequisites

- OnWorks account with Ubuntu instance
- One2lvOS repository access
- Astra DB credentials (from .env file)
- Network connectivity

## Deployment Methods

### Method 1: Automated Deployment (Recommended)

Use the automated deployment script:

```bash
# In OnWorks terminal
cd /home/admin
curl -O https://raw.githubusercontent.com/one2lv-com/One2lvos/main/semantic_layer/deploy_to_onworks.sh
chmod +x deploy_to_onworks.sh
./deploy_to_onworks.sh
```

This script will:
1. Check environment
2. Install dependencies
3. Clone/update repository
4. Configure environment
5. Test semantic layer
6. Create helper scripts

### Method 2: Manual Deployment

#### Step 1: Clone Repository

```bash
cd /home/admin
git clone https://github.com/one2lv-com/One2lvos.git
cd One2lvos
```

#### Step 2: Install Dependencies

```bash
# Update system
sudo apt-get update

# Install Python 3
sudo apt-get install -y python3 python3-pip

# Install Python packages
pip3 install --user requests
```

#### Step 3: Configure Environment

```bash
# Copy .env file
cd /home/admin/One2lvos
cp .env.example .env

# Edit with your credentials
nano .env
```

Required credentials:
```bash
ASTRA_DB_API_ENDPOINT=https://YOUR-DB-ID.apps.astra.datastax.com
ASTRA_DB_APPLICATION_TOKEN=AstraCS:YOUR_TOKEN
ASTRA_DB_KEYSPACE=one2lvOS
```

#### Step 4: Test Semantic Layer

```bash
cd /home/admin/One2lvos/semantic_layer

# Test RDF parser
python3 -c "from rdf_parser import RDFParser; print('✓ Parser OK')"

# Run full test
python3 test_semantic_layer.py
```

#### Step 5: Load Ontologies

```bash
# Load all ontologies into Astra DB
python3 semantic_cli.py load

# Verify
python3 semantic_cli.py stats
```

## Method 3: Boot from Saved OnWorks Image

If you have a saved OnWorks image with One2lvOS:

### Option A: Use Lumenis to Deploy

Have Lumenis boot the OnWorks instance and run deployment:

```bash
# From Maton Tasks or local terminal
# Talk to Lumenis
"Boot OnWorks from saved image and run: bash <(curl -s https://raw.githubusercontent.com/one2lv-com/One2lvos/main/start-up.sh)"
```

### Option B: Manual Boot

1. **Launch OnWorks**
   - Go to onworks.net
   - Select your saved Ubuntu image
   - Launch instance

2. **Open Terminal**
   - Once booted, open terminal
   - Set admin password: `sudo passwd admin`

3. **Run Deployment**
   ```bash
   cd /home/admin/One2lvos
   git pull origin main
   cd semantic_layer
   python3 semantic_cli.py load
   ```

## Configuration

### Environment Variables

Edit `/home/admin/One2lvos/.env`:

```bash
# Astra DB (Required)
ASTRA_DB_API_ENDPOINT=https://9b5b1939-fd21-477d-95b8-a1aecc5f90b9-us-east-2.apps.astra.datastax.com
ASTRA_DB_APPLICATION_TOKEN=AstraCS:wdhjJlzIvxbEWgIWnNApOWDA:e4393a627e01f234e99d366c0936793e0b61462dbc0b58542b3e0e6dd06c634a
ASTRA_DB_KEYSPACE=one2lvOS

# NVIDIA (Optional)
NVIDIA_API_KEY=nvapi-YOUR_KEY

# Maton (Optional)
MATON_API_KEY=v2.YOUR_KEY
```

### Persistence

OnWorks instances are ephemeral. To persist changes:

1. **Save OnWorks Image**
   - Use OnWorks "Save" feature
   - Save after deployment complete
   - Name it "One2lvOS-Semantic-Ready"

2. **Export to Google Drive**
   - Use Maton api-gateway skill
   - Save important files to cloud storage
   ```bash
   # In OnWorks
   python3 << EOF
   from maton import save_to_drive
   save_to_drive('/home/admin/One2lvos/semantic_layer', 'One2lvOS-Semantic-Backup')
   EOF
   ```

## Verification

After deployment, verify everything works:

```bash
cd /home/admin/One2lvos/semantic_layer

# 1. Test RDF parser
python3 -c "from rdf_parser import RDFParser; p = RDFParser(); print(f'✓ Parser loaded: {len(p.parse_file(\"ontologies/rdf-schema.ttl\"))} triples')"

# 2. Load ontologies
python3 semantic_cli.py load

# 3. Check statistics
python3 semantic_cli.py stats

# 4. List agents
python3 semantic_cli.py list agents

# 5. Run Lumenis demo
cd /home/admin/One2lvos
python3 lumenis_semantic_demo.py
```

Expected output:
```
✓ Loaded 2 ontologies
✓ 46 triples stored
✓ Agents: Lumenis, Aria
✓ Semantic layer operational
```

## Using Semantic Layer in OnWorks

### Quick Commands

```bash
# Navigate to semantic layer
cd /home/admin/One2lvos/semantic_layer

# Load ontologies (do this once after boot)
python3 semantic_cli.py load

# Query Lumenis
python3 semantic_cli.py query Lumenis

# Semantic search
python3 semantic_cli.py search "artificial intelligence"

# Visualize entity
python3 semantic_cli.py visualize Lumenis

# Get statistics
python3 semantic_cli.py stats
```

### Run Lumenis with Semantic Layer

```bash
cd /home/admin/One2lvos

# Run semantic demo
python3 lumenis_semantic_demo.py

# Start Lumenis with semantic capabilities
# (Add to lumenis-main.py startup)
python3 -c "
from semantic_layer.tools import LumenisOntologyTools
tools = LumenisOntologyTools()
tools.load_ontologies()
print('Lumenis semantic layer ready!')
"
```

### Keep OnWorks Alive

OnWorks has strict timeout settings. Use keepalive:

```bash
# Run in background
cd /home/admin/One2lvos
python3 onworks_keepalive.py &

# Or use screen
screen -S keepalive
python3 onworks_keepalive.py
# Press Ctrl+A, D to detach
```

## Integration with Lumenis

### Add to Lumenis Startup

Edit `/home/admin/One2lvos/lumenis-main.py`:

```python
# Add at top
import sys
sys.path.insert(0, '/home/admin/One2lvos/semantic_layer')
from tools.lumenis_ontology_tools import LumenisOntologyTools

# In Lumenis.__init__()
self.semantic = LumenisOntologyTools()
print("Loading semantic knowledge graph...")
self.semantic.load_ontologies()
print("✓ Semantic layer ready")
```

### Add Semantic Commands

```python
# In Lumenis message handling
if message.startswith('/semantic'):
    parts = message.split()
    command = parts[1] if len(parts) > 1 else 'help'
    args = parts[2:]

    from tools.lumenis_ontology_tools import lumenis_command_handler
    result = lumenis_command_handler(command, *args)
    return result
```

## Troubleshooting

### Issue: "Astra DB credentials not configured"

**Solution:**
```bash
# Check .env file exists
ls -la /home/admin/One2lvos/.env

# Verify it has credentials
grep ASTRA_DB_API_ENDPOINT /home/admin/One2lvos/.env

# Set environment manually
export ASTRA_DB_API_ENDPOINT="https://YOUR-DB-ID.apps.astra.datastax.com"
export ASTRA_DB_APPLICATION_TOKEN="AstraCS:YOUR_TOKEN"
export ASTRA_DB_KEYSPACE="one2lvOS"
```

### Issue: "Import Error"

**Solution:**
```bash
# Ensure in correct directory
cd /home/admin/One2lvos/semantic_layer

# Add to Python path
export PYTHONPATH="/home/admin/One2lvos/semantic_layer:$PYTHONPATH"

# Or run from parent directory
cd /home/admin/One2lvos
python3 -c "from semantic_layer.tools import LumenisOntologyTools"
```

### Issue: "Collection not found"

**Solution:**
```bash
# The collection is auto-created on first use
# Just run any semantic command:
python3 semantic_cli.py load
```

### Issue: OnWorks Timeout

**Solution:**
```bash
# Use keepalive script
python3 onworks_keepalive.py &

# Or ping frequently
while true; do
    python3 semantic_cli.py stats > /dev/null 2>&1
    sleep 300  # Every 5 minutes
done &
```

## Network Configuration

If OnWorks has network restrictions:

```bash
# Test Astra DB connectivity
curl -H "Token: $ASTRA_DB_APPLICATION_TOKEN" \
     "$ASTRA_DB_API_ENDPOINT/api/json/v1/$ASTRA_DB_KEYSPACE"

# If blocked, use proxy (if available)
export http_proxy="http://proxy:port"
export https_proxy="http://proxy:port"
```

## Performance Tips

1. **Preload Ontologies**: Load once on boot, cache in memory
2. **Batch Operations**: Use batch inserts for multiple triples
3. **Limit Results**: Use limit parameter in queries
4. **Cache Frequently Used Queries**: Store results locally

## Backup and Recovery

### Backup

```bash
# Export knowledge graph
cd /home/admin/One2lvos/semantic_layer
python3 semantic_cli.py export /tmp/kg_backup.json

# Save to Google Drive via Maton
python3 << EOF
import subprocess
subprocess.run(['python3', '-m', 'maton', 'googledrive', 'upload', '/tmp/kg_backup.json'])
EOF
```

### Recovery

```bash
# Re-clone repository
cd /home/admin
rm -rf One2lvos
git clone https://github.com/one2lv-com/One2lvos.git

# Re-configure
cd One2lvos
nano .env

# Reload ontologies
cd semantic_layer
python3 semantic_cli.py load
```

## Quick Reference

### File Locations
- Semantic Layer: `/home/admin/One2lvos/semantic_layer/`
- Ontologies: `/home/admin/One2lvos/semantic_layer/ontologies/`
- Environment: `/home/admin/One2lvos/.env`
- CLI Tool: `/home/admin/One2lvos/semantic_layer/semantic_cli.py`

### Common Commands
```bash
# Load ontologies
python3 semantic_cli.py load

# Query
python3 semantic_cli.py query Lumenis

# Search
python3 semantic_cli.py search "AI"

# Stats
python3 semantic_cli.py stats

# Demo
python3 ../lumenis_semantic_demo.py
```

## Support

- Documentation: `/home/admin/One2lvos/semantic_layer/README.md`
- Integration: `/home/admin/One2lvos/semantic_layer/LUMENIS_INTEGRATION.md`
- Issues: https://github.com/one2lv-com/One2lvos/issues

## Success Checklist

- [ ] OnWorks instance running
- [ ] Repository cloned
- [ ] Dependencies installed
- [ ] .env configured
- [ ] Ontologies loaded (46 triples)
- [ ] Tests passing
- [ ] Lumenis can query semantic layer
- [ ] Image saved for persistence

Once all checked, your semantic layer is ready for production use in OnWorks!
