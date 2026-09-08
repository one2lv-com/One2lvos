#!/usr/bin/env python3
"""
Astra DB NVIDIA Vectorize Integration Setup
Configures Astra DB with NVIDIA embedding provider for One2lvOS
"""

import os
import json
import requests
from typing import Dict, List, Optional

class AstraDBVectorize:
    """Astra DB configuration with NVIDIA embedding integration"""

    def __init__(self):
        self.api_endpoint = os.getenv("ASTRA_DB_API_ENDPOINT")
        self.token = os.getenv("ASTRA_DB_APPLICATION_TOKEN")
        self.keyspace = os.getenv("ASTRA_DB_KEYSPACE", "sovereign_memory")

        if not self.api_endpoint or not self.token:
            raise ValueError("ASTRA_DB_API_ENDPOINT and ASTRA_DB_APPLICATION_TOKEN required")

        self.headers = {
            "Token": self.token,
            "Content-Type": "application/json"
        }

    def create_nvidia_collection(
        self,
        collection_name: str,
        model_name: str = "nvidia/nv-embedqa-e5-v5",
        metric: str = "cosine"
    ) -> Dict:
        """
        Create a collection with NVIDIA vectorize integration

        Args:
            collection_name: Name of the collection
            model_name: NVIDIA embedding model (default: nvidia/nv-embedqa-e5-v5)
            metric: Similarity metric (cosine, dot_product, euclidean)

        Returns:
            Response from Astra DB
        """
        url = f"{self.api_endpoint}/api/json/v1/{self.keyspace}"

        payload = {
            "createCollection": {
                "name": collection_name,
                "options": {
                    "vector": {
                        "metric": metric,
                        "service": {
                            "provider": "nvidia",
                            "modelName": model_name
                        }
                    }
                }
            }
        }

        response = requests.post(url, headers=self.headers, json=payload)
        return response.json()

    def insert_document_with_vectorize(
        self,
        collection_name: str,
        document: Dict,
        vectorize_text: Optional[str] = None
    ) -> Dict:
        """
        Insert document with automatic NVIDIA embedding generation

        Args:
            collection_name: Target collection
            document: Document data
            vectorize_text: Text to vectorize (if None, uses $vectorize field)

        Returns:
            Insert response
        """
        url = f"{self.api_endpoint}/api/json/v1/{self.keyspace}/{collection_name}"

        if vectorize_text:
            document["$vectorize"] = vectorize_text

        payload = {
            "insertOne": {
                "document": document
            }
        }

        response = requests.post(url, headers=self.headers, json=payload)
        return response.json()

    def vector_search(
        self,
        collection_name: str,
        query_text: str,
        limit: int = 5,
        filter_query: Optional[Dict] = None
    ) -> Dict:
        """
        Perform vector similarity search using NVIDIA embeddings

        Args:
            collection_name: Collection to search
            query_text: Query text for vectorization and search
            limit: Number of results
            filter_query: Optional filter criteria

        Returns:
            Search results
        """
        url = f"{self.api_endpoint}/api/json/v1/{self.keyspace}/{collection_name}"

        payload = {
            "find": {
                "sort": {
                    "$vectorize": query_text
                },
                "options": {
                    "limit": limit,
                    "includeSimilarity": True
                }
            }
        }

        if filter_query:
            payload["find"]["filter"] = filter_query

        response = requests.post(url, headers=self.headers, json=payload)
        return response.json()

    def setup_one2lvos_collections(self):
        """Create all required collections for One2lvOS"""

        collections = [
            {
                "name": "agent_memory",
                "model": "nvidia/nv-embedqa-e5-v5",
                "metric": "cosine",
                "description": "Agent conversation and decision memory"
            },
            {
                "name": "sovereign_council",
                "model": "nvidia/nv-embedqa-e5-v5",
                "metric": "cosine",
                "description": "Council deliberation and consensus tracking"
            },
            {
                "name": "delta_engine_state",
                "model": "nvidia/nv-embedqa-e5-v5",
                "metric": "cosine",
                "description": "Delta Engine autonomous dynamics memory"
            },
            {
                "name": "system_snapshots",
                "model": "nvidia/nv-embedqa-e5-v5",
                "metric": "cosine",
                "description": "O2PNG system state snapshots metadata"
            },
            {
                "name": "user_interactions",
                "model": "nvidia/nv-embedqa-e5-v5",
                "metric": "cosine",
                "description": "User commands and interaction history"
            }
        ]

        results = []
        for collection in collections:
            print(f"Creating collection: {collection['name']}")
            try:
                result = self.create_nvidia_collection(
                    collection_name=collection["name"],
                    model_name=collection["model"],
                    metric=collection["metric"]
                )
                results.append({
                    "collection": collection["name"],
                    "status": "created",
                    "result": result
                })
                print(f"✓ {collection['name']} created successfully")
            except Exception as e:
                results.append({
                    "collection": collection["name"],
                    "status": "error",
                    "error": str(e)
                })
                print(f"✗ {collection['name']} failed: {e}")

        return results


def main():
    """Setup Astra DB with NVIDIA vectorize for One2lvOS"""

    print("=" * 80)
    print("One2lvOS - Astra DB NVIDIA Vectorize Setup")
    print("=" * 80)

    try:
        astra = AstraDBVectorize()
        print(f"\n✓ Connected to Astra DB")
        print(f"  Endpoint: {astra.api_endpoint}")
        print(f"  Keyspace: {astra.keyspace}")

        print("\nCreating collections with NVIDIA embedding integration...")
        results = astra.setup_one2lvos_collections()

        print("\n" + "=" * 80)
        print("Setup Summary:")
        print("=" * 80)

        for result in results:
            status_icon = "✓" if result["status"] == "created" else "✗"
            print(f"{status_icon} {result['collection']}: {result['status']}")

        # Test insertion
        print("\nTesting vector insertion...")
        test_doc = {
            "agent": "Gemini_Astra",
            "message": "System initialization complete",
            "timestamp": "2026-09-08T00:00:00Z",
            "$vectorize": "One2lvOS system started successfully with all agents online"
        }

        insert_result = astra.insert_document_with_vectorize(
            "agent_memory",
            test_doc
        )
        print(f"✓ Test document inserted: {insert_result.get('status', {}).get('insertedIds', [])}")

        # Test search
        print("\nTesting vector search...")
        search_result = astra.vector_search(
            "agent_memory",
            "system startup",
            limit=1
        )
        print(f"✓ Search returned {len(search_result.get('data', {}).get('documents', []))} results")

        print("\n" + "=" * 80)
        print("✓ Astra DB NVIDIA Vectorize integration ready!")
        print("=" * 80)

    except Exception as e:
        print(f"\n✗ Setup failed: {e}")
        return 1

    return 0


if __name__ == "__main__":
    exit(main())
