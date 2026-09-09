import re
import os

# --- Patch producers.py ---
with open('api/tools/producers.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Add FileResponse import
if "from fastapi.responses import FileResponse" not in content:
    content = content.replace(
        "from fastapi import APIRouter, HTTPException, Depends, BackgroundTasks",
        "from fastapi import APIRouter, HTTPException, Depends, BackgroundTasks\nfrom fastapi.responses import FileResponse"
    )

old_pdf_output = '''    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as temp_pdf:
        pdf.output(temp_pdf.name)
        pdf_path = temp_pdf.name
        
    bucket_name = os.getenv("GCS_BUCKET", "sceneiq-storyboards")
    url = upload_to_gcs(bucket_name, f"storyboard_{task_id}.pdf", pdf_path)
    if url is None:
        url = f"mock-url-for-{task_id}.pdf"
    os.remove(pdf_path)'''

new_pdf_output = '''    downloads_dir = os.path.join(tempfile.gettempdir(), "sceneiq_downloads")
    os.makedirs(downloads_dir, exist_ok=True)
    pdf_path = os.path.join(downloads_dir, f"storyboard_{task_id}.pdf")
    pdf.output(pdf_path)
        
    bucket_name = os.getenv("GCS_BUCKET", "sceneiq-storyboards")
    url = upload_to_gcs(bucket_name, f"storyboard_{task_id}.pdf", pdf_path)
    if url is None:
        url = f"/tools/producers/download/{task_id}"
    else:
        # If successfully uploaded to GCS, we can remove the local file
        os.remove(pdf_path)'''

content = content.replace(old_pdf_output, new_pdf_output)

download_endpoint = '''
@router.get("/download/{task_id}")
async def download_storyboard(task_id: str):
    downloads_dir = os.path.join(tempfile.gettempdir(), "sceneiq_downloads")
    local_pdf_path = os.path.join(downloads_dir, f"storyboard_{task_id}.pdf")
    if os.path.exists(local_pdf_path):
        return FileResponse(local_pdf_path, media_type="application/pdf", filename=f"storyboard_{task_id}.pdf")
    raise HTTPException(status_code=404, detail="File not found locally.")
'''

if "@router.get(\"/download/{task_id}\")" not in content:
    content = content + download_endpoint

with open('api/tools/producers.py', 'w', encoding='utf-8') as f:
    f.write(content)


# --- Patch ui.py ---
with open('app/ui.py', 'r', encoding='utf-8') as f:
    ui_content = f.read()

old_ui_url = '''                                    url = status_data.get("url")
                                    st.success("Generation Complete!")
                                    st.markdown(f"[**Download Storyboard PDF here**]({url})")'''

new_ui_url = '''                                    url = status_data.get("url")
                                    if url and url.startswith("/"):
                                        url = f"{API_BASE_URL}{url}"
                                    st.success("Generation Complete!")
                                    st.markdown(f"[**Download Storyboard PDF here**]({url})")'''

ui_content = ui_content.replace(old_ui_url, new_ui_url)

with open('app/ui.py', 'w', encoding='utf-8') as f:
    f.write(ui_content)

print("Patch applied.")
