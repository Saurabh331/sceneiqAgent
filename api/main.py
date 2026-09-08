from fastapi import FastAPI, UploadFile, File, HTTPException, BackgroundTasks, Form
from pydantic import BaseModel
from typing import List, Optional
import shutil
import os
import uuid
import tempfile
import logging

from .logger import get_logger
from .ingestion import load_and_split_document
from .rag import ingest_chunks_to_bq
from .agent import parallel_search
from .models import Document, Insight, DB
from .auth import verify_user_token
from fastapi import Depends

from .tools import producers, writers, enthusiasts

logger = get_logger(__name__)

app = FastAPI(title="SceneIQ API")

app.include_router(producers.router)
app.include_router(writers.router)
app.include_router(enthusiasts.router)

# Ensure upload directory exists
UPLOAD_DIR = os.path.join(tempfile.gettempdir(), "sceneiq_uploads")
os.makedirs(UPLOAD_DIR, exist_ok=True)

class ChatRequest(BaseModel):
    session_id: str = None
    query: str
    system_instruction: str = None

class ChatResponse(BaseModel):
    response: str
    tool_log: list[str] = []

class ResearchRequest(BaseModel):
    query: str


def process_document_background(file_path: str, filename: str, document_id: str, extract_props: bool, embedding_type: str):
    try:
        logger.info(f"Processing document {document_id} in background: {filename}")
        chunks, scenes = load_and_split_document(file_path, filename, extract_props)
        ingest_chunks_to_bq(chunks, document_id, embedding_type)
        
        doc = DB["documents"].get(document_id)
        if doc:
            doc.status = "indexed"
            doc.scenes = scenes
            
        mock_insight = Insight(
            type="Complexity", severity="High", evidence_chunk_ids=["mock-chunk-1"],
            explanation="Multiple night shoots detected.", confidence=0.85
        )
        DB["insights"][document_id] = [mock_insight]
        logger.info(f"Successfully processed document {document_id}")
    except Exception as e:
        logger.error(f"Background ingestion failed for {document_id}: {e}")
        doc = DB["documents"].get(document_id)
        if doc:
            doc.status = "failed"
    finally:
        if os.path.exists(file_path):
            os.remove(file_path)

@app.post("/documents")
async def upload_document(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    extract_props: bool = Form(True),
    embedding_type: str = Form("vertexai"),
    user: dict = Depends(verify_user_token)
):
    if not file.filename:
        raise HTTPException(status_code=400, detail="No filename provided")
        
    file_ext = os.path.splitext(file.filename)[1].lower()
    if file_ext not in [".pdf", ".txt", ".md", ".docx"]:
         raise HTTPException(status_code=400, detail="Only PDF, DOCX, and TXT/MD files are supported.")
         
    file_path = os.path.join(UPLOAD_DIR, f"{uuid.uuid4()}_{file.filename}")
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
        
    try:
        doc = Document(filename=file.filename, status="processing", embedding_type=embedding_type)
        DB["documents"][doc.document_id] = doc

        logger.info(f"Starting background processing for document: {doc.document_id} (Extract Props: {extract_props})")
        background_tasks.add_task(process_document_background, file_path, file.filename, doc.document_id, extract_props, embedding_type)
        
        return {"document_id": doc.document_id, "status": doc.status}
    except Exception as e:
        if os.path.exists(file_path):
            os.remove(file_path)
        logger.error(f"Upload failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/documents/{id}/status")
async def get_document_status(id: str, user: dict = Depends(verify_user_token)):
    """Check ingestion and indexing status."""
    doc = DB["documents"].get(id)
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    return {"document_id": id, "status": doc.status}

@app.get("/documents/{id}/insights")
async def get_document_insights(id: str, user: dict = Depends(verify_user_token)):
    """Return extracted screenplay intelligence."""
    insights = DB["insights"].get(id, [])
    return {"document_id": id, "insights": insights}

from fastapi.responses import StreamingResponse

@app.post("/chat")
async def chat(request: ChatRequest, user: dict = Depends(verify_user_token)):
    """Run grounded SceneIQ conversation."""
    logger.info(f"Received chat request for session: {request.session_id}")
    try:
        from .agent import process_agentic_chat_stream
        
        # Return a StreamingResponse using the generator
        return StreamingResponse(
            process_agentic_chat_stream(request.session_id, request.query, request.system_instruction),
            media_type="application/x-ndjson"
        )
    except Exception as e:
        logger.error(f"Chat execution failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/research")
async def research(request: ResearchRequest, user: dict = Depends(verify_user_token)):
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
