import re

# --- Patch ingestion.py ---
with open('api/ingestion.py', 'r', encoding='utf-8') as f:
    ingestion_content = f.read()

# Modify process_scene signature and logic
ingestion_content = ingestion_content.replace(
    'def process_scene(i: int, scene_text: str, global_context: str) -> List[Document]:',
    'def process_scene(i: int, scene_text: str, global_context: str, extract_props: bool = True) -> List[Document]:'
)
ingestion_content = ingestion_content.replace(
    '    propositions = extract_propositions(scene_text)',
    '    propositions = extract_propositions(scene_text) if extract_props else []'
)

# Modify parse_and_chunk_script signature and logic
ingestion_content = ingestion_content.replace(
    'def parse_and_chunk_script(full_text: str) -> List[Document]:',
    'def parse_and_chunk_script(full_text: str, extract_props: bool = True) -> List[Document]:'
)
ingestion_content = ingestion_content.replace(
    'executor.submit(process_scene, i, text, global_context): i',
    'executor.submit(process_scene, i, text, global_context, extract_props): i'
)

# Modify load_and_split_document signature and logic
ingestion_content = ingestion_content.replace(
    'def load_and_split_document(file_path: str, filename: str) -> List[Document]:',
    'def load_and_split_document(file_path: str, filename: str, extract_props: bool = True) -> List[Document]:'
)
ingestion_content = ingestion_content.replace(
    'chunks = parse_and_chunk_script(full_text)',
    'chunks = parse_and_chunk_script(full_text, extract_props)'
)

with open('api/ingestion.py', 'w', encoding='utf-8') as f:
    f.write(ingestion_content)


# --- Patch main.py ---
with open('api/main.py', 'r', encoding='utf-8') as f:
    main_content = f.read()

main_content = main_content.replace('from fastapi import FastAPI, UploadFile, File, HTTPException', 'from fastapi import FastAPI, UploadFile, File, HTTPException, BackgroundTasks, Form')

background_worker_code = '''
def process_document_background(file_path: str, filename: str, document_id: str, extract_props: bool):
    try:
        chunks = load_and_split_document(file_path, filename, extract_props)
        ingest_chunks_to_bq(chunks, document_id)
        
        doc = DB["documents"].get(document_id)
        if doc:
            doc.status = "indexed"
            
        mock_insight = Insight(
            type="Complexity", severity="High", evidence_chunk_ids=["mock-chunk-1"],
            explanation="Multiple night shoots detected.", confidence=0.85
        )
        DB["insights"][document_id] = [mock_insight]
    except Exception as e:
        print(f"Background ingestion failed: {e}")
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
    user: dict = Depends(verify_user_token)
):
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

        background_tasks.add_task(process_document_background, file_path, file.filename, doc.document_id, extract_props)
        
        return {"document_id": doc.document_id, "status": doc.status}
    except Exception as e:
        if os.path.exists(file_path):
            os.remove(file_path)
        raise HTTPException(status_code=500, detail=str(e))
'''

# Find the original upload_document function and replace it
import re
main_content = re.sub(r'@app\.post\("/documents"\).*?def upload_document.*?return {"document_id".*?os\.remove\(file_path\)', background_worker_code, main_content, flags=re.DOTALL)

with open('api/main.py', 'w', encoding='utf-8') as f:
    f.write(main_content)


# --- Patch ui.py ---
with open('app/ui.py', 'r', encoding='utf-8') as f:
    ui_content = f.read()

new_ui_upload_code = '''        extract_props = st.checkbox("Extract Atomic Propositions (Slower, High Cost)", value=True, help="Disable this for extremely large scripts to speed up ingestion.")
        if uploaded_file is not None:
            if st.button("Process Document"):
                with st.spinner("Uploading and processing document..."):
                    try:
                        headers = {"Authorization": f"Bearer {token_data['token']['id_token']}"}
                        files = {"file": (uploaded_file.name, uploaded_file.getvalue(), uploaded_file.type)}
                        data = {"extract_props": "true" if extract_props else "false"}
                        response = requests.post(f"{API_BASE_URL}/documents", files=files, data=data, headers=headers)
                        
                        if response.status_code == 200:
                            resp_data = response.json()
                            st.session_state.session_id = resp_data.get("document_id")
                            
                            progress_text = st.empty()
                            while True:
                                status_res = requests.get(f"{API_BASE_URL}/documents/{st.session_state.session_id}/status", headers=headers)
                                if status_res.status_code == 200:
                                    status_data = status_res.json()
                                    if status_data.get("status") == "indexed":
                                        progress_text.success("Document processed and indexed successfully!")
                                        st.session_state.messages = []
                                        break
                                    elif status_data.get("status") == "failed":
                                        progress_text.error("Document ingestion failed.")
                                        break
                                    else:
                                        progress_text.info("Processing in background... please wait.")
                                else:
                                    progress_text.warning("Checking status...")
                                time.sleep(3)
                        else:
                            st.error(f"Error: {response.text}")
                    except Exception as e:
                        st.error(f"Failed to connect to API. Is it running? Error: {e}")'''

ui_content = re.sub(r'        if uploaded_file is not None:.*?st\.error\(f"Failed to connect to API.*?Error: \{e\}"\)', new_ui_upload_code, ui_content, flags=re.DOTALL)

with open('app/ui.py', 'w', encoding='utf-8') as f:
    f.write(ui_content)

print("Patching complete.")
