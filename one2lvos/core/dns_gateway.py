#!/usr/bin/env python3
"""
============================================================================
ONE2LVOS DNS GATEWAY - DOMAIN NAME SERVER & ROUTING CORE
============================================================================
Sovereign DNS resolver with dynamic domain registration and gateway routing
"""

import asyncio
import json
import socket
import struct
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from datetime import datetime
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("DNS_Gateway")


@dataclass
class DNSRecord:
    """DNS Record with metadata"""
    domain: str
    ip: str
    port: int
    service_type: str
    ttl: int = 3600
    created_at: str = None

    def __post_init__(self):
        if not self.created_at:
            self.created_at = datetime.utcnow().isoformat()


class One2lvDNSGateway:
    """
    Sovereign DNS Gateway for One2lvOS Network
    Handles domain resolution, service discovery, and traffic routing
    """

    def __init__(self, host: str = "0.0.0.0", port: int = 5353):
        self.host = host
        self.port = port
        self.dns_records: Dict[str, DNSRecord] = {}
        self.domain_suffix = ".one2lv.local"

        # Initialize core service domains
        self._init_core_domains()

    def _init_core_domains(self):
        """Initialize core One2lvOS service domains"""
        core_services = [
            DNSRecord("reactor.one2lv.local", "127.0.0.1", 8000, "reactor_core"),
            DNSRecord("ui.one2lv.local", "127.0.0.1", 4000, "infinity_glasses"),
            DNSRecord("memory.one2lv.local", "127.0.0.1", 8001, "astra_memory"),
            DNSRecord("ai.one2lv.local", "127.0.0.1", 8787, "ai_lobby"),
            DNSRecord("gateway.one2lv.local", "127.0.0.1", 5353, "dns_gateway"),
            DNSRecord("minimax.one2lv.local", "127.0.0.1", 8080, "minimax_engine"),
            DNSRecord("api.one2lv.local", "127.0.0.1", 3002, "python_core"),
            DNSRecord("dashboard.one2lv.local", "127.0.0.1", 9000, "dashboard"),
            DNSRecord("bios.one2lv.local", "127.0.0.1", 9001, "bios_recovery"),
        ]

        for record in core_services:
            self.dns_records[record.domain] = record
            logger.info(f"📍 Registered: {record.domain} -> {record.ip}:{record.port} [{record.service_type}]")

    def register_domain(self, domain: str, ip: str, port: int, service_type: str = "custom") -> bool:
        """Dynamically register a new domain"""
        if not domain.endswith(self.domain_suffix):
            domain = domain + self.domain_suffix

        record = DNSRecord(domain, ip, port, service_type)
        self.dns_records[domain] = record
        logger.info(f"✅ Domain registered: {domain} -> {ip}:{port}")
        return True

    def resolve_domain(self, domain: str) -> Optional[DNSRecord]:
        """Resolve domain to DNS record"""
        if not domain.endswith(self.domain_suffix):
            domain = domain + self.domain_suffix

        return self.dns_records.get(domain)

    def get_service_url(self, domain: str) -> Optional[str]:
        """Get full service URL from domain"""
        record = self.resolve_domain(domain)
        if record:
            return f"http://{record.ip}:{record.port}"
        return None

    def list_domains(self) -> List[Dict]:
        """List all registered domains"""
        return [
            {
                "domain": record.domain,
                "ip": record.ip,
                "port": record.port,
                "service": record.service_type,
                "url": f"http://{record.ip}:{record.port}",
                "created": record.created_at
            }
            for record in self.dns_records.values()
        ]

    def remove_domain(self, domain: str) -> bool:
        """Remove a domain registration"""
        if not domain.endswith(self.domain_suffix):
            domain = domain + self.domain_suffix

        if domain in self.dns_records:
            del self.dns_records[domain]
            logger.info(f"🗑️  Domain removed: {domain}")
            return True
        return False

    async def start_dns_server(self):
        """Start the DNS server for domain resolution"""
        logger.info(f"🌐 Starting DNS Gateway on {self.host}:{self.port}")
        logger.info(f"📡 Registered {len(self.dns_records)} domains")

        # Create UDP socket for DNS
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        sock.bind((self.host, self.port))
        sock.setblocking(False)

        logger.info("✅ DNS Gateway ONLINE - Ready to resolve domains")

        while True:
            try:
                # Non-blocking receive
                await asyncio.sleep(0.1)
                # In production, implement full DNS protocol here
            except Exception as e:
                logger.error(f"DNS Server error: {e}")
                await asyncio.sleep(1)

    def export_hosts_file(self, output_path: str = "/tmp/one2lv_hosts"):
        """Export DNS records to hosts file format"""
        with open(output_path, 'w') as f:
            f.write("# One2lvOS Sovereign DNS Records\n")
            f.write(f"# Generated: {datetime.utcnow().isoformat()}\n\n")

            for record in self.dns_records.values():
                f.write(f"{record.ip}\t{record.domain}\t# {record.service_type}\n")

        logger.info(f"📄 Hosts file exported to: {output_path}")
        return output_path

    def get_gateway_status(self) -> Dict:
        """Get DNS gateway status"""
        return {
            "status": "ONLINE",
            "host": self.host,
            "port": self.port,
            "domain_suffix": self.domain_suffix,
            "total_domains": len(self.dns_records),
            "services": list(set(r.service_type for r in self.dns_records.values())),
            "uptime_check": datetime.utcnow().isoformat()
        }


