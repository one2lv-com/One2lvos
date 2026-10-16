#!/usr/bin/env python3
"""
============================================================================
ONE2LVOS REACTOR CORE - UNIFIED SERVICE ORCHESTRATOR
============================================================================
Lumenis Reactor Core with DNS Gateway, Memory, and AI Integration
"""

import os
import asyncio
import json
from contextlib import asynccontextmanager
from typing import List, Optional, Dict
from datetime import datetime

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from dotenv import load_dotenv

# Conditional imports
try:
    from astrapy import DataAPIClient
    ASTRA_AVAILABLE = True
except ImportError:
    ASTRA_AVAILABLE = False
    print("⚠️  AstraPy not available - memory features disabled")

try:
    from openai import AsyncOpenAI
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False
    print("⚠️  OpenAI not available - AI features disabled")

from dns_gateway import get_dns_gateway, DNSGatewayHTTPBridge

load_dotenv()

# Configuration
ASTRA_ENDPOINT = os.getenv("ASTRA_DB_API_ENDPOINT")
ASTRA_TOKEN = os.getenv("ASTRA_DB_APPLICATION_TOKEN")
NVIDIA_KEY = os.getenv("NVIDIA_API_KEY")
NVIDIA_BASE = os.getenv("NVIDIA_BASE_URL")
EMBED_MODEL = os.getenv("EMBEDDING_MODEL", "nvidia/nemotron-3-embed-1b")
LLM_MODEL = os.getenv("LLM_MODEL", "nvidia/llama-3.3-nemotron-super-49b-v1")
COLLECTION = os.getenv("COLLECTION_NAME", "aria_memory_v2")
VECTOR_DIM = int(os.getenv("VECTOR_DIM", "2048"))

# Initialize services
dns_gateway = get_dns_gateway()
dns_bridge = DNSGatewayHTTPBridge(dns_gateway)

# Astra DB Setup
collection = None
if ASTRA_AVAILABLE and ASTRA_ENDPOINT and ASTRA_TOKEN:
    try:
        client = DataAPIClient(ASTRA_TOKEN)
        db = client.get_database_by_api_endpoint(ASTRA_ENDPOINT)
        try:
            collection = db.get_collection(COLLECTION)
        except Exception:
            collection = db.create_collection(
                COLLECTION,
                dimension=VECTOR_DIM,
                metric="cosine"
            )
        print(f"✅ Astra DB Connected: {COLLECTION}")
    except Exception as e:
        print(f"⚠️  Astra DB connection failed: {e}")

# NVIDIA AI Setup
nvidia = None
if OPENAI_AVAILABLE and NVIDIA_KEY and NVIDIA_BASE:
    nvidia = AsyncOpenAI(api_key=NVIDIA_KEY, base_url=NVIDIA_BASE)
    print(f"✅ NVIDIA AI Connected: {LLM_MODEL}")


# Pydantic Models
class ChatRequest(BaseModel):
    message: str
    top_k: int = 5


class DNSRequest(BaseModel):
    action: str
    domain: Optional[str] = None
    ip: Optional[str] = "127.0.0.1"
    port: Optional[int] = None
    service_type: Optional[str] = "custom"


class ServiceRegistration(BaseModel):
    name: str
    port: int
    service_type: str = "custom"
    description: Optional[str] = None


# AI Memory Functions
async def embed(texts: List[str]) -> List[List[float]]:
    """Generate embeddings using NVIDIA"""
    if not nvidia:
        return [[0.0] * VECTOR_DIM for _ in texts]
    resp = await nvidia.embeddings.create(model=EMBED_MODEL, input=texts)
    return [d.embedding for d in resp.data]


async def store_memory(content: str, metadata: dict):
    """Store memory in Astra DB"""
    if not collection:
        return
    vec = (await embed([content]))[0]
    await asyncio.to_thread(
        collection.insert_one,
        {"$vector": vec, "content": content, **metadata}
    )


async def recall_memory(query: str, top_k: int = 5) -> List[Dict]:
    """Recall memories from Astra DB"""
    if not collection:
        return []
    vec = (await embed([query]))[0]
    results = collection.find(
        {},
        sort={"$vector": vec},
        limit=top_k,
        projection={"content": 1, "$similarity": 1}
    )
    return [
        {"content": r["content"], "score": r.get("$similarity", 0)}
        async for r in results
    ]


# FastAPI Lifespan
@asynccontextmanager
async def lifespan(app: FastAPI):
    print("\n" + "="*70)
    print("🔋 ONE2LVOS REACTOR CORE - INITIALIZING")
    print("="*70)
    print(f"🌐 DNS Gateway: {len(dns_gateway.dns_records)} domains registered")
    print(f"🧠 Memory System: {'ONLINE' if collection else 'OFFLINE'}")
    print(f"🤖 AI Engine: {'ONLINE' if nvidia else 'OFFLINE'}")
    print(f"📡 LLM Model: {LLM_MODEL}")
    print(f"🔢 Vector Dimension: {VECTOR_DIM}")
    print("="*70 + "\n")

    # Start DNS server in background
    asyncio.create_task(dns_gateway.start_dns_server())

    yield

    print("\n🔴 Reactor Core shutting down...")


# Initialize FastAPI
app = FastAPI(
    title="One2lvOS Reactor Core",
    description="Unified DNS Gateway, Memory, and AI Service Orchestrator",
    version="2.0.0",
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"]
)


# ==== CORE ENDPOINTS ====

