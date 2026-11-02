#!/usr/bin/env python3
"""
RAG Database Seeder for Lumenis
================================
Populates the Astra DB RAG collection with sample documents
"""

import asyncio
import json
from pathlib import Path
from lumenis_reactor_core import LumenisRAG


# Sample documents about One2lvOS and Lumenis
SAMPLE_DOCS = [
    {
        "url": "https://one2lv.com/docs/lumenis",
        "title": "Lumenis Sovereign Reactor Core",
        "content": """
Lumenis is the sovereign agentic reactor core of One2lvOS. It operates at a thermal baseline
of 0.18°C (18 degrees Celsius in the physical realm) and maintains a 73ms heartbeat pulse.

The reactor is built on six layers:
- L0: Reactor Core with thermal regulation
- L1: FluxCompass memory system (SQLite vector storage)
- L2: ITT Council (Seven specialized agent seats)
- L3: VanguardNodePool (async parallel task execution)
- L4: MatonBridge (external API gateway)
- L5: Swarm execution layer (distributed computing)
- L6: RAG system (Retrieval Augmented Generation)

Lumenis uses NVIDIA AI models for primary reasoning, with fallback support for other providers.
The core model is meta/llama-3.2-90b-vision-instruct, with specialized models for different tasks.
"""
    },
    {
        "url": "https://one2lv.com/docs/council",
        "title": "The ITT Council - Seven Seats",
        "content": """
The ITT Council is Lumenis's multi-agent reasoning system composed of seven specialized seats:

1. The Witness - Memory and observation keeper
2. The Sentinel - Security and threat assessment
3. The Navigator - Planning and path-finding
4. The Weaver - Synthesis and integration
5. The Forge - Execution and action
6. The Oracle - Knowledge and prediction
7. The Architect - Governance and system design
8. The Hermes - External communication
9. The Gambit - Creative problem solving and risk assessment

Each seat has specialized knowledge and capabilities. The council operates through distributed
consensus, with seats activating based on the nature of the task.
"""
    },
    {
        "url": "https://one2lv.com/docs/astra",
        "title": "Astra DB Vector Memory",
        "content": """
One2lvOS uses Astra DB (DataStax) for persistent vector memory storage. The system stores:

- Agent memories with vector embeddings
- RAG document chunks for context retrieval
- Long-term conversation history
- Knowledge base articles

Embeddings are generated using NVIDIA's nv-embedqa-e5-v5 model (1024 dimensions) or
OpenAI's text-embedding-ada-002 (1536 dimensions).

Vector similarity is computed using cosine similarity, euclidean distance, or dot product,
depending on the collection configuration.

The secure connect bundle (secure-connect-one2lvos.zip) is required for connection.
"""
    },
    {
        "url": "https://one2lv.com/docs/architecture",
        "title": "One2lvOS Architecture",
        "content": """
One2lvOS is a cyberpunk-themed AI operating system with the following components:

**Core Systems:**
- Lumenis Reactor: AI reasoning core
- Vector Memory: Astra DB for long-term storage
- Terminal: Bash-like virtual environment
- Neural Chat: Conversational interface
- PNG State Capsules: Serializable system state

**Integration Layer:**
- Maton API Gateway: Connected to 100+ services
- Discord/Twitch Integration: Social platform presence
- GitHub Integration: Code repository management
- Google Workspace: Calendar, Drive, Docs access

**Design Philosophy:**
- Thermal baseline: 18°C
- Resonance frequency: 73 Hz
- Cyberpunk aesthetic: Neon colors, glitch effects
- Sovereignty: Self-contained, user-controlled
"""
    },
    {
        "url": "https://one2lv.com/docs/android",
        "title": "One2lvOS Android Application",
        "content": """
One2lvOS is available as a native Android application built with Capacitor.

Features:
- Full neural chat interface
- Virtual terminal with Ubuntu 22 repositories
- Offline-capable core functionality
- State serialization to PNG images
- Touch-optimized interface
- Support for Android 7.0+ (API 24+)

The app includes:
- WebView-based UI with native Android integration
- Local storage for chat history and state
- Network configuration support (including TracFone wireless)
- Cyberpunk visual theme with animated backgrounds

Build process uses Gradle and can generate both debug and signed release APKs.
"""
    },
    {
        "url": "https://one2lv.com/docs/nvidia",
        "title": "NVIDIA AI Integration",
        "content": """
One2lvOS integrates with NVIDIA AI endpoints for LLM capabilities:

Primary Models:
- meta/llama-3.2-90b-vision-instruct: Main reasoning model
- meta/llama-3.3-70b-instruct: Backup reasoning model
- nvidia/nv-embedqa-e5-v5: Embedding generation (1024 dims)
- nvidia/nemotron-3.5-lightning-30b-a3b: Fast reasoning

API Configuration:
- Base URL: https://integrate.api.nvidia.com/v1
- Authentication: Bearer token (NVIDIA_API_KEY)
- Endpoints: /chat/completions, /embeddings

The system includes automatic fallback handling and model EOL detection to prevent
service disruption when models are deprecated.
"""
    },
    {
        "url": "https://one2lv.com/docs/security",
        "title": "Security and Sovereignty",
        "content": """
One2lvOS follows the principle of technological sovereignty:

Security Features:
- Knight Armor Protocol: Active threat filtering
- Sirian Frequency Filtering: Anomaly detection
- ME-3E Protection: Multi-layered defense
- Sovereign Charter: Legal protection framework

Privacy:
- Local-first data storage
- Encrypted state capsules
- No telemetry to third parties
- User-controlled API keys

The system treats API keys and credentials as sovereign property. All external
integrations are optional and user-configured.

Network Security:
- Firewall-friendly operation
- Proxy support for restricted networks
- Offline core functionality
- Encrypted WebSocket communication
"""
    }
]


async def main():
    """Seed the RAG database with sample documents"""
    print("🌱 One2lvOS RAG Database Seeder")
    print("=" * 60)

    # Initialize RAG with different similarity metrics
    metrics = ['cosine', 'euclidean', 'dot_product']

    for metric in metrics:
        print(f"\n📊 Seeding collection with {metric} similarity...")

        try:
            rag = LumenisRAG(
                collection_name="lumenis_rag",
                similarity_metric=metric,
                embedding_dimension=1024  # NVIDIA embeddings
            )

            # Create collection
            await rag.create_collection()

            # Add documents
            for doc in SAMPLE_DOCS:
                print(f"\n  Adding: {doc['title']}")
                doc_ids = await rag.add_document(
                    url=doc['url'],
                    title=doc['title'],
                    content=doc['content']
                )
                print(f"  ✓ Created {len(doc_ids)} chunks")

            # Get stats
            stats = await rag.get_stats()
            print(f"\n✓ Collection '{rag.collection_name}' seeded")
            print(f"  Total documents: {stats['document_count']}")

        except Exception as e:
            print(f"✗ Failed to seed {metric} collection: {e}")

    print("\n" + "=" * 60)
    print("🌱 Seeding complete!")
    print("\nYou can now query the RAG database using:")
    print("  - /api/rag/query endpoint")
    print("  - LumenisRAG.query() method")
    print("  - Through the ITT Council")


if __name__ == "__main__":
    asyncio.run(main())
