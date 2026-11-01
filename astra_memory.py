"""
Astra DB Vector Memory Integration for One2lvOS
Provides long-term memory and vector embeddings for AI agents
"""

import os
import json
import time
from typing import List, Dict, Optional, Any
from dataclasses import dataclass, asdict
from datetime import datetime

try:
    from astrapy import DataAPIClient
    from astrapy.constants import VectorMetric
    ASTRA_AVAILABLE = True
except ImportError:
    ASTRA_AVAILABLE = False
    print("Warning: astrapy not installed. Install with: pip install astrapy")

try:
    import openai
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False


@dataclass
class AgentMemory:
    """Represents a single agent memory entry"""
    memory_id: str
    agent_id: str
    agent_name: str
    timestamp: float
    memory_type: str  # 'conversation', 'decision', 'observation', 'action'
    content: str
    embedding: Optional[List[float]] = None
    metadata: Optional[Dict[str, Any]] = None
    importance: float = 0.5

    def to_dict(self) -> Dict:
        """Convert to dictionary for storage"""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict) -> 'AgentMemory':
        """Create from dictionary"""
        return cls(**data)


class AstraMemoryStore:
    """
    Astra DB Vector Memory Store for One2lvOS Agents
    Provides persistent memory with semantic search capabilities
    """

    def __init__(
        self,
        api_endpoint: Optional[str] = None,
        token: Optional[str] = None,
        keyspace: Optional[str] = None,
        collection_name: str = "agent_memories",
        embedding_dimension: int = 1536
    ):
        """
        Initialize Astra DB connection

        Args:
            api_endpoint: Astra DB API endpoint
            token: Astra DB application token
            keyspace: Database keyspace name
            collection_name: Collection name for memories
            embedding_dimension: Dimension of embedding vectors (1536 for OpenAI, 4096 for NVIDIA)
        """
        if not ASTRA_AVAILABLE:
            raise ImportError("astrapy package required. Install with: pip install astrapy")

        # Load from environment if not provided
        self.api_endpoint = api_endpoint or os.getenv('ASTRA_DB_API_ENDPOINT')
        self.token = token or os.getenv('ASTRA_DB_APPLICATION_TOKEN')
        self.keyspace = keyspace or os.getenv('ASTRA_DB_KEYSPACE', 'sovereign_memory')
        self.collection_name = collection_name
        self.embedding_dimension = embedding_dimension

        if not self.api_endpoint or not self.token:
            raise ValueError("Astra DB credentials required (ASTRA_DB_API_ENDPOINT and ASTRA_DB_APPLICATION_TOKEN)")

        # Initialize Astra DB client
        self.client = DataAPIClient(self.token)
        self.db = self.client.get_database(self.api_endpoint)

        # Create or get collection
        self._initialize_collection()

        print(f"✅ Astra DB Memory Store initialized: {self.keyspace}.{self.collection_name}")

    def _initialize_collection(self):
        """Create collection if it doesn't exist"""
        try:
            # Check if collection exists
            collections = self.db.list_collection_names()

            if self.collection_name not in collections:
                # Create new collection with vector support
                self.collection = self.db.create_collection(
                    self.collection_name,
                    dimension=self.embedding_dimension,
                    metric=VectorMetric.COSINE
                )
                print(f"✅ Created collection: {self.collection_name}")
            else:
                self.collection = self.db.get_collection(self.collection_name)
                print(f"✅ Connected to existing collection: {self.collection_name}")

        except Exception as e:
            print(f"❌ Error initializing collection: {e}")
            raise

    def store_memory(
        self,
        agent_id: str,
        agent_name: str,
        content: str,
        memory_type: str = "observation",
        importance: float = 0.5,
        metadata: Optional[Dict[str, Any]] = None,
        embedding: Optional[List[float]] = None
    ) -> str:
        """
        Store a new memory

        Args:
            agent_id: Unique agent identifier
            agent_name: Human-readable agent name
            content: Memory content/text
            memory_type: Type of memory (conversation, decision, observation, action)
            importance: Importance score 0.0-1.0
            metadata: Additional metadata
            embedding: Pre-computed embedding vector (optional)

        Returns:
            memory_id: Unique identifier for stored memory
        """
        # Generate memory ID
        memory_id = f"{agent_id}_{int(time.time() * 1000)}"
        timestamp = time.time()

        # Create memory object
        memory = AgentMemory(
            memory_id=memory_id,
            agent_id=agent_id,
            agent_name=agent_name,
            timestamp=timestamp,
            memory_type=memory_type,
            content=content,
            embedding=embedding,
            metadata=metadata or {},
            importance=importance
        )

        # Generate embedding if not provided
        if embedding is None and OPENAI_AVAILABLE:
            embedding = self._generate_embedding(content)

        # Prepare document
        document = {
            "_id": memory_id,
            "agent_id": agent_id,
            "agent_name": agent_name,
            "timestamp": timestamp,
            "datetime": datetime.fromtimestamp(timestamp).isoformat(),
            "memory_type": memory_type,
            "content": content,
            "importance": importance,
            "metadata": metadata or {},
            "$vector": embedding
        }

        # Store in Astra DB
        try:
            self.collection.insert_one(document)
            print(f"✅ Stored memory: {memory_id} ({agent_name})")
            return memory_id
        except Exception as e:
            print(f"❌ Error storing memory: {e}")
            raise

    def search_memories(
        self,
        query: str,
        agent_id: Optional[str] = None,
        memory_type: Optional[str] = None,
        limit: int = 10,
        min_importance: float = 0.0
    ) -> List[Dict[str, Any]]:
        """
        Search memories using semantic similarity

        Args:
            query: Search query text
            agent_id: Filter by specific agent (optional)
            memory_type: Filter by memory type (optional)
            limit: Maximum number of results
            min_importance: Minimum importance threshold

        Returns:
            List of matching memories with similarity scores
        """
        # Generate query embedding
        query_embedding = self._generate_embedding(query)

        if query_embedding is None:
            print("⚠️ Cannot generate embedding for query, falling back to text search")
            return self._text_search(query, agent_id, memory_type, limit)

        # Build filter
        filter_dict = {}
        if agent_id:
            filter_dict["agent_id"] = agent_id
        if memory_type:
            filter_dict["memory_type"] = memory_type
        if min_importance > 0:
            filter_dict["importance"] = {"$gte": min_importance}

        # Perform vector search
        try:
            results = self.collection.find(
                filter=filter_dict if filter_dict else None,
                sort={"$vector": query_embedding},
                limit=limit,
                include_similarity=True
            )

            memories = []
            for doc in results:
                memory = {
                    "memory_id": doc.get("_id"),
                    "agent_id": doc.get("agent_id"),
                    "agent_name": doc.get("agent_name"),
                    "timestamp": doc.get("timestamp"),
                    "datetime": doc.get("datetime"),
                    "memory_type": doc.get("memory_type"),
                    "content": doc.get("content"),
                    "importance": doc.get("importance"),
                    "metadata": doc.get("metadata", {}),
                    "similarity": doc.get("$similarity", 0.0)
                }
                memories.append(memory)

            return memories

        except Exception as e:
            print(f"❌ Error searching memories: {e}")
            return []

    def _text_search(
        self,
        query: str,
        agent_id: Optional[str],
        memory_type: Optional[str],
        limit: int
    ) -> List[Dict[str, Any]]:
        """Fallback text-based search without embeddings"""
        filter_dict = {}
        if agent_id:
            filter_dict["agent_id"] = agent_id
        if memory_type:
            filter_dict["memory_type"] = memory_type

        try:
            results = self.collection.find(
                filter=filter_dict if filter_dict else None,
                limit=limit
            )

            memories = []
            for doc in results:
                # Simple text matching
                if query.lower() in doc.get("content", "").lower():
                    memories.append({
                        "memory_id": doc.get("_id"),
                        "agent_id": doc.get("agent_id"),
                        "agent_name": doc.get("agent_name"),
                        "timestamp": doc.get("timestamp"),
                        "datetime": doc.get("datetime"),
                        "memory_type": doc.get("memory_type"),
                        "content": doc.get("content"),
                        "importance": doc.get("importance"),
                        "metadata": doc.get("metadata", {}),
                        "similarity": 0.5  # Default similarity for text search
                    })

            return memories[:limit]

        except Exception as e:
            print(f"❌ Error in text search: {e}")
            return []

    def get_agent_memories(
        self,
        agent_id: str,
        memory_type: Optional[str] = None,
        limit: int = 50,
        sort_by_time: bool = True
    ) -> List[Dict[str, Any]]:
        """
        Get all memories for a specific agent

        Args:
            agent_id: Agent identifier
            memory_type: Filter by memory type (optional)
            limit: Maximum number of memories
            sort_by_time: Sort by timestamp (newest first)

        Returns:
            List of agent memories
        """
        filter_dict = {"agent_id": agent_id}
        if memory_type:
            filter_dict["memory_type"] = memory_type

        try:
            sort_dict = {"timestamp": -1} if sort_by_time else None

            results = self.collection.find(
                filter=filter_dict,
                sort=sort_dict,
                limit=limit
            )

            memories = []
            for doc in results:
                memories.append({
                    "memory_id": doc.get("_id"),
                    "agent_id": doc.get("agent_id"),
                    "agent_name": doc.get("agent_name"),
                    "timestamp": doc.get("timestamp"),
                    "datetime": doc.get("datetime"),
                    "memory_type": doc.get("memory_type"),
                    "content": doc.get("content"),
                    "importance": doc.get("importance"),
                    "metadata": doc.get("metadata", {})
                })

            return memories

        except Exception as e:
            print(f"❌ Error fetching agent memories: {e}")
            return []

    def delete_memory(self, memory_id: str) -> bool:
        """Delete a specific memory"""
        try:
            result = self.collection.delete_one({"_id": memory_id})
            return result.deleted_count > 0
        except Exception as e:
            print(f"❌ Error deleting memory: {e}")
            return False

    def clear_agent_memories(self, agent_id: str) -> int:
        """Clear all memories for a specific agent"""
        try:
            result = self.collection.delete_many({"agent_id": agent_id})
            return result.deleted_count
        except Exception as e:
            print(f"❌ Error clearing agent memories: {e}")
            return 0

    def _generate_embedding(self, text: str) -> Optional[List[float]]:
        """Generate embedding vector for text using OpenAI or NVIDIA"""
        if not OPENAI_AVAILABLE:
            return None

        try:
            # Use OpenAI embeddings
            openai.api_key = os.getenv('OPENAI_API_KEY')
            if not openai.api_key:
                return None

            response = openai.embeddings.create(
                input=text,
                model="text-embedding-ada-002"
            )

            return response.data[0].embedding

        except Exception as e:
            print(f"⚠️ Error generating embedding: {e}")
            return None

    def get_stats(self) -> Dict[str, Any]:
        """Get memory store statistics"""
        try:
            # Count total documents
            total_count = self.collection.count_documents({})

            # Count by agent
            agent_counts = {}
            all_docs = self.collection.find({}, projection={"agent_id": 1, "agent_name": 1})
            for doc in all_docs:
                agent_id = doc.get("agent_id")
                agent_name = doc.get("agent_name", agent_id)
                agent_counts[agent_name] = agent_counts.get(agent_name, 0) + 1

            return {
                "total_memories": total_count,
                "agent_counts": agent_counts,
                "collection": self.collection_name,
                "keyspace": self.keyspace,
                "embedding_dimension": self.embedding_dimension
            }

        except Exception as e:
            print(f"❌ Error getting stats: {e}")
            return {
                "total_memories": 0,
                "agent_counts": {},
                "error": str(e)
            }


# Example usage
if __name__ == "__main__":
    # Initialize memory store
    memory_store = AstraMemoryStore()

    # Store some test memories
    memory_store.store_memory(
        agent_id="alpha",
        agent_name="Alpha Agent",
        content="System boot completed successfully. All agents online.",
        memory_type="observation",
        importance=0.8
    )

    memory_store.store_memory(
        agent_id="alpha",
        agent_name="Alpha Agent",
        content="Approved reactor core health check protocol.",
        memory_type="decision",
        importance=0.9
    )

    # Search memories
    results = memory_store.search_memories(
        query="reactor health",
        limit=5
    )

    print(f"\n🔍 Search Results:")
    for result in results:
        print(f"  {result['agent_name']}: {result['content'][:60]}... (similarity: {result['similarity']:.3f})")

    # Get stats
    stats = memory_store.get_stats()
    print(f"\n📊 Memory Store Stats:")
    print(f"  Total Memories: {stats['total_memories']}")
    print(f"  Agents: {stats['agent_counts']}")
