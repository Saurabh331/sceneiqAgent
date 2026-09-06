from fastapi import APIRouter, HTTPException, Depends, BackgroundTasks
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
import json
import base64
import uuid
import tempfile
import os
from fpdf import FPDF
from google.cloud import storage

from ..auth import verify_user_token, get_google_credentials
from ..rag import retrieve_from_bq
from ..agent import client, MOCK_MODE
from google.genai import types

router = APIRouter(prefix="/tools/producers", tags=["Filmmakers & Producers"])

storyboard_tasks: Dict[str, Any] = {}

def upload_to_gcs(bucket_name, blob_name, file_path):
    if MOCK_MODE:
        return f"https://storage.googleapis.com/{bucket_name}/{blob_name}"
    try:
        credentials = get_google_credentials()
        storage_client = storage.Client(credentials=credentials) if credentials else storage.Client()
        bucket = storage_client.bucket(bucket_name)
        blob = bucket.blob(blob_name)
        blob.upload_from_filename(file_path)
        return blob.public_url
    except Exception as e:
        print(f"GCS upload failed: {e}")
        return None

class StoryboardRequest(BaseModel):
    session_id: str
    scene_query: str

class StoryboardResponse(BaseModel):
    scene_description: str
    image_prompt: str
    image_base64: Optional[str] = None

class BatchStoryboardRequest(BaseModel):
    session_id: str
    scenes: List[str]

class ScenesResponse(BaseModel):
    scenes: List[str]

class BreakdownRequest(BaseModel):
    session_id: str
    scene_query: str

class BreakdownResponse(BaseModel):
    scenes: List[str] = Field(description="List of scene headings")
    characters: List[str] = Field(description="List of characters appearing in the scenes")
    props: List[str] = Field(description="List of physical props required")
    locations: List[str] = Field(description="List of physical locations")

class CastAnalysisRequest(BaseModel):
    session_id: str
    character_name: str
    video_uri: str 

class CastAnalysisResponse(BaseModel):
    character_profile: str = Field(description="The extracted character profile from the script")
    performance_analysis: str = Field(description="Critique of the video performance")
    match_score: float = Field(description="A score from 0.0 to 1.0 indicating fit")

def generate_storyboards_background(task_id: str, request: BatchStoryboardRequest):
    storyboard_tasks[task_id] = {"status": "processing", "progress": 0, "total": len(request.scenes), "url": None}
    
    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()
    pdf.set_font("Arial", size=12)
    
    pdf.cell(200, 10, txt="Storyboards", ln=True, align='C')
    
    for i, scene in enumerate(request.scenes):
        chunks = retrieve_from_bq(request.session_id, scene)
        scene_context = "\\n".join(chunks) if chunks else "No context found."
        
        prompt_instruction = f"Based on the following scene context, write a highly detailed, cinematic image generation prompt for a storyboard frame representing '{scene}'. Just output the prompt text.\\n\\nContext:\\n{scene_context[:3000]}"
        
        try:
            if MOCK_MODE or not client:
                image_prompt = f"Mock prompt for {scene}"
                temp_img_path = None
            else:
                response = client.models.generate_content(model="gemini-2.5-flash", contents=prompt_instruction)
                image_prompt = response.text.strip()
                
                image_response = client.models.generate_images(
                    model='imagen-3.0-generate-001',
                    prompt=image_prompt,
                    config=types.GenerateImagesConfig(number_of_images=1, aspect_ratio="16:9")
                )
                image_bytes = image_response.generated_images[0].image.image_bytes
                
                with tempfile.NamedTemporaryFile(delete=False, suffix=".png") as temp_img:
                    temp_img.write(image_bytes)
                    temp_img_path = temp_img.name
                
            pdf.cell(200, 10, txt=f"Scene: {scene}", ln=True)
            pdf.multi_cell(0, 10, txt=f"Prompt: {image_prompt}")
            if temp_img_path:
                pdf.image(temp_img_path, w=150)
                pdf.ln(10)
                os.remove(temp_img_path)
            else:
                pdf.cell(200, 10, txt="(Mock Image)", ln=True)
                pdf.ln(10)
        except Exception as e:
            print(f"Failed to generate for scene {scene}: {e}")
            pdf.cell(200, 10, txt=f"Scene: {scene} (Failed to generate)", ln=True)
            
        storyboard_tasks[task_id]["progress"] = i + 1
        
    downloads_dir = os.path.join(tempfile.gettempdir(), "sceneiq_downloads")
    os.makedirs(downloads_dir, exist_ok=True)
    pdf_path = os.path.join(downloads_dir, f"storyboard_{task_id}.pdf")
    pdf.output(pdf_path)
        
    bucket_name = os.getenv("GCS_BUCKET", "sceneiq-storyboards")
    url = upload_to_gcs(bucket_name, f"storyboard_{task_id}.pdf", pdf_path)
    if url is None:
        url = f"/tools/producers/download/{task_id}"
    else:
        # If successfully uploaded to GCS, we can remove the local file
        os.remove(pdf_path)
    
    storyboard_tasks[task_id]["status"] = "completed"
    storyboard_tasks[task_id]["url"] = url

