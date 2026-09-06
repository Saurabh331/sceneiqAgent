import re

with open('api/tools/producers.py', 'r', encoding='utf-8') as f:
    content = f.read()

imports = '''from fastapi import APIRouter, HTTPException, Depends, BackgroundTasks
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
import json
import base64
import uuid
import tempfile
import os
from fpdf import FPDF
from google.cloud import storage
from ..auth import get_google_credentials'''

content = re.sub(r'from fastapi import.*', imports, content, flags=re.DOTALL | re.MULTILINE)
content = content.replace('import base64\n', '')
content = content.replace('import json\n', '')
content = content.replace('from pydantic import BaseModel, Field\n', '')
content = content.replace('from typing import List, Optional\n', '')
content = content.replace('from ..auth import verify_user_token\n', 'from ..auth import verify_user_token, get_google_credentials\n')

new_classes_and_funcs = '''

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

class BatchStoryboardRequest(BaseModel):
    session_id: str
    scenes: List[str]

class ScenesResponse(BaseModel):
    scenes: List[str]

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
            if MOCK_MODE:
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
        
    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as temp_pdf:
        pdf.output(temp_pdf.name)
        pdf_path = temp_pdf.name
        
    bucket_name = os.getenv("GCS_BUCKET", "sceneiq-storyboards")
    url = upload_to_gcs(bucket_name, f"storyboard_{task_id}.pdf", pdf_path)
    if url is None:
        url = f"mock-url-for-{task_id}.pdf"
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

'''

content = content.replace('router = APIRouter(prefix="/tools/producers", tags=["Filmmakers & Producers"])', 'router = APIRouter(prefix="/tools/producers", tags=["Filmmakers & Producers"])\n' + new_classes_and_funcs)

with open('api/tools/producers.py', 'w', encoding='utf-8') as f:
    f.write(content)
print("Successfully patched producers.py")