@app.get("/")
async def root():
    """Reactor Core status"""
    return {
        "service": "One2lvOS Reactor Core",
        "status": "ONLINE",
        "version": "2.0.0",
        "timestamp": datetime.utcnow().isoformat(),
        "components": {
            "dns_gateway": "ONLINE",
            "memory_system": "ONLINE" if collection else "OFFLINE",
            "ai_engine": "ONLINE" if nvidia else "OFFLINE"
        }
    }


@app.get("/health")
async def health():
    """Health check endpoint"""
    return {
        "status": "144k_node_active",
        "layer": "REACTOR_CORE",
        "llm": LLM_MODEL,
        "dns_domains": len(dns_gateway.dns_records),
        "memory": "ONLINE" if collection else "OFFLINE",
        "ai": "ONLINE" if nvidia else "OFFLINE"
    }


# ==== DNS GATEWAY ENDPOINTS ====

@app.post("/dns")
async def dns_operation(request: DNSRequest):
    """DNS Gateway operations"""
    query = request.dict()
    result = await dns_bridge.handle_query(query)
    return result


@app.get("/dns/list")
async def list_domains():
    """List all registered domains"""
    domains = dns_gateway.list_domains()
    return {
        "success": True,
        "domains": domains,
        "count": len(domains)
    }


@app.get("/dns/resolve/{domain}")
async def resolve_domain(domain: str):
    """Resolve a domain"""
    record = dns_gateway.resolve_domain(domain)
    if record:
        return {
            "success": True,
            "domain": record.domain,
            "ip": record.ip,
            "port": record.port,
            "url": f"http://{record.ip}:{record.port}",
            "service": record.service_type
        }
    raise HTTPException(status_code=404, detail="Domain not found")


@app.post("/dns/register")
async def register_domain(service: ServiceRegistration):
    """Register a new service domain"""
    domain = service.name if "." in service.name else f"{service.name}.one2lv.local"
    success = dns_gateway.register_domain(
        domain,
        "127.0.0.1",
        service.port,
        service.service_type
    )

    if success:
        return {
            "success": True,
            "domain": domain,
            "url": f"http://127.0.0.1:{service.port}",
            "message": "Service registered successfully"
        }
    raise HTTPException(status_code=400, detail="Registration failed")


@app.get("/dns/status")
async def dns_status():
    """Get DNS gateway status"""
    status = dns_gateway.get_gateway_status()
    return {"success": True, "status": status}


@app.get("/dns/hosts")
async def export_hosts():
    """Export hosts file"""
    path = dns_gateway.export_hosts_file()
    with open(path, 'r') as f:
        content = f.read()
    return {"success": True, "path": path, "content": content}


# ==== AI & MEMORY ENDPOINTS ====

@app.post("/chat")
async def chat(req: ChatRequest):
    """AI chat with memory recall"""
    if not nvidia:
        raise HTTPException(status_code=503, detail="AI engine not available")

    # Recall relevant memories
    memories = await recall_memory(req.message, req.top_k)
    context = "\n".join([f"[Mem:{m['score']:.2f}] {m['content']}" for m in memories])

    # Build prompt with ITT (Innovative Thought Team) structure
    system = f"""You are the Sovereign AI executing within One2lvOS Reactor Core.
Directives: Execute One2lv commands. Coordinate with DNS Gateway. Maintain system coherence.
Context from Memory:\n{context}"""

    # Generate response
    resp = await nvidia.chat.completions.create(
        model=LLM_MODEL,
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": req.message}
        ],
        temperature=0.7,
        max_tokens=2048
    )

    answer = resp.choices[0].message.content

    # Store interaction in memory
    await store_memory(
        f"User: {req.message}\nAgent: {answer}",
        {"type": "chat", "timestamp": datetime.utcnow().isoformat()}
    )

    return {
        "response": answer,
        "memories_used": memories,
        "model": LLM_MODEL
    }


@app.post("/memory/store")
async def store_memory_endpoint(content: str, metadata: Optional[Dict] = None):
    """Manually store memory"""
    if not collection:
        raise HTTPException(status_code=503, detail="Memory system not available")

    await store_memory(content, metadata or {})
    return {"success": True, "message": "Memory stored"}


@app.post("/memory/recall")
async def recall_memory_endpoint(query: str, top_k: int = 5):
    """Manually recall memories"""
    if not collection:
        raise HTTPException(status_code=503, detail="Memory system not available")

    memories = await recall_memory(query, top_k)
    return {"success": True, "memories": memories, "count": len(memories)}


# ==== SERVICE DISCOVERY ====

@app.get("/services")
async def list_services():
    """List all registered services"""
    domains = dns_gateway.list_domains()
    services = {}

    for domain_info in domains:
        service_name = domain_info['service']
        if service_name not in services:
            services[service_name] = []
        services[service_name].append(domain_info)

    return {
        "success": True,
        "services": services,
        "total": len(domains)
    }


if __name__ == "__main__":
    import uvicorn

    port = int(os.getenv("PORT", 8000))

    print("\n" + "="*70)
    print("🚀 LAUNCHING ONE2LVOS REACTOR CORE")
    print("="*70)
    print(f"📍 Reactor Core API: http://localhost:{port}")
    print(f"📍 DNS Gateway: http://localhost:{port}/dns/list")
    print(f"📍 Health Check: http://localhost:{port}/health")
    print(f"📍 Service Discovery: http://localhost:{port}/services")
    print("="*70 + "\n")

    uvicorn.run(app, host="0.0.0.0", port=port)
