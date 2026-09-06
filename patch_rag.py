import re

with open('api/rag.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Add Vertex AI import back
content = content.replace(
    'from langchain_huggingface import HuggingFaceEmbeddings',
    'from langchain_huggingface import HuggingFaceEmbeddings\nfrom langchain_google_vertexai import VertexAIEmbeddings'
)

# Replace get_vector_store
old_get_vector_store = '''def get_vector_store() -> BigQueryVectorStore:
    """Initializes and returns the BigQuery Vector Store."""
    from .auth import get_google_credentials
    credentials = get_google_credentials()

    embeddings = HuggingFaceEmbeddings(
        model_name="all-MiniLM-L6-v2"
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
    
    return store'''

new_get_vector_store = '''def get_vector_store(embedding_type: str = "vertexai") -> BigQueryVectorStore:
    """Initializes and returns the BigQuery Vector Store dynamically based on type."""
    from .auth import get_google_credentials
    credentials = get_google_credentials()

    if embedding_type == "huggingface":
        embeddings = HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2")
        table_name = "screenplay_embeddings_large"
    else:
        embeddings = VertexAIEmbeddings(
            model="gemini-embedding-001",
            project=PROJECT_ID,
            credentials=credentials,
            dimensions=256
        )
        table_name = "screenplay_embeddings"
    
    client = bigquery.Client(project=PROJECT_ID, credentials=credentials) if credentials else None
    
    store = BigQueryVectorStore(
        project_id=PROJECT_ID,
        dataset_name=DATASET,
        table_name=table_name,
        location=REGION,
        embedding=embeddings,
    )
    
    return store'''

content = content.replace(old_get_vector_store, new_get_vector_store)

# Replace ingest_chunks_to_bq
content = content.replace(
    'def ingest_chunks_to_bq(chunks: List, session_id: str):',
    'def ingest_chunks_to_bq(chunks: List, session_id: str, embedding_type: str = "vertexai"):'
)
content = content.replace(
    'store = get_vector_store()',
    'store = get_vector_store(embedding_type)'
)
content = content.replace(
    'dataset {DATASET}.{TABLE_NAME}',
    'dataset {DATASET}.{store.table_name}'
)

# Replace retrieve_from_bq
old_retrieve = '''def retrieve_from_bq(session_id: str, query: str, top_k: int = 4) -> List[str]:
    """Retrieves context from BigQuery using vector similarity."""
    if PROJECT_ID == "mock-project-id":
        return [f"[MOCK BQ] Retrieved mock context for query '{query}' from session {session_id}."]
        
    store = get_vector_store()'''

new_retrieve = '''def retrieve_from_bq(session_id: str, query: str, top_k: int = 4) -> List[str]:
    """Retrieves context from BigQuery using vector similarity."""
    if PROJECT_ID == "mock-project-id":
        return [f"[MOCK BQ] Retrieved mock context for query '{query}' from session {session_id}."]
        
    from .models import DB
    doc = DB["documents"].get(session_id)
    embedding_type = doc.embedding_type if doc else "vertexai"
    store = get_vector_store(embedding_type)'''

content = content.replace(old_retrieve, new_retrieve)

with open('api/rag.py', 'w', encoding='utf-8') as f:
    f.write(content)

print("Patched rag.py")
