from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, Field
from typing import List, Optional

from ..auth import verify_user_token
from ..rag import retrieve_from_bq
from ..agent import client, MOCK_MODE
from google.genai import types

router = APIRouter(prefix="/tools/enthusiasts", tags=["Film Enthusiasts & Academics"])

class ResearchRequest(BaseModel):
    session_id: str
    query: str

class ResearchResponse(BaseModel):
    synthesis: str = Field(description="Academic synthesis regarding the query")
    citations: List[str] = Field(description="Specific scene or page citations")

class CYOARequest(BaseModel):
    session_id: str
    current_state: str
    user_choice: str

class CYOAResponse(BaseModel):
    new_scenario: str = Field(description="The outcome of the choice and new scenario")
    options: List[str] = Field(description="3 new choices for the user")
    lore_validation: bool = Field(description="Whether the choice adhered strictly to the tone and world-building rules")

class CommentaryRequest(BaseModel):
    session_id: str
    scene_query: str

class CommentaryResponse(BaseModel):
    commentary_track: str = Field(description="The simulated director's commentary track for the scene")
    production_notes: List[str] = Field(description="Key production notes or trivia generated for the scene")

@router.post("/research", response_model=ResearchResponse)
async def cinematic_deep_research(request: ResearchRequest, user: dict = Depends(verify_user_token)):
    chunks = retrieve_from_bq(request.session_id, request.query)
    context = "\n".join(chunks) if chunks else "No relevant context found."
    
    if MOCK_MODE or not client:
        return ResearchResponse(
            synthesis=f"Academic synthesis regarding '{request.query}'. The themes of betrayal are prominent in Act 2...",
            citations=["Scene 24 (Page 28)", "Scene 45 (Page 52)"]
        )

    prompt = f"Perform a deep cinematic analysis on the following script context to answer this query: '{request.query}'. Synthesize an academic-level breakdown and extract specific citations.\n\nContext:\n{context[:6000]}"
    
    response = client.models.generate_content(
        model="gemini-2.5-pro",
        contents=prompt,
        config=types.GenerateContentConfig(
            response_mime_type="application/json",
            response_schema=ResearchResponse
        )
    )
    
    try:
        return ResearchResponse.model_validate_json(response.text)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to parse structured output: {e}")

@router.post("/cyoa", response_model=CYOAResponse)
async def cyoa_simulator(request: CYOARequest, user: dict = Depends(verify_user_token)):
    lore_chunks = retrieve_from_bq(request.session_id, "world building rules and tone")
    lore_context = "\n".join(lore_chunks) if lore_chunks else "No lore context found."
    
    if MOCK_MODE or not client:
        return CYOAResponse(
            new_scenario=f"You chose to {request.user_choice}. As a result, the antagonist notices you...",
            options=["Fight", "Flee", "Hide"],
            lore_validation=True
        )

    prompt = f"You are an interactive Choose Your Own Adventure Simulator. Adhering strictly to the provided world-building lore and tone, evaluate the user's choice from the current state and generate a new scenario and 3 options.\n\nLore & Tone:\n{lore_context[:4000]}\n\nCurrent State:\n{request.current_state}\n\nUser Choice:\n{request.user_choice}"
    
    response = client.models.generate_content(
        model="gemini-2.5-flash",
        contents=prompt,
        config=types.GenerateContentConfig(
            response_mime_type="application/json",
            response_schema=CYOAResponse
        )
    )
    
    try:
        return CYOAResponse.model_validate_json(response.text)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to parse structured output: {e}")

@router.post("/commentary", response_model=CommentaryResponse)
async def directors_commentary(request: CommentaryRequest, user: dict = Depends(verify_user_token)):
    scene_chunks = retrieve_from_bq(request.session_id, request.scene_query)
    scene_context = "\n".join(scene_chunks) if scene_chunks else "No scene context found."
    
    if MOCK_MODE or not client:
        return CommentaryResponse(
            commentary_track="Notice how the lighting shifts here? We actually ran out of daylight during this shoot...",
            production_notes=["Shot on location", "Lighting issues resolved in post"]
        )

    prompt = f"Act as the director of the film for the following scene. Generate an educational behind-the-scenes 'Director's Commentary' track discussing script changes, lore, or supposed production challenges based on the scene content.\n\nScene Context:\n{scene_context[:6000]}"
    
    response = client.models.generate_content(
        model="gemini-2.5-pro",
        contents=prompt,
        config=types.GenerateContentConfig(
            response_mime_type="application/json",
            response_schema=CommentaryResponse
        )
    )
    
    try:
        return CommentaryResponse.model_validate_json(response.text)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to parse structured output: {e}")
