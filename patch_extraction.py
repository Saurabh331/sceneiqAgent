import re

# --- Patch models.py ---
with open('api/models.py', 'r', encoding='utf-8') as f:
    models_content = f.read()

if "scenes: List[str] = []" not in models_content:
    models_content = models_content.replace(
        'embedding_type: str = "vertexai"',
        'embedding_type: str = "vertexai"\n    scenes: List[str] = []'
    )
    with open('api/models.py', 'w', encoding='utf-8') as f:
        f.write(models_content)
    print("Patched models.py")


# --- Patch ingestion.py ---
with open('api/ingestion.py', 'r', encoding='utf-8') as f:
    ingestion_content = f.read()

# Update parse_and_chunk_script
old_parse = '''    scene_texts = []
    for i in range(len(scene_splits)):
        start = scene_splits[i].start()
        end = scene_splits[i+1].start() if i + 1 < len(scene_splits) else len(full_text)
        scene_texts.append((i, full_text[start:end]))
        
    documents = []'''

new_parse = '''    scene_texts = []
    scene_headings = []
    for i in range(len(scene_splits)):
        start = scene_splits[i].start()
        end = scene_splits[i+1].start() if i + 1 < len(scene_splits) else len(full_text)
        scene_text = full_text[start:end]
        scene_texts.append((i, scene_text))
        
        # Extract the heading (first line)
        heading = scene_text.split('\\n')[0].strip()
        if heading:
            scene_headings.append(heading)
            
    documents = []'''

ingestion_content = ingestion_content.replace(old_parse, new_parse)

old_parse_return = '''    return documents'''
new_parse_return = '''    return documents, scene_headings'''

# Only replace the last occurrence which is in parse_and_chunk_script
last_idx = ingestion_content.rfind(old_parse_return)
if last_idx != -1:
    ingestion_content = ingestion_content[:last_idx] + new_parse_return + ingestion_content[last_idx + len(old_parse_return):]

# Update load_and_split_document
old_load = '''    full_text = "\\n".join([doc.page_content for doc in raw_documents])
    
    chunks = parse_and_chunk_script(full_text, extract_props)
    
    return chunks'''

new_load = '''    full_text = "\\n".join([doc.page_content for doc in raw_documents])
    
    chunks, scenes = parse_and_chunk_script(full_text, extract_props)
    
    return chunks, scenes'''

ingestion_content = ingestion_content.replace(old_load, new_load)

with open('api/ingestion.py', 'w', encoding='utf-8') as f:
    f.write(ingestion_content)
print("Patched ingestion.py")


# --- Patch main.py ---
with open('api/main.py', 'r', encoding='utf-8') as f:
    main_content = f.read()

old_main_process = '''def process_document_background(file_path: str, filename: str, document_id: str, extract_props: bool, embedding_type: str):
    try:
        chunks = load_and_split_document(file_path, filename, extract_props)
        ingest_chunks_to_bq(chunks, document_id, embedding_type)
        
        doc = DB["documents"].get(document_id)
        if doc:
            doc.status = "indexed"'''

new_main_process = '''def process_document_background(file_path: str, filename: str, document_id: str, extract_props: bool, embedding_type: str):
    try:
        chunks, scenes = load_and_split_document(file_path, filename, extract_props)
        ingest_chunks_to_bq(chunks, document_id, embedding_type)
        
        doc = DB["documents"].get(document_id)
        if doc:
            doc.status = "indexed"
            doc.scenes = scenes'''

main_content = main_content.replace(old_main_process, new_main_process)

with open('api/main.py', 'w', encoding='utf-8') as f:
    f.write(main_content)
print("Patched main.py")


# --- Patch producers.py ---
with open('api/tools/producers.py', 'r', encoding='utf-8') as f:
    producers_content = f.read()

old_get_scenes = '''@router.get("/scenes", response_model=ScenesResponse)
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
        )
        # Parse JSON array safely
        import json
        text = response.text
        start = text.find('[')
        end = text.rfind(']') + 1
        if start != -1 and end != 0:
            scenes = json.loads(text[start:end])
            return ScenesResponse(scenes=scenes)
    except Exception as e:
        print(f"Error extracting scenes: {e}")
        
    return ScenesResponse(scenes=[])'''

new_get_scenes = '''@router.get("/scenes", response_model=ScenesResponse)
async def get_scenes(session_id: str, user: dict = Depends(verify_user_token)):
    from ..models import DB
    doc = DB["documents"].get(session_id)
    if doc and doc.scenes:
        return ScenesResponse(scenes=doc.scenes)
    
    if MOCK_MODE or not client:
        return ScenesResponse(scenes=["Opening Scene", "Act 1", "The Climax", "Ending"])
        
    return ScenesResponse(scenes=[])'''

producers_content = producers_content.replace(old_get_scenes, new_get_scenes)

with open('api/tools/producers.py', 'w', encoding='utf-8') as f:
    f.write(producers_content)
print("Patched producers.py")
