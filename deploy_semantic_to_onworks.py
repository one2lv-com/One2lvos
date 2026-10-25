#!/usr/bin/env python3
"""
Deploy Semantic Layer to OnWorks via Lumenis
=============================================

This script uses Lumenis to deploy the semantic layer to OnWorks.
"""

import os
import sys
import time


def deploy_via_lumenis():
    """Deploy semantic layer using Lumenis to control OnWorks"""

    print("╔══════════════════════════════════════════════════════════════════════════════╗")
    print("║          DEPLOY SEMANTIC LAYER TO ONWORKS VIA LUMENIS                        ║")
    print("╚══════════════════════════════════════════════════════════════════════════════╝")
    print()

    instructions = """
🤖 LUMENIS DEPLOYMENT INSTRUCTIONS
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

To deploy the semantic layer to OnWorks, you have several options:

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
OPTION 1: Use Lumenis via Talk Script
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Start Lumenis and give deployment instructions:

1. Start Lumenis server:
   cd /home/vercel-sandbox/One2lvos
   python3 -m uvicorn lumenis-main:app --host 0.0.0.0 --port 8000

2. In another terminal, talk to Lumenis:
   python3 talk_to_lumenis.py "Boot OnWorks from saved image, open terminal, and deploy semantic layer by running: bash <(curl -s https://raw.githubusercontent.com/one2lv-com/One2lvos/main/semantic_layer/deploy_to_onworks.sh)"

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
OPTION 2: Manual OnWorks Deployment
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

1. Go to onworks.net and launch your saved Ubuntu image

2. Open terminal and run:
   cd /home/admin/One2lvos
   git pull origin main
   cd semantic_layer
   bash deploy_to_onworks.sh

3. Configure .env file with your credentials:
   nano /home/admin/One2lvos/.env

4. Load ontologies:
   python3 semantic_cli.py load

5. Test:
   python3 semantic_cli.py stats
   python3 semantic_cli.py list agents

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
OPTION 3: One-Command Deployment
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

In OnWorks terminal, run this single command:

bash <(curl -s https://raw.githubusercontent.com/one2lv-com/One2lvos/main/semantic_layer/deploy_to_onworks.sh)

This will:
✓ Install dependencies
✓ Clone/update repository
✓ Setup semantic layer
✓ Create helper scripts

Then configure credentials and load ontologies:
cd /home/admin/One2lvos
nano .env
cd semantic_layer
python3 semantic_cli.py load

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
OPTION 4: Use Maton API Gateway
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

If Lumenis has Maton integration:

python3 talk_to_lumenis.py "Use Maton to connect to OnWorks, then deploy the semantic layer"

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

📝 REQUIRED CREDENTIALS (from .env file):
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

ASTRA_DB_API_ENDPOINT=https://9b5b1939-fd21-477d-95b8-a1aecc5f90b9-us-east-2.apps.astra.datastax.com
ASTRA_DB_APPLICATION_TOKEN=AstraCS:wdhjJlzIvxbEWgIWnNApOWDA:e4393a627e01f234e99d366c0936793e0b61462dbc0b58542b3e0e6dd06c634a
ASTRA_DB_KEYSPACE=one2lvOS

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

✅ VERIFICATION STEPS:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

After deployment, verify in OnWorks terminal:

cd /home/admin/One2lvos/semantic_layer

# Load ontologies
python3 semantic_cli.py load

# Should show: Loaded 2 ontologies, 46 triples

# Check status
python3 semantic_cli.py stats

# List agents
python3 semantic_cli.py list agents

# Should show: Lumenis, Aria

# Run demo
cd /home/admin/One2lvos
python3 lumenis_semantic_demo.py

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

📚 DOCUMENTATION:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Full deployment guide: semantic_layer/ONWORKS_DEPLOYMENT.md
Integration guide: semantic_layer/LUMENIS_INTEGRATION.md
Usage guide: semantic_layer/README.md

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"""

    print(instructions)

    # Check if Lumenis is running
    try:
        import requests
        response = requests.get("http://localhost:8000/health", timeout=2)
        if response.status_code == 200:
            print("\n✅ Lumenis server is running!")
            print("You can now use: python3 talk_to_lumenis.py <command>")
        else:
            print("\n⚠️  Lumenis server status unclear")
    except:
        print("\n⚠️  Lumenis server not detected")
        print("Start it with: python3 -m uvicorn lumenis-main:app --host 0.0.0.0 --port 8000")


def create_deployment_package():
    """Create a deployment package"""
    import tarfile

    print("\n📦 Creating deployment package...")

    package_name = "/tmp/semantic_layer_deployment.tar.gz"

    with tarfile.open(package_name, "w:gz") as tar:
        tar.add("semantic_layer", arcname="semantic_layer")
        tar.add(".env", arcname=".env")
        tar.add("lumenis_semantic_demo.py", arcname="lumenis_semantic_demo.py")

    print(f"✓ Package created: {package_name}")
    print(f"  Size: {os.path.getsize(package_name) / 1024:.1f} KB")
    print()
    print("Transfer to OnWorks:")
    print(f"  1. Download from this machine")
    print(f"  2. Upload to OnWorks")
    print(f"  3. Extract: tar -xzf semantic_layer_deployment.tar.gz")


if __name__ == "__main__":
    deploy_via_lumenis()

    print("\n" + "━" * 80)
    response = input("\nCreate deployment package? (y/n): ")
    if response.lower() == 'y':
        try:
            create_deployment_package()
        except Exception as e:
            print(f"Could not create package: {e}")

    print("\n✅ Deployment instructions displayed!")
    print("Choose an option above to deploy to OnWorks.")
