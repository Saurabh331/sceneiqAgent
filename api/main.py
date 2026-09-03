from fastapi import FastAPI, UploadFile, File, HTTPException
from pydantic import BaseModel
import shutil
import os
import uuid

from .ingestion import load_and_split_document
from .rag import ingest_chunks_to_bq
from .agent import process_agentic_chat, parallel_search
from .models import Document, Insight, DB

app = FastAPI(title="SceneIQ API")

import tempfile

# Ensure upload directory exists
UPLOAD_DIR = os.path.join(tempfile.gettempdir(), "sceneiq_uploads")
os.makedirs(UPLOAD_DIR, exist_ok=True)

class ChatRequest(BaseModel):
    session_id: str
    query: str

class ChatResponse(BaseModel):
    response: str
    tool_log: list[str] = []

class ResearchRequest(BaseModel):
    query: str

@app.post("/documents")
async def upload_document(file: UploadFile = File(...)):
    """Upload and register a screenplay."""
    if not file.filename:
        raise HTTPException(status_code=400, detail="No filename provided")
        
    file_ext = os.path.splitext(file.filename)[1].lower()
    if file_ext not in [".pdf", ".txt", ".md", ".docx"]:
         raise HTTPException(status_code=400, detail="Only PDF, DOCX, and TXT/MD files are supported.")
         
    file_path = os.path.join(UPLOAD_DIR, file.filename)
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
        
    try:
        doc = Document(filename=file.filename, status="processing")
        DB["documents"][doc.document_id] = doc

        chunks = load_and_split_document(file_path, file.filename)
        ingest_chunks_to_bq(chunks, doc.document_id)
        
        doc.status = "indexed"
        
        # Mock generating some insights
        mock_insight = Insight(
            type="Complexity", severity="High", evidence_chunk_ids=["mock-chunk-1"],
            explanation="Multiple night shoots detected.", confidence=0.85
        )
        DB["insights"][doc.document_id] = [mock_insight]
        
        return {"document_id": doc.document_id, "status": doc.status}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        if os.path.exists(file_path):
            os.remove(file_path)

@app.get("/documents/{id}/status")
async def get_document_status(id: str):
    """Check ingestion and indexing status."""
    doc = DB["documents"].get(id)
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    return {"document_id": id, "status": doc.status}

@app.get("/documents/{id}/insights")
async def get_document_insights(id: str):
    """Return extracted screenplay intelligence."""
    insights = DB["insights"].get(id, [])
    return {"document_id": id, "insights": insights}

@app.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """Run grounded SceneIQ conversation."""
    try:
        result = process_agentic_chat(request.session_id, request.query)
        return ChatResponse(response=result["response"], tool_log=result["tool_log"])
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/research")
async def research(request: ResearchRequest):
    """Invoke externally grounded partner research."""
    try:
        result = parallel_search(request.query)
        return {"query": request.query, "result": result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/health")
async def health_check():
    """Return readiness status."""
    return {"status": "ok"}
