"""
Astra DB Semantic Bridge
=========================

Bridges RDF triples with Astra DB for persistent knowledge graph storage.
Stores semantic triples as vectors for efficient querying.
"""

import os
import json
import hashlib
from typing import List, Dict, Optional, Any
from datetime import datetime
import requests

try:
    from .rdf_parser import Triple
except ImportError:
    from rdf_parser import Triple


class AstraSemanticBridge:
    """
    Bridge between RDF semantic layer and Astra DB.
    Stores triples as structured documents with vector embeddings.
    """

    def __init__(
        self,
        api_endpoint: Optional[str] = None,
        token: Optional[str] = None,
        keyspace: Optional[str] = None,
        collection_name: str = "semantic_knowledge_graph"
    ):
        self.api_endpoint = api_endpoint or os.getenv("ASTRA_DB_API_ENDPOINT")
        self.token = token or os.getenv("ASTRA_DB_APPLICATION_TOKEN")
        self.keyspace = keyspace or os.getenv("ASTRA_DB_KEYSPACE", "one2lvOS")
        self.collection_name = collection_name

        if not self.api_endpoint or not self.token:
            raise ValueError("Astra DB credentials not configured")

        self.base_url = f"{self.api_endpoint}/api/json/v1/{self.keyspace}/{self.collection_name}"
        self.headers = {
            "Token": self.token,
            "Content-Type": "application/json"
        }

        # Initialize collection
        self._ensure_collection()

    def _ensure_collection(self):
        """Ensure the semantic collection exists"""
        # Check if collection exists
        collections_url = f"{self.api_endpoint}/api/json/v1/{self.keyspace}"

        try:
            response = requests.post(
                collections_url,
                headers=self.headers,
                json={
                    "findCollections": {}
                }
            )

            if response.status_code == 200:
                data = response.json()
                collections = data.get("status", {}).get("collections", [])

                if self.collection_name not in collections:
                    # Create collection
                    self._create_collection()
        except Exception as e:
            print(f"Warning: Could not verify collection: {e}")

    def _create_collection(self):
        """Create the semantic knowledge graph collection"""
        collections_url = f"{self.api_endpoint}/api/json/v1/{self.keyspace}"

        try:
            response = requests.post(
                collections_url,
                headers=self.headers,
                json={
                    "createCollection": {
                        "name": self.collection_name,
                        "options": {
                            "vector": {
                                "dimension": 384,  # For semantic embeddings
                                "metric": "cosine"
                            }
                        }
                    }
                }
            )

            if response.status_code == 200:
                print(f"Created collection: {self.collection_name}")
            else:
                print(f"Warning: Could not create collection: {response.text}")
        except Exception as e:
            print(f"Warning: Collection creation failed: {e}")

    def _triple_to_id(self, triple: Triple) -> str:
        """Generate a unique ID for a triple"""
        triple_str = f"{triple.subject}|{triple.predicate}|{triple.object}"
        return hashlib.sha256(triple_str.encode()).hexdigest()[:16]

    def _simple_embedding(self, text: str) -> List[float]:
        """
        Generate a simple embedding vector.
        In production, use NVIDIA embedding API.
        """
        # Simple character-based embedding for demo
        # This should be replaced with NVIDIA nv-embedqa-e5-v5 API
        import hashlib

        hash_obj = hashlib.sha256(text.encode())
        hash_bytes = hash_obj.digest()

        # Convert to 384-dim vector
        embedding = []
        for i in range(384):
            byte_val = hash_bytes[i % len(hash_bytes)]
            embedding.append((byte_val / 255.0) * 2 - 1)

        return embedding

    def store_triple(self, triple: Triple, metadata: Optional[Dict] = None) -> bool:
        """Store a single RDF triple in Astra DB"""
        triple_id = self._triple_to_id(triple)

        # Create embedding from triple content
        triple_text = f"{triple.subject} {triple.predicate} {triple.object}"
        embedding = self._simple_embedding(triple_text)

        document = {
            "_id": triple_id,
            "subject": triple.subject,
            "predicate": triple.predicate,
            "object": triple.object,
            "object_type": triple.object_type,
            "triple_text": triple_text,
            "$vector": embedding,
            "created_at": datetime.utcnow().isoformat(),
            "metadata": metadata or {}
        }

        try:
            response = requests.post(
                self.base_url,
                headers=self.headers,
                json={
                    "insertOne": {
                        "document": document
                    }
                }
            )

            return response.status_code == 200
        except Exception as e:
            print(f"Error storing triple: {e}")
            return False

    def store_triples(self, triples: List[Triple], metadata: Optional[Dict] = None) -> int:
        """Store multiple triples in batch"""
        success_count = 0

        for triple in triples:
            if self.store_triple(triple, metadata):
                success_count += 1

        return success_count

    def query_triples(
        self,
        subject: Optional[str] = None,
        predicate: Optional[str] = None,
        obj: Optional[str] = None,
        limit: int = 100
    ) -> List[Dict]:
        """Query triples by subject, predicate, or object"""
        filter_dict = {}

        if subject:
            filter_dict["subject"] = subject
        if predicate:
            filter_dict["predicate"] = predicate
        if obj:
            filter_dict["object"] = obj

        try:
            response = requests.post(
                self.base_url,
                headers=self.headers,
                json={
                    "find": {
                        "filter": filter_dict,
                        "options": {
                            "limit": limit
                        }
                    }
                }
            )

            if response.status_code == 200:
                data = response.json()
                return data.get("data", {}).get("documents", [])
        except Exception as e:
            print(f"Error querying triples: {e}")

        return []

    def semantic_search(self, query: str, limit: int = 10) -> List[Dict]:
        """Perform semantic search on the knowledge graph"""
        query_vector = self._simple_embedding(query)

        try:
            response = requests.post(
                self.base_url,
                headers=self.headers,
                json={
                    "find": {
                        "sort": {"$vector": query_vector},
                        "options": {
                            "limit": limit,
                            "includeSimilarity": True
                        }
                    }
                }
            )

            if response.status_code == 200:
                data = response.json()
                return data.get("data", {}).get("documents", [])
        except Exception as e:
            print(f"Error in semantic search: {e}")

        return []

    def get_all_subjects(self) -> List[str]:
        """Get all unique subjects in the knowledge graph"""
        # This would require aggregation in production
        results = self.query_triples(limit=1000)
        subjects = list(set(doc["subject"] for doc in results))
        return subjects

    def get_related(self, entity_uri: str, depth: int = 1) -> List[Dict]:
        """Get all related entities to a given entity"""
        related = []

        # Get triples where entity is subject
        results = self.query_triples(subject=entity_uri)
        related.extend(results)

        # Get triples where entity is object
        results = self.query_triples(obj=entity_uri)
        related.extend(results)

        return related

    def clear_collection(self) -> bool:
        """Clear all triples from the collection (use with caution!)"""
        try:
            response = requests.post(
                self.base_url,
                headers=self.headers,
                json={
                    "deleteMany": {
                        "filter": {}
                    }
                }
            )

            return response.status_code == 200
        except Exception as e:
            print(f"Error clearing collection: {e}")
            return False

    def export_to_json(self, output_file: str):
        """Export the knowledge graph to JSON"""
        all_triples = self.query_triples(limit=10000)

        with open(output_file, 'w') as f:
            json.dump(all_triples, f, indent=2)

        print(f"Exported {len(all_triples)} triples to {output_file}")


if __name__ == "__main__":
    # Test the bridge
    bridge = AstraSemanticBridge()

    # Test triple
    test_triple = Triple(
        subject="http://one2lv.com/ontology#Lumenis",
        predicate="http://www.w3.org/1999/02/22-rdf-syntax-ns#type",
        object="http://one2lv.com/ontology#Agent"
    )

    print("Storing test triple...")
    success = bridge.store_triple(test_triple)
    print(f"Store success: {success}")

    print("\nQuerying triples...")
    results = bridge.query_triples(subject="http://one2lv.com/ontology#Lumenis")
    print(f"Found {len(results)} triples")

    print("\nSemantic search...")
    results = bridge.semantic_search("agent artificial intelligence")
    print(f"Found {len(results)} semantically similar triples")
