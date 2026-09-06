from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime
import uuid

class Document(BaseModel):
    document_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    filename: str
    checksum: Optional[str] = None
    upload_time: datetime = Field(default_factory=datetime.utcnow)
    status: str = "processing"
    embedding_type: str = "vertexai"

class Chunk(BaseModel):
    chunk_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    document_id: str
    page: Optional[int] = None
    scene_id: Optional[str] = None
    text: str
    # embedding omitted in API model to save bandwidth, it lives in BigQuery

class Scene(BaseModel):
    scene_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    heading: str
    location: Optional[str] = None
    time_of_day: Optional[str] = None
    characters: List[str] = []
    page_range: Optional[str] = None

class Character(BaseModel):
    character_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    canonical_name: str
    aliases: List[str] = []
    appearances: int = 0

class Insight(BaseModel):
    type: str
    severity: str
    evidence_chunk_ids: List[str]
    explanation: str
    confidence: float

class ExternalSource(BaseModel):
    query: str
    title: str
    url: str
    retrieved_at: datetime = Field(default_factory=datetime.utcnow)
    source_excerpt: str

# Mock Database
DB = {
    "documents": {},
    "insights": {}
}
