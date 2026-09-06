from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, Field
from typing import List, Optional, Dict

from ..auth import verify_user_token
from ..rag import retrieve_from_bq
from ..agent import parallel_search, client, MOCK_MODE
from google.genai import types

router = APIRouter(prefix="/tools/writers", tags=["Writers & Script Editors"])

class ScriptDoctorRequest(BaseModel):
    session_id: str
    framework: str = "Hero's Journey"

class ScriptDoctorResponse(BaseModel):
    pacing_analysis: str = Field(description="Analysis of the pacing based on the framework")
    plot_holes: List[str] = Field(description="Identified plot holes or logic gaps")
    structural_beats: dict[str, str] = Field(description="Mapping of framework beats to specific scenes/pages")

class DialogPartnerRequest(BaseModel):
    session_id: str
    character_name: str
    user_message: str

class DialogPartnerResponse(BaseModel):
    character_response: str = Field(description="The in-character response to the user's message")
    subtext_hints: List[str] = Field(description="Hints about what the character is actually feeling or hiding")

class LocalizationRequest(BaseModel):
    session_id: str
    scene_query: str
    target_language: str
    regional_context: str

class LocalizationResponse(BaseModel):
    translated_text: str = Field(description="The translated scene text maintaining tone and regional context")
    translation_notes: List[str] = Field(description="Notes explaining slang or subtext adjustments")

@router.post("/script_doctor", response_model=ScriptDoctorResponse)
async def dynamic_script_doctor(request: ScriptDoctorRequest, user: dict = Depends(verify_user_token)):
    framework_context = parallel_search(f"What are the key structural beats of {request.framework}?")
    chunks = retrieve_from_bq(request.session_id, "entire script summary and main plot points")
    script_context = "\n".join(chunks) if chunks else "No script context found."
    
    if MOCK_MODE or not client:
        return ScriptDoctorResponse(
            pacing_analysis=f"Analysis based on {request.framework}: Act 2 feels slightly rushed.",
            plot_holes=["Character motivation in Scene 45 is unclear."],
            structural_beats={"Inciting Incident": "Scene 10", "Midpoint": "Scene 50", "Climax": "Scene 90"}
        )

    prompt = f"You are an expert Script Doctor. Compare the following script's structural beats against the {request.framework} framework.\n\nFramework Details:\n{framework_context}\n\nScript Context:\n{script_context[:8000]}"
    
    response = client.models.generate_content(
        model="gemini-2.5-pro",
        contents=prompt,
        config=types.GenerateContentConfig(
            response_mime_type="application/json",
            response_schema=ScriptDoctorResponse
        )
    )
    
    try:
        return ScriptDoctorResponse.model_validate_json(response.text)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to parse structured output: {e}")

@router.post("/dialog_partner", response_model=DialogPartnerResponse)
async def bespoke_dialog_partner(request: DialogPartnerRequest, user: dict = Depends(verify_user_token)):
    character_context_chunks = retrieve_from_bq(request.session_id, request.character_name)
    character_context = "\n".join(character_context_chunks) if character_context_chunks else ""
    
    if MOCK_MODE or not client:
        return DialogPartnerResponse(
            character_response=f"(As {request.character_name}) I wouldn't say that... it doesn't sound like me.",
            subtext_hints=["Character is feeling defensive.", "Hiding a secret from Scene 12."]
        )

    prompt = f"You are roleplaying as {request.character_name}. Based on the following character context, respond to the writer's message in character. Also provide subtext hints about what the character is actually feeling.\n\nCharacter Context:\n{character_context[:4000]}\n\nWriter's Message:\n{request.user_message}"
    
    response = client.models.generate_content(
        model="gemini-2.5-flash",
        contents=prompt,
        config=types.GenerateContentConfig(
            response_mime_type="application/json",
            response_schema=DialogPartnerResponse
        )
    )
    
    try:
        return DialogPartnerResponse.model_validate_json(response.text)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to parse structured output: {e}")


@router.post("/localization", response_model=LocalizationResponse)
async def localization_engine(request: LocalizationRequest, user: dict = Depends(verify_user_token)):
    scene_chunks = retrieve_from_bq(request.session_id, request.scene_query)
    scene_context = "\n".join(scene_chunks) if scene_chunks else "No scene context found."
    
    if MOCK_MODE or not client:
        return LocalizationResponse(
            translated_text=f"[Translated to {request.target_language} with {request.regional_context} context]",
            translation_notes=["Adjusted colloquial slang in line 4 to match regional dialect."]
        )

    prompt = f"You are an expert film localization engine. Translate the following scene text into {request.target_language}, specifically tailoring it to the regional context of '{request.regional_context}'. Maintain the emotional tone and adjust slang appropriately.\n\nScene Text:\n{scene_context[:6000]}"
    
    response = client.models.generate_content(
        model="gemini-2.5-pro",
        contents=prompt,
        config=types.GenerateContentConfig(
            response_mime_type="application/json",
            response_schema=LocalizationResponse
        )
    )
    
    try:
        return LocalizationResponse.model_validate_json(response.text)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to parse structured output: {e}")
