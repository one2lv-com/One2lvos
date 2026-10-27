# ONE2LVOS SEMANTIC LAYER - ONWORKS DEPLOYMENT READY ✅

## Status: Ready for OnWorks Deployment

The semantic layer is fully prepared for OnWorks deployment with multiple deployment methods.

## 🚀 Quick Deployment (Choose One)

### Option 1: One-Command Deploy (Easiest)

In OnWorks Ubuntu terminal:
```bash
bash <(curl -s https://raw.githubusercontent.com/one2lv-com/One2lvos/main/semantic_layer/deploy_to_onworks.sh)
```

Then:
```bash
cd /home/admin/One2lvos
nano .env  # Add your credentials
cd semantic_layer
python3 semantic_cli.py load
```

### Option 2: Manual Deploy

```bash
# 1. Clone repo
cd /home/admin
git clone https://github.com/one2lv-com/One2lvos.git
cd One2lvos

# 2. Configure
nano .env  # Add credentials

# 3. Load ontologies
cd semantic_layer
python3 semantic_cli.py load
```

### Option 3: Via Lumenis (Automated)

Have Lumenis deploy it for you:
```bash
python3 talk_to_lumenis.py "Boot OnWorks, open terminal, and deploy semantic layer"
```

## 📋 Required Credentials

Add these to `/home/admin/One2lvos/.env`:

```bash
ASTRA_DB_API_ENDPOINT=https://9b5b1939-fd21-477d-95b8-a1aecc5f90b9-us-east-2.apps.astra.datastax.com
ASTRA_DB_APPLICATION_TOKEN=AstraCS:YOUR_TOKEN_HERE
ASTRA_DB_KEYSPACE=one2lvOS
```

## ✅ Verification

After deployment, test in OnWorks:

```bash
cd /home/admin/One2lvos/semantic_layer

# Load ontologies
python3 semantic_cli.py load
# Expected: Loaded 2 ontologies, 46 triples

# Check status
python3 semantic_cli.py stats

# List agents
python3 semantic_cli.py list agents
# Expected: Lumenis, Aria

# Run demo
cd /home/admin/One2lvos
python3 lumenis_semantic_demo.py
```

## 📁 Deployment Files Created

```
✓ semantic_layer/deploy_to_onworks.sh - Automated deployment script
✓ semantic_layer/ONWORKS_DEPLOYMENT.md - Complete deployment guide
✓ deploy_semantic_to_onworks.py - Deployment helper
✓ lumenis_semantic_demo.py - Working demonstration
✓ All semantic layer components (14 files)
```

## 🎯 What Lumenis Can Do After Deployment

- ✓ Load RDF/OWL ontologies (46 triples)
- ✓ Query knowledge graph in Astra DB
- ✓ Semantic search on concepts
- ✓ Visualize entity relationships
- ✓ Learn new skills dynamically
- ✓ Self-awareness through ontologies
- ✓ Discover other agents
- ✓ Track system architecture

## 💬 Available Commands in OnWorks

```bash
# CLI Commands
python3 semantic_cli.py load              # Load ontologies
python3 semantic_cli.py stats             # Show statistics
python3 semantic_cli.py list agents       # List all agents
python3 semantic_cli.py query Lumenis     # Query entity
python3 semantic_cli.py search "AI"       # Semantic search
python3 semantic_cli.py visualize Lumenis # Visualize relationships

# Demo
python3 ../lumenis_semantic_demo.py       # Full demonstration
```

## 🔧 Integration with Lumenis

In OnWorks, Lumenis can use semantic layer:

```python
from semantic_layer.tools import LumenisOntologyTools

# Initialize
tools = LumenisOntologyTools()
tools.load_ontologies()

# Query self
info = tools.query_entity("Lumenis")
skills = tools.get_agent_skills("Lumenis")

# Semantic search
results = tools.semantic_search("artificial intelligence")
```

## 📚 Documentation Available

- `semantic_layer/README.md` - Full usage guide
- `semantic_layer/LUMENIS_INTEGRATION.md` - Integration instructions
- `semantic_layer/ONWORKS_DEPLOYMENT.md` - Deployment guide (detailed)
- `SEMANTIC_LAYER_COMPLETE.md` - Complete summary

## 🎉 Production Ready

- ✅ All components built and tested
- ✅ Astra DB integration working
- ✅ 46 RDF triples ready to load
- ✅ Lumenis integration demonstrated
- ✅ Deployment scripts created
- ✅ Documentation complete
- ✅ OnWorks compatible

## 🚨 Keep OnWorks Alive

OnWorks has timeout settings. Use keepalive:

```bash
cd /home/admin/One2lvos
python3 onworks_keepalive.py &
```

## 💾 Save Your Work

After successful deployment, save the OnWorks image:
1. Use OnWorks "Save" feature
2. Name it: "One2lvOS-Semantic-Ready"
3. Use this image for future sessions

## 🆘 Troubleshooting

If you encounter issues:

```bash
# Check environment
env | grep ASTRA_DB

# Test connectivity
python3 -c "from astra_semantic_bridge import AstraSemanticBridge; print('OK')"

# Reload .env
source /home/admin/One2lvos/.env

# Re-run deployment
cd /home/admin/One2lvos/semantic_layer
bash deploy_to_onworks.sh
```

## Next Steps

1. **Deploy to OnWorks** - Choose deployment method above
2. **Configure credentials** - Add to .env file
3. **Load ontologies** - Run `python3 semantic_cli.py load`
4. **Test** - Run verification commands
5. **Integrate** - Add to Lumenis startup
6. **Save image** - Preserve OnWorks configuration

---

**Ready for deployment!** Choose any method above and deploy the semantic layer to OnWorks.

For questions, see: `semantic_layer/ONWORKS_DEPLOYMENT.md`
