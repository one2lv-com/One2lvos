"""
Astra DB Vector Memory Integration for One2lvOS
Manages vector embeddings using NVIDIA embedding provider through Astra vectorize
"""

import os
import json
import requests
from typing import Dict, List, Optional, Any
from datetime import datetime


class AstraVectorMemory:
    """Vector memory management using Astra DB with NVIDIA embeddings"""

    def __init__(self):
        self.api_endpoint = os.getenv("ASTRA_DB_API_ENDPOINT")
        self.token = os.getenv("ASTRA_DB_APPLICATION_TOKEN")
        self.keyspace = os.getenv("ASTRA_DB_KEYSPACE", "sovereign_memory")
        self.model = os.getenv("ASTRA_NVIDIA_MODEL", "nvidia/nv-embedqa-e5-v5")

        if not self.api_endpoint or not self.token:
            raise ValueError("ASTRA_DB credentials required")

        self.headers = {
            "Token": self.token,
            "Content-Type": "application/json"
        }

        self.collections = {
            "agent_memory": "agent_memory",
            "council": "sovereign_council",
            "delta": "delta_engine_state",
            "snapshots": "system_snapshots",
            "interactions": "user_interactions"
        }

    def _api_call(self, collection: str, payload: Dict) -> Dict:
        """Make API call to Astra DB"""
        url = f"{self.api_endpoint}/api/json/v1/{self.keyspace}/{collection}"
        response = requests.post(url, headers=self.headers, json=payload)
        response.raise_for_status()
        return response.json()

    async def store_agent_memory(
        self,
        agent_name: str,
        content: str,
        metadata: Optional[Dict] = None
    ) -> str:
        """
        Store agent memory with automatic NVIDIA embedding

        Args:
            agent_name: Name of the agent
            content: Memory content to vectorize
            metadata: Additional metadata

        Returns:
            Document ID
        """
        document = {
            "agent": agent_name,
            "content": content,
            "timestamp": datetime.utcnow().isoformat(),
            "$vectorize": content,  # Automatic NVIDIA embedding
            **(metadata or {})
        }

        payload = {"insertOne": {"document": document}}
        result = self._api_call(self.collections["agent_memory"], payload)

        return result.get("status", {}).get("insertedIds", [None])[0]

    async def search_agent_memory(
        self,
        query: str,
        agent_name: Optional[str] = None,
        limit: int = 5
    ) -> List[Dict]:
        """
        Search agent memories using vector similarity

        Args:
            query: Search query (will be vectorized by NVIDIA)
            agent_name: Filter by specific agent
            limit: Number of results

        Returns:
            List of similar memories with similarity scores
        """
        payload = {
            "find": {
                "sort": {"$vectorize": query},
                "options": {
                    "limit": limit,
                    "includeSimilarity": True
                }
            }
        }

        if agent_name:
            payload["find"]["filter"] = {"agent": agent_name}

        result = self._api_call(self.collections["agent_memory"], payload)
        return result.get("data", {}).get("documents", [])

    async def store_council_deliberation(
        self,
        decision_id: str,
        agents: List[str],
        topic: str,
        deliberation: str,
        consensus: float,
        votes: Dict[str, Any]
    ) -> str:
        """Store Sovereign Council deliberation"""
        document = {
            "decision_id": decision_id,
            "agents": agents,
            "topic": topic,
            "deliberation": deliberation,
            "consensus": consensus,
            "votes": votes,
            "timestamp": datetime.utcnow().isoformat(),
            "$vectorize": f"{topic}: {deliberation}"
        }

        payload = {"insertOne": {"document": document}}
        result = self._api_call(self.collections["council"], payload)

        return result.get("status", {}).get("insertedIds", [None])[0]

    async def search_council_decisions(
        self,
        query: str,
        min_consensus: Optional[float] = None,
        limit: int = 5
    ) -> List[Dict]:
        """Search past council decisions"""
        payload = {
            "find": {
                "sort": {"$vectorize": query},
                "options": {
                    "limit": limit,
                    "includeSimilarity": True
                }
            }
        }

        if min_consensus is not None:
            payload["find"]["filter"] = {"consensus": {"$gte": min_consensus}}

        result = self._api_call(self.collections["council"], payload)
        return result.get("data", {}).get("documents", [])

    async def store_delta_state(
        self,
        cycle: int,
        energy: float,
        stability: float,
        momentum: float,
        state_description: str,
        full_state: Dict
    ) -> str:
        """Store Delta Engine state snapshot"""
        document = {
            "cycle": cycle,
            "energy": energy,
            "stability": stability,
            "momentum": momentum,
            "state_description": state_description,
            "full_state": full_state,
            "timestamp": datetime.utcnow().isoformat(),
            "$vectorize": f"Cycle {cycle}: {state_description}"
        }

        payload = {"insertOne": {"document": document}}
        result = self._api_call(self.collections["delta"], payload)

        return result.get("status", {}).get("insertedIds", [None])[0]

    async def store_o2png_snapshot(
        self,
        snapshot_id: str,
        generation: int,
        description: str,
        snapshot_path: str,
        metadata: Dict
    ) -> str:
        """Store O2PNG snapshot metadata"""
        document = {
            "snapshot_id": snapshot_id,
            "generation": generation,
            "description": description,
            "snapshot_path": snapshot_path,
            "metadata": metadata,
            "timestamp": datetime.utcnow().isoformat(),
            "$vectorize": f"Snapshot {generation}: {description}"
        }

        payload = {"insertOne": {"document": document}}
        result = self._api_call(self.collections["snapshots"], payload)

        return result.get("status", {}).get("insertedIds", [None])[0]

    async def search_snapshots(
        self,
        query: str,
        limit: int = 5
    ) -> List[Dict]:
        """Search O2PNG snapshots by description"""
        payload = {
            "find": {
                "sort": {"$vectorize": query},
                "options": {
                    "limit": limit,
                    "includeSimilarity": True
                }
            }
        }

        result = self._api_call(self.collections["snapshots"], payload)
        return result.get("data", {}).get("documents", [])

    async def store_user_interaction(
        self,
        user_id: str,
        command: str,
        response: str,
        context: Optional[Dict] = None
    ) -> str:
        """Store user interaction"""
        document = {
            "user_id": user_id,
            "command": command,
            "response": response,
            "context": context or {},
            "timestamp": datetime.utcnow().isoformat(),
            "$vectorize": f"User: {command}\nAssistant: {response}"
        }

        payload = {"insertOne": {"document": document}}
        result = self._api_call(self.collections["interactions"], payload)

        return result.get("status", {}).get("insertedIds", [None])[0]

    async def get_relevant_context(
        self,
        query: str,
        limit: int = 10
    ) -> Dict[str, List[Dict]]:
        """
        Get relevant context from all collections

        Args:
            query: Context query
            limit: Results per collection

        Returns:
            Dictionary with results from each collection
        """
        context = {}

        for name, collection in self.collections.items():
            try:
                payload = {
                    "find": {
                        "sort": {"$vectorize": query},
                        "options": {
                            "limit": limit,
                            "includeSimilarity": True
                        }
                    }
                }

                result = self._api_call(collection, payload)
                context[name] = result.get("data", {}).get("documents", [])
            except Exception as e:
                print(f"Error fetching context from {name}: {e}")
                context[name] = []

        return context


# Singleton instance
_astra_memory = None


def get_astra_memory() -> AstraVectorMemory:
    """Get or create Astra memory instance"""
    global _astra_memory
    if _astra_memory is None:
        _astra_memory = AstraVectorMemory()
    return _astra_memory