class DNSGatewayHTTPBridge:
    """HTTP Bridge for DNS Gateway management"""

    def __init__(self, gateway: One2lvDNSGateway):
        self.gateway = gateway

    async def handle_query(self, query: Dict) -> Dict:
        """Handle DNS query via HTTP"""
        action = query.get("action")

        if action == "resolve":
            domain = query.get("domain")
            record = self.gateway.resolve_domain(domain)
            if record:
                return {
                    "success": True,
                    "domain": record.domain,
                    "ip": record.ip,
                    "port": record.port,
                    "url": f"http://{record.ip}:{record.port}",
                    "service": record.service_type
                }
            return {"success": False, "error": "Domain not found"}

        elif action == "register":
            domain = query.get("domain")
            ip = query.get("ip", "127.0.0.1")
            port = query.get("port")
            service_type = query.get("service_type", "custom")

            success = self.gateway.register_domain(domain, ip, port, service_type)
            return {"success": success, "domain": domain}

        elif action == "list":
            domains = self.gateway.list_domains()
            return {"success": True, "domains": domains, "count": len(domains)}

        elif action == "status":
            status = self.gateway.get_gateway_status()
            return {"success": True, "status": status}

        elif action == "remove":
            domain = query.get("domain")
            success = self.gateway.remove_domain(domain)
            return {"success": success, "domain": domain}

        return {"success": False, "error": "Unknown action"}


# Singleton instance
_dns_gateway = None

def get_dns_gateway() -> One2lvDNSGateway:
    """Get or create DNS gateway instance"""
    global _dns_gateway
    if _dns_gateway is None:
        _dns_gateway = One2lvDNSGateway()
    return _dns_gateway


if __name__ == "__main__":
    # Test DNS Gateway
    gateway = One2lvDNSGateway()

    print("\n" + "="*70)
    print("ONE2LVOS DNS GATEWAY - STANDALONE TEST")
    print("="*70 + "\n")

    print("📋 Registered Domains:")
    for domain_info in gateway.list_domains():
        print(f"  • {domain_info['domain']:<30} -> {domain_info['url']:<25} [{domain_info['service']}]")

    print(f"\n🔍 Resolving 'reactor':")
    record = gateway.resolve_domain("reactor")
    if record:
        print(f"  ✅ {record.domain} -> {record.ip}:{record.port}")

    print(f"\n📊 Gateway Status:")
    status = gateway.get_gateway_status()
    for key, value in status.items():
        print(f"  {key}: {value}")

    print("\n" + "="*70)
