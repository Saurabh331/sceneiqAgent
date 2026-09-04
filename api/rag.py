import os
from typing import List
from google.cloud import bigquery
from langchain_google_vertexai import VertexAIEmbeddings
from langchain_google_community import BigQueryVectorStore
from dotenv import load_dotenv, find_dotenv

load_dotenv(find_dotenv())

PROJECT_ID = os.getenv("GOOGLE_CLOUD_PROJECT", "mock-project-id")
DATASET = os.getenv("BQ_DATASET", "sceneiq_dataset")
REGION = os.getenv("BQ_REGION", "us-central1")
TABLE_NAME = "screenplay_embeddings"

def get_vector_store() -> BigQueryVectorStore:
    """Initializes and returns the BigQuery Vector Store."""
    from .auth import get_google_credentials
    credentials = get_google_credentials()

    embeddings = VertexAIEmbeddings(
        model_name="text-embedding-large-exp-03-07",
        project=PROJECT_ID,
        credentials=credentials
    )
    
    # In a real environment, BigQueryVectorStore needs valid credentials and project setup.
    # We try to initialize it; if it fails due to mock keys, we handle it in the caller.
    client = bigquery.Client(project=PROJECT_ID, credentials=credentials) if credentials else None
    
    store = BigQueryVectorStore(
        project_id=PROJECT_ID,
        dataset_name=DATASET,
        table_name=TABLE_NAME,
        location=REGION,
        embedding=embeddings,
        # Pass explicit client if it's available and supported, otherwise rely on ADC
    )
    
    if client:
        store.client = client
        
    return store

def ingest_chunks_to_bq(chunks: List, session_id: str):
    """Embeds and stores chunks in BigQuery."""
    # Inject session_id into metadata for filtering during retrieval
    for chunk in chunks:
        chunk.metadata["session_id"] = session_id
        
    store = get_vector_store()
    
    if PROJECT_ID == "mock-project-id":
        print(f"[MOCK] Would ingest {len(chunks)} chunks into BigQuery dataset {DATASET}.{TABLE_NAME}")
        return
        
    # Add documents to the vector store in batches to avoid Vertex AI embedding limit (250)
    batch_size = 250
    for i in range(0, len(chunks), batch_size):
        batch = chunks[i:i + batch_size]
        store.add_documents(batch)

def retrieve_from_bq(session_id: str, query: str, top_k: int = 4) -> List[str]:
    """Retrieves context from BigQuery using vector similarity."""
    if PROJECT_ID == "mock-project-id":
        return [f"[MOCK BQ] Retrieved mock context for query '{query}' from session {session_id}."]
        
    store = get_vector_store()
    
    # Filter by session_id to only search within the uploaded document
    # Note: BigQueryVectorStore supports filtering via metadata dicts or SQL WHERE strings depending on version.
    # Assuming basic metadata filtering is supported:
    filter_dict = {"session_id": session_id}
    
    try:
        results = store.similarity_search(query, k=top_k, filter=filter_dict)
        return [doc.page_content for doc in results]
    except Exception as e:
        print(f"Error during BQ retrieval: {e}")
        return []
