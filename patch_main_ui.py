import re

# --- Patch main.py ---
with open('api/main.py', 'r', encoding='utf-8') as f:
    main_content = f.read()

# Update process_document_background
old_worker = '''def process_document_background(file_path: str, filename: str, document_id: str, extract_props: bool):
    try:
        chunks = load_and_split_document(file_path, filename, extract_props)
        ingest_chunks_to_bq(chunks, document_id)'''

new_worker = '''def process_document_background(file_path: str, filename: str, document_id: str, extract_props: bool, embedding_type: str):
    try:
        chunks = load_and_split_document(file_path, filename, extract_props)
        ingest_chunks_to_bq(chunks, document_id, embedding_type)'''

main_content = main_content.replace(old_worker, new_worker)

# Update upload_document
old_upload = '''@app.post("/documents")
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

        background_tasks.add_task(process_document_background, file_path, file.filename, doc.document_id, extract_props)'''

new_upload = '''@app.post("/documents")
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
         
    file_path = os.path.join(UPLOAD_DIR, file.filename)
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
        
    try:
        doc = Document(filename=file.filename, status="processing", embedding_type=embedding_type)
        DB["documents"][doc.document_id] = doc

        background_tasks.add_task(process_document_background, file_path, file.filename, doc.document_id, extract_props, embedding_type)'''

main_content = main_content.replace(old_upload, new_upload)

with open('api/main.py', 'w', encoding='utf-8') as f:
    f.write(main_content)


# --- Patch ui.py ---
with open('app/ui.py', 'r', encoding='utf-8') as f:
    ui_content = f.read()

old_ui = '''        extract_props = st.checkbox("Extract Atomic Propositions (Slower, High Cost)", value=True, help="Disable this for extremely large scripts to speed up ingestion.")
        if uploaded_file is not None:
            if st.button("Process Document"):
                with st.spinner("Uploading and processing document..."):
                    try:
                        headers = {"Authorization": f"Bearer {token_data['token']['id_token']}"}
                        files = {"file": (uploaded_file.name, uploaded_file.getvalue(), uploaded_file.type)}
                        data = {"extract_props": "true" if extract_props else "false"}
                        response = requests.post(f"{API_BASE_URL}/documents", files=files, data=data, headers=headers)'''

new_ui = '''        extract_props = st.checkbox("Extract Atomic Propositions (Slower, High Cost)", value=True, help="Disable this for extremely large scripts to speed up ingestion.")
        model_choice = st.radio("Select Embedding Model", ["Vertex AI (Small Documents)", "Hugging Face (Large Documents)"])
        embedding_type = "vertexai" if "Vertex AI" in model_choice else "huggingface"
        
        if uploaded_file is not None:
            if st.button("Process Document"):
                with st.spinner("Uploading and processing document..."):
                    try:
                        headers = {"Authorization": f"Bearer {token_data['token']['id_token']}"}
                        files = {"file": (uploaded_file.name, uploaded_file.getvalue(), uploaded_file.type)}
                        data = {
                            "extract_props": "true" if extract_props else "false",
                            "embedding_type": embedding_type
                        }
                        response = requests.post(f"{API_BASE_URL}/documents", files=files, data=data, headers=headers)'''

ui_content = ui_content.replace(old_ui, new_ui)

with open('app/ui.py', 'w', encoding='utf-8') as f:
    f.write(ui_content)

print("Patched main.py and ui.py")