@router.get("/scenes", response_model=ScenesResponse)
async def get_scenes(session_id: str, user: dict = Depends(verify_user_token)):
    if MOCK_MODE or not client:
        return ScenesResponse(scenes=["Opening Scene", "Act 1", "The Climax", "Ending"])
        
    chunks = retrieve_from_bq(session_id, "list all scene headings", top_k=10)
    context = "\\n".join(chunks) if chunks else ""
    
    prompt = f"Extract a list of distinct scene headings from the following text. Just return a JSON array of strings, nothing else.\\n\\n{context[:8000]}"
    try:
        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=prompt,
            config=types.GenerateContentConfig(response_mime_type="application/json")
        )
        data = json.loads(response.text)
        if isinstance(data, list):
            return ScenesResponse(scenes=data)
        elif isinstance(data, dict) and "scenes" in data:
            return ScenesResponse(scenes=data["scenes"])
    except:
        pass
    return ScenesResponse(scenes=["Opening Scene", "Act 1"])

@router.post("/storyboard/batch")
async def batch_generate_storyboards(request: BatchStoryboardRequest, background_tasks: BackgroundTasks, user: dict = Depends(verify_user_token)):
    task_id = str(uuid.uuid4())
    background_tasks.add_task(generate_storyboards_background, task_id, request)
    return {"task_id": task_id, "status": "processing"}

@router.get("/storyboard/status/{task_id}")
async def get_storyboard_status(task_id: str):
    if task_id not in storyboard_tasks:
        raise HTTPException(status_code=404, detail="Task not found")
    return storyboard_tasks[task_id]

@router.post("/storyboard", response_model=StoryboardResponse)
async def generate_storyboards(request: StoryboardRequest, user: dict = Depends(verify_user_token)):
    chunks = retrieve_from_bq(request.session_id, request.scene_query)
    scene_context = "\\n".join(chunks) if chunks else "No context found."
    
    if MOCK_MODE or not client:
        return StoryboardResponse(
            scene_description=scene_context[:200] + "...",
            image_prompt=f"A cinematic storyboard shot inspired by: {request.scene_query}",
            image_base64=None
        )

    prompt_instruction = f"Based on the following scene context, write a highly detailed, cinematic image generation prompt for a storyboard frame representing '{request.scene_query}'. Just output the prompt text.\\n\\nContext:\\n{scene_context[:3000]}"
    
    response = client.models.generate_content(
        model="gemini-2.5-flash",
        contents=prompt_instruction
    )
    image_prompt = response.text.strip()

    try:
        image_response = client.models.generate_images(
            model='imagen-3.0-generate-001',
            prompt=image_prompt,
            config=types.GenerateImagesConfig(
                number_of_images=1,
                aspect_ratio="16:9"
            )
        )
        img_base64 = base64.b64encode(image_response.generated_images[0].image.image_bytes).decode('utf-8')
    except Exception as e:
        print(f"Image generation failed: {e}")
        img_base64 = None

    return StoryboardResponse(
        scene_description=scene_context[:200] + "...",
        image_prompt=image_prompt,
        image_base64=img_base64
    )

@router.post("/breakdown", response_model=BreakdownResponse)
async def automated_breakdown(request: BreakdownRequest, user: dict = Depends(verify_user_token)):
    chunks = retrieve_from_bq(request.session_id, request.scene_query)
    scene_context = "\\n".join(chunks) if chunks else "No context found."
    
    if MOCK_MODE or not client:
        return BreakdownResponse(
            scenes=[request.scene_query], characters=["Main Character"], props=["Gun"], locations=["Office"]
        )

    prompt = f"Analyze the following screenplay chunks and perform a production breakdown. Extract the scenes, characters, props, and locations.\\n\\nChunks:\\n{scene_context[:8000]}"
    
    response = client.models.generate_content(
        model="gemini-2.5-flash",
        contents=prompt,
        config=types.GenerateContentConfig(
            response_mime_type="application/json",
            response_schema=BreakdownResponse
        )
    )
    
    try:
        return BreakdownResponse.model_validate_json(response.text)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to parse structured output: {e}")

@router.post("/cast_analysis", response_model=CastAnalysisResponse)
async def interactive_casting(request: CastAnalysisRequest, user: dict = Depends(verify_user_token)):
    chunks = retrieve_from_bq(request.session_id, request.character_name)
    character_context = "\\n".join(chunks) if chunks else "No character context found."
    
    if MOCK_MODE or not client:
        return CastAnalysisResponse(
            character_profile=character_context[:100], performance_analysis="Mock analysis.", match_score=0.89
        )
        
    prompt = f"You are a casting director. Analyze the provided audition video. Compare the actor's performance, tone, and delivery against the following character profile/context extracted from the script. Provide a structured analysis and a fit score.\\n\\nCharacter Context:\\n{character_context[:4000]}"
    video_part = types.Part.from_uri(file_uri=request.video_uri, mime_type="video/mp4")
    
    response = client.models.generate_content(
        model="gemini-2.5-pro",
        contents=[video_part, prompt],
        config=types.GenerateContentConfig(
            response_mime_type="application/json",
            response_schema=CastAnalysisResponse
        )
    )
    
    try:
        return CastAnalysisResponse.model_validate_json(response.text)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to parse structured output: {e}")

@router.get("/download/{task_id}")
async def download_storyboard(task_id: str):
    downloads_dir = os.path.join(tempfile.gettempdir(), "sceneiq_downloads")
    local_pdf_path = os.path.join(downloads_dir, f"storyboard_{task_id}.pdf")
    if os.path.exists(local_pdf_path):
        return FileResponse(local_pdf_path, media_type="application/pdf", filename=f"storyboard_{task_id}.pdf")
    raise HTTPException(status_code=404, detail="File not found locally.")
