"""
RAGBot - Retrieval Augmented Generation Module for Lumenis
===========================================================
Integrated RAG system using Astra DB vector database for context-aware responses.

Based on ragbot-starter architecture with Lumenis-specific optimizations.
"""

import os
import asyncio
from typing import List, Dict, Optional, Any, AsyncGenerator
from dataclasses import dataclass
from datetime import datetime

# Astra DB for vector storage
try:
    from astrapy import DataAPIClient
    from astrapy.constants import VectorMetric
    ASTRA_AVAILABLE = True
except ImportError:
    ASTRA_AVAILABLE = False
    print("⚠️  astrapy not installed for RAG. Install: pip install astrapy")

# Embeddings
try:
    import openai
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False

# Text splitting for chunking
try:
    from langchain.text_splitter import RecursiveCharacterTextSplitter
    LANGCHAIN_AVAILABLE = True
except ImportError:
    try:
        from langchain_text_splitters import RecursiveCharacterTextSplitter
        LANGCHAIN_AVAILABLE = True
    except ImportError:
        LANGCHAIN_AVAILABLE = False
        print("⚠️  langchain text splitters not available. Install: pip install langchain")


@dataclass
class RAGDocument:
    """A document stored in the RAG vector database"""
    document_id: str
    url: str
    title: str
    content: str
    chunk_index: int = 0
    vector: Optional[List[float]] = None
    metadata: Optional[Dict[str, Any]] = None


@dataclass
class RAGResult:
    """Result from RAG retrieval"""
    query: str
    context: str
    documents: List[RAGDocument]
    similarity_scores: List[float]
    response: Optional[str] = None


