import os
from typing import List
from langchain_community.document_loaders import PyPDFLoader, TextLoader, Docx2txtLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter

def load_and_split_document(file_path: str, filename: str) -> List:
    """
    Loads a document (PDF, TXT, DOCX) and splits it into chunks using LangChain.
    Returns a list of LangChain Document objects.
    """
    ext = os.path.splitext(filename)[1].lower()
    
    if ext == '.pdf':
        loader = PyPDFLoader(file_path)
    elif ext in ['.txt', '.md']:
        loader = TextLoader(file_path)
    elif ext == '.docx':
        loader = Docx2txtLoader(file_path)
    else:
        raise ValueError(f"Unsupported file format: {ext}")
        
    documents = loader.load()
    
    # Split the document into chunks
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=1000,
        chunk_overlap=200,
        length_function=len,
    )
    chunks = text_splitter.split_documents(documents)
    
    # Basic mock metadata extraction (Scene detection)
    import re
    scene_pattern = re.compile(r'^(INT\.|EXT\.)', re.IGNORECASE)
    current_scene_id = "mock-scene-id-000"
    
    for i, chunk in enumerate(chunks):
        if scene_pattern.search(chunk.page_content):
            current_scene_id = f"mock-scene-id-{i:03d}"
        
        chunk.metadata["scene_id"] = current_scene_id
        chunk.metadata["chunk_index"] = i
    
    return chunks
