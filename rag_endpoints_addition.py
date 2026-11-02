# ── RAG (Retrieval Augmented Generation) ──────────────────────────────────────
# Initialize RAG module (lazy initialization)
_rag_instance = None

def get_rag():
    """Get or create RAG instance"""
    global _rag_instance
    if _rag_instance is None:
        from lumenis_reactor_core import LumenisRAG
        _rag_instance = LumenisRAG(
            collection_name="lumenis_rag",
            similarity_metric="cosine",
            embedding_dimension=1024
        )
        asyncio.create_task(_rag_instance.create_collection())
    return _rag_instance

@app.post("/api/rag/add")
async def rag_add_document(body: dict):
    """Add a document to RAG database"""
    try:
        rag = get_rag()
        url = body.get("url", "")
        title = body.get("title", "")
        content = body.get("content", "")
        
        if not content:
            return JSONResponse({"error": "content required"}, status_code=400)
        
        doc_ids = await rag.add_document(
            url=url or f"doc_{int(time.time())}",
            title=title or "Untitled",
            content=content,
            metadata=body.get("metadata", {})
        )
        
        return JSONResponse({
            "ok": True,
            "document_ids": doc_ids,
            "chunks_created": len(doc_ids)
        })
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)

@app.post("/api/rag/query")
async def rag_query(body: dict):
    """Query RAG database for relevant context"""
    try:
        rag = get_rag()
        query = body.get("query", "").strip()
        top_k = body.get("top_k", 5)
        
        if not query:
            return JSONResponse({"error": "query required"}, status_code=400)
        
        result = await rag.query(query, top_k=top_k)
        
        return JSONResponse({
            "ok": True,
            "query": result.query,
            "context": result.context,
            "documents": [
                {
                    "document_id": doc.document_id,
                    "url": doc.url,
                    "title": doc.title,
                    "content": doc.content,
                    "chunk_index": doc.chunk_index
                }
                for doc in result.documents
            ],
            "similarity_scores": result.similarity_scores,
            "count": len(result.documents)
        })
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)

@app.get("/api/rag/stats")
async def rag_stats():
    """Get RAG database statistics"""
    try:
        rag = get_rag()
        stats = await rag.get_stats()
        return JSONResponse(stats)
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)

