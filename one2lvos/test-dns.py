#!/usr/bin/env python3
import sys
sys.path.insert(0, 'core')
from dns_gateway import get_dns_gateway

gateway = get_dns_gateway()
print("\n✅ DNS Gateway Test Complete!")
print(f"   Total domains: {len(gateway.dns_records)}")
