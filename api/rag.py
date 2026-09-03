import json
from typing import List, Dict

# In-memory store for the MVP.
# In production, this would be BigQuery Vector Search or Vertex AI Search.
DOCUMENT_STORE: Dict[str, List[str]] = {}

def store_chunks(session_id: str, chunks: List[str]):
    """Stores text chunks for a given session."""
    DOCUMENT_STORE[session_id] = chunks

def retrieve_chunks(session_id: str, query: str, top_k: int = 3) -> List[str]:
    """
    Retrieves the most relevant chunks.
    For this MVP prototype without an active vector database, 
    we use a naive keyword matching approach as a placeholder for semantic search.
    """
    if session_id not in DOCUMENT_STORE:
        return []
        
    chunks = DOCUMENT_STORE[session_id]
    
    # Simple term frequency for mock retrieval
    query_terms = set(query.lower().split())
    scored_chunks = []
    
    for chunk in chunks:
        score = sum(1 for term in query_terms if term in chunk.lower())
        scored_chunks.append((score, chunk))
        
    # Sort by score descending
    scored_chunks.sort(key=lambda x: x[0], reverse=True)
    
    # Return top K
    return [chunk for score, chunk in scored_chunks[:top_k] if score > 0] or chunks[:top_k]

def generate_response(query: str, retrieved_chunks: List[str]) -> str:
    """
    Generates a response using an LLM.
    For this MVP, it acts as a mock generation step to ensure the pipeline works 
    before injecting actual API keys for Gemini.
    """
    if not retrieved_chunks:
        return "I couldn't find any relevant information in the uploaded screenplay to answer your question."
        
    context = "\n\n".join(retrieved_chunks)
    
    # MOCK LLM behavior: Return a canned response that includes the context.
    # In a real implementation, this would call `google-generativeai` or ADK.
    response = (
        f"Based on the provided screenplay context, here is what I found regarding your query: '{query}'\n\n"
        f"**Relevant Excerpts:**\n"
        f"{context[:500]}...\n\n"
        f"*(Note: This is a simulated response. In production, this context is passed to Google Gemini for synthesis.)*"
    )
    
    return response

def process_chat(session_id: str, query: str) -> str:
    """End-to-end RAG chat flow."""
    chunks = retrieve_chunks(session_id, query)
    response = generate_response(query, chunks)
    return response
