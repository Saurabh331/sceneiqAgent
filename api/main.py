from fastapi import FastAPI, UploadFile, File, HTTPException
from pydantic import BaseModel
import shutil
import os
import uuid

from .ingestion import parse_document, chunk_text
from .rag import store_chunks
from .agent import process_agentic_chat

app = FastAPI(title="SceneIQ API")

# Ensure upload directory exists
UPLOAD_DIR = "/tmp/sceneiq_uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)

class ChatRequest(BaseModel):
    session_id: str
    query: str

class ChatResponse(BaseModel):
    response: str
    tool_log: list[str] = []

@app.post("/upload")
async def upload_document(file: UploadFile = File(...)):
    if not file.filename:
        raise HTTPException(status_code=400, detail="No filename provided")
        
    file_ext = os.path.splitext(file.filename)[1].lower()
    if file_ext not in [".pdf", ".txt", ".md"]:
         raise HTTPException(status_code=400, detail="Only PDF and TXT/MD files are supported.")
         
    # Save the file temporarily
    file_path = os.path.join(UPLOAD_DIR, file.filename)
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
        
    try:
        # Parse and chunk
        text = parse_document(file_path, file.filename)
        chunks = chunk_text(text)
        
        # Generate session ID for this document
        session_id = str(uuid.uuid4())
        
        # Store chunks for RAG
        store_chunks(session_id, chunks)
        
        return {
            "message": "File processed successfully", 
            "session_id": session_id,
            "chunks_count": len(chunks)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        # Clean up
        if os.path.exists(file_path):
            os.remove(file_path)

@app.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    try:
        result = process_agentic_chat(request.session_id, request.query)
        return ChatResponse(response=result["response"], tool_log=result["tool_log"])
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/health")
async def health_check():
    return {"status": "ok"}