class LumenisRAG:
    """
    RAG (Retrieval Augmented Generation) Module for Lumenis

    Uses Astra DB for vector storage and retrieval, compatible with
    NVIDIA embeddings or OpenAI embeddings.
    """

    def __init__(
        self,
        api_endpoint: Optional[str] = None,
        token: Optional[str] = None,
        keyspace: Optional[str] = None,
        collection_name: str = "lumenis_rag",
        embedding_model: str = "nvidia/nemotron-3-embed-1b",  # nv-embedqa-e5-v5 was retired 2026-08-25 (HTTP 410)
        embedding_dimension: int = 2048,
        similarity_metric: str = "cosine"
    ):
        """
        Initialize RAG module

        Args:
            api_endpoint: Astra DB API endpoint
            token: Astra DB application token
            keyspace: Database keyspace
            collection_name: Collection name for RAG documents
            embedding_model: Model for embeddings (nvidia or openai)
            embedding_dimension: Vector dimension (1024 for NVIDIA, 1536 for OpenAI)
            similarity_metric: 'cosine', 'euclidean', or 'dot_product'
        """
        if not ASTRA_AVAILABLE:
            raise ImportError("astrapy required for RAG. Install: pip install astrapy")

        # Load from environment
        self.api_endpoint = api_endpoint or os.getenv('ASTRA_DB_API_ENDPOINT')
        self.token = token or os.getenv('ASTRA_DB_APPLICATION_TOKEN')
        self.keyspace = keyspace or os.getenv('ASTRA_DB_KEYSPACE', 'one2lvOS')

        if not self.api_endpoint or not self.token:
            raise ValueError("Astra DB credentials required (API endpoint and token)")

        # Configuration
        self.collection_name = f"{collection_name}_{similarity_metric}"
        self.embedding_model = embedding_model
        self.embedding_dimension = embedding_dimension
        self.similarity_metric = similarity_metric

        # Initialize client
        self.client = DataAPIClient(self.token)
        self.database = self.client.get_database(
            self.api_endpoint,
            namespace=self.keyspace
        )

        # Text splitter for chunking documents
        if LANGCHAIN_AVAILABLE:
            self.text_splitter = RecursiveCharacterTextSplitter(
                chunk_size=1000,
                chunk_overlap=200,
                length_function=len,
            )
        else:
            self.text_splitter = None

        # NVIDIA API client
        self.nvidia_api_key = os.getenv('NVIDIA_API_KEY')
        self.nvidia_base_url = os.getenv('NVIDIA_BASE_URL', 'https://integrate.api.nvidia.com/v1')

        # OpenAI client (fallback)
        if OPENAI_AVAILABLE:
            self.openai_client = openai.OpenAI(api_key=os.getenv('OPENAI_API_KEY'))
        else:
            self.openai_client = None

        print(f"🧠 LumenisRAG initialized: {self.collection_name} ({similarity_metric})")

    async def create_collection(self) -> bool:
        """Create the RAG collection with vector support"""
        try:
            # Map similarity metric to Astra constant
            metric_map = {
                'cosine': VectorMetric.COSINE,
                'euclidean': VectorMetric.EUCLIDEAN,
                'dot_product': VectorMetric.DOT_PRODUCT,
            }

            self.collection = self.database.create_collection(
                self.collection_name,
                dimension=self.embedding_dimension,
                metric=metric_map.get(self.similarity_metric, VectorMetric.COSINE),
                check_exists=True
            )
            print(f"✓ Collection '{self.collection_name}' ready")
            return True
        except Exception as e:
            print(f"✗ Collection creation failed: {e}")
            # Try to get existing collection
            try:
                self.collection = self.database.get_collection(self.collection_name)
                print(f"✓ Using existing collection '{self.collection_name}'")
                return True
            except:
                return False

    async def get_embedding(self, text: str) -> Optional[List[float]]:
        """Generate embedding for text using NVIDIA or OpenAI"""
        try:
            # Try NVIDIA first
            if self.nvidia_api_key and 'nvidia' in self.embedding_model.lower():
                import requests

                headers = {
                    'Authorization': f'Bearer {self.nvidia_api_key}',
                    'Content-Type': 'application/json'
                }

                payload = {
                    'input': text,
                    'model': self.embedding_model,
                    'input_type': 'query'
                }

                response = requests.post(
                    f'{self.nvidia_base_url}/embeddings',
                    headers=headers,
                    json=payload,
                    timeout=30
                )

                if response.status_code == 200:
                    data = response.json()
                    return data['data'][0]['embedding']

            # Fallback to OpenAI
            if self.openai_client:
                response = self.openai_client.embeddings.create(
                    input=text,
                    model='text-embedding-ada-002'
                )
                return response.data[0].embedding

            print("⚠️  No embedding provider available")
            return None

        except Exception as e:
            print(f"✗ Embedding generation failed: {e}")
            return None

    async def add_document(
        self,
        url: str,
        title: str,
        content: str,
        metadata: Optional[Dict] = None
    ) -> List[str]:
        """
        Add a document to RAG database (automatically chunks)

        Returns list of document IDs created
        """
        if not hasattr(self, 'collection'):
            await self.create_collection()

        # Split into chunks
        if self.text_splitter:
            chunks = self.text_splitter.split_text(content)
        else:
            # Fallback simple chunking
            chunks = [content[i:i+1000] for i in range(0, len(content), 800)]

        document_ids = []

        for i, chunk in enumerate(chunks):
            # Generate embedding
            embedding = await self.get_embedding(chunk)
            if not embedding:
                print(f"⚠️  Skipping chunk {i} - no embedding")
                continue

            # Create document ID
            doc_id = f"{url.replace('/', '_')}_{i}"

            # Insert into Astra
            try:
                self.collection.insert_one({
                    'document_id': doc_id,
                    '$vector': embedding,
                    'url': url,
                    'title': title,
                    'content': chunk,
                    'chunk_index': i,
                    'timestamp': datetime.now().isoformat(),
                    'metadata': metadata or {}
                })
                document_ids.append(doc_id)
            except Exception as e:
                print(f"✗ Failed to insert chunk {i}: {e}")

        print(f"✓ Added {len(document_ids)} chunks from '{title}'")
        return document_ids

    async def query(
        self,
        query_text: str,
        top_k: int = 5,
        include_metadata: bool = True
    ) -> RAGResult:
        """
        Query the RAG database for relevant context

        Args:
            query_text: User's query
            top_k: Number of results to return
            include_metadata: Include document metadata in results

        Returns:
            RAGResult with context and retrieved documents
        """
        if not hasattr(self, 'collection'):
            await self.create_collection()

        # Generate query embedding
        query_embedding = await self.get_embedding(query_text)
        if not query_embedding:
            return RAGResult(
                query=query_text,
                context="",
                documents=[],
                similarity_scores=[]
            )

        # Search vector database
        try:
            results = self.collection.find(
                filter={},
                sort={'$vector': query_embedding},
                limit=top_k,
                include_similarity=True
            )

            documents = []
            scores = []
            context_parts = []

            for doc in results:
                documents.append(RAGDocument(
                    document_id=doc.get('document_id', ''),
                    url=doc.get('url', ''),
                    title=doc.get('title', ''),
                    content=doc.get('content', ''),
                    chunk_index=doc.get('chunk_index', 0),
                    metadata=doc.get('metadata') if include_metadata else None
                ))
                scores.append(doc.get('$similarity', 0.0))
                context_parts.append(doc.get('content', ''))

            # Build context string
            context = "\n\n".join([
                f"[{doc.title}]\n{doc.content}"
                for doc in documents
            ])

            return RAGResult(
                query=query_text,
                context=context,
                documents=documents,
                similarity_scores=scores
            )

        except Exception as e:
            print(f"✗ Query failed: {e}")
            return RAGResult(
                query=query_text,
                context="",
                documents=[],
                similarity_scores=[]
            )

    async def generate_response(
        self,
        query: str,
        context: Optional[str] = None,
        system_prompt: Optional[str] = None,
        temperature: float = 0.7
    ) -> str:
        """
        Generate RAG-enhanced response using retrieved context

        Args:
            query: User query
            context: Retrieved context (if None, will query RAG database)
            system_prompt: Custom system prompt
            temperature: LLM temperature

        Returns:
            Generated response string
        """
        # Get context if not provided
        if context is None:
            rag_result = await self.query(query)
            context = rag_result.context

        # Default system prompt for RAG
        if system_prompt is None:
            system_prompt = f"""You are an AI assistant with access to a knowledge base.
Use the provided context to answer questions accurately.

CONTEXT:
{context}

If the answer is not in the context, say "I don't have enough information to answer that."
"""

        # For now, return context summary (full LLM integration requires reactor access)
        # This should be called through the ITT Council for full LLM generation
        return f"[RAG Context Retrieved]\n\n{context[:500]}..."

    async def get_stats(self) -> Dict[str, Any]:
        """Get RAG database statistics"""
        if not hasattr(self, 'collection'):
            await self.create_collection()

        try:
            # Count documents
            count = self.collection.count_documents({})

            return {
                'collection': self.collection_name,
                'document_count': count,
                'embedding_model': self.embedding_model,
                'embedding_dimension': self.embedding_dimension,
                'similarity_metric': self.similarity_metric,
                'status': 'operational'
            }
        except Exception as e:
            return {
                'collection': self.collection_name,
                'status': 'error',
                'error': str(e)
            }
