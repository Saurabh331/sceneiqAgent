import os
import re
import time
from typing import List
from concurrent.futures import ThreadPoolExecutor, as_completed
from langchain_core.documents import Document
from langchain_community.document_loaders import PyPDFLoader, TextLoader, Docx2txtLoader
from google.genai import Client
from .auth import get_google_credentials

# Using the new google-genai SDK for extraction
PROJECT_ID = os.getenv("GOOGLE_CLOUD_PROJECT", "mock-project-id")
REGION = os.getenv("BQ_REGION", "us-central1")

credentials = get_google_credentials()
genai_client = Client(
    vertexai=True, 
    project=PROJECT_ID, 
    location=REGION, 
    credentials=credentials
)

def generate_content_with_retry(prompt: str, max_retries: int = 4) -> str:
    """Helper to call Gemini API with exponential backoff for rate limits."""
    for attempt in range(max_retries):
        try:
            response = genai_client.models.generate_content(
                model='gemini-2.5-flash',
                contents=prompt,
            )
            return response.text
        except Exception as e:
            if "429" in str(e) or "503" in str(e):
                if attempt == max_retries - 1:
                    print(f"Max retries reached: {e}")
                    raise
                sleep_time = 2 ** attempt
                print(f"Rate limited. Retrying in {sleep_time} seconds...")
                time.sleep(sleep_time)
            else:
                print(f"Failed to generate content: {e}")
                raise e
    return ""

def extract_propositions(scene_text: str) -> List[str]:
    """Uses LLM to extract atomic facts/propositions from a scene."""
    prompt = (
        "Extract key atomic facts, character arcs, and lore from the following scene as a list of short, standalone propositions.\n"
        "Return each proposition on a new line.\n\n"
        f"Scene:\n{scene_text}\n\nPropositions:"
    )
    
    try:
        response_text = generate_content_with_retry(prompt)
        propositions = [p.strip('-* ') for p in response_text.split('\n') if p.strip()]
        return propositions
    except Exception:
        return []

def get_global_context(full_text: str) -> str:
    """Uses LLM to get a global summary of the script for Late Chunking simulation."""
    truncated_text = full_text[:30000]
    prompt = (
        "Provide a concise summary of the main plot, themes, and characters of this script "
        "to be used as global context for document retrieval.\n\n"
        f"Script:\n{truncated_text}\n\nSummary:"
    )
    try:
        response_text = generate_content_with_retry(prompt)
        return response_text.strip()
    except Exception:
        return "A movie script."

def process_scene(i: int, scene_text: str, global_context: str) -> List[Document]:
    """Processes a single scene text into chunked and enriched Documents."""
    scene_text = scene_text.strip()
    if not scene_text:
        return []
        
    lines = scene_text.split('\n')
    scene_heading = lines[0].strip()
    
    # Simple extraction of characters in the scene
    char_pattern = re.compile(r'^[A-Z][A-Z0-9\s]+$')
    characters = set()
    for line in lines[1:]:
        if char_pattern.match(line.strip()) and len(line.strip()) > 2:
            characters.add(line.strip())
            
    chars_str = ", ".join(characters)
    metadata_prefix = f"[Scene {i+1} | {scene_heading} | Characters: {chars_str}]\n[Global Context: {global_context}]"
    
    # 1. Hierarchical: The scene is the parent
    parent_scene_id = f"scene_{i+1}"
    
    # 2. Child Chunks
    blocks = re.split(r'\n\s*\n', scene_text)
    current_chunk = []
    current_len = 0
    documents = []
    
    for block in blocks:
        block = block.strip()
        if not block:
            continue
        if current_len + len(block) > 400 and current_chunk:
            child_text = "\n\n".join(current_chunk)
            enriched_text = f"{metadata_prefix}\n\n{child_text}"
            doc = Document(
                page_content=enriched_text,
                metadata={
                    "scene_id": parent_scene_id,
                    "parent_text": scene_text, 
                    "type": "child_chunk"
                }
            )
            documents.append(doc)
            current_chunk = [block]
            current_len = len(block)
        else:
            current_chunk.append(block)
            current_len += len(block)
            
    if current_chunk:
        child_text = "\n\n".join(current_chunk)
        enriched_text = f"{metadata_prefix}\n\n{child_text}"
        doc = Document(
            page_content=enriched_text,
            metadata={
                "scene_id": parent_scene_id,
                "parent_text": scene_text,
                "type": "child_chunk"
            }
        )
        documents.append(doc)
        
    # 3. Propositional Embeddings
    propositions = extract_propositions(scene_text)
    for prop in propositions:
        prop_enriched = f"{metadata_prefix}\n\nFact: {prop}"
        doc = Document(
            page_content=prop_enriched,
            metadata={
                "scene_id": parent_scene_id,
                "parent_text": scene_text,
                "type": "proposition"
            }
        )
        documents.append(doc)
        
    return documents

def parse_and_chunk_script(full_text: str) -> List[Document]:
    """
    Custom parser that creates hierarchical, metadata-enriched, 
    and context-aware chunks from a movie script, using parallel processing.
    """
    global_context = get_global_context(full_text)
    
    scene_pattern = re.compile(r'^(INT\.|EXT\.)', re.IGNORECASE | re.MULTILINE)
    scene_splits = list(scene_pattern.finditer(full_text))
    
    if not scene_splits:
        return [Document(page_content=full_text, metadata={"global_context": global_context})]
        
    scene_texts = []
    for i in range(len(scene_splits)):
        start = scene_splits[i].start()
        end = scene_splits[i+1].start() if i + 1 < len(scene_splits) else len(full_text)
        scene_texts.append((i, full_text[start:end]))
        
    documents = []
    
    # Process scenes concurrently with a ThreadPoolExecutor
    with ThreadPoolExecutor(max_workers=5) as executor:
        future_to_scene = {
            executor.submit(process_scene, i, text, global_context): i 
            for i, text in scene_texts
        }
        
        for future in as_completed(future_to_scene):
            try:
                docs = future.result()
                documents.extend(docs)
            except Exception as e:
                scene_num = future_to_scene[future] + 1
                print(f"Error processing scene {scene_num}: {e}")

    return documents


def load_and_split_document(file_path: str, filename: str) -> List[Document]:
    """
    Loads a document (PDF, TXT, DOCX) and processes it with advanced chunking.
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
        
    raw_documents = loader.load()
    
    full_text = "\n".join([doc.page_content for doc in raw_documents])
    
    chunks = parse_and_chunk_script(full_text)
    
    return chunks
