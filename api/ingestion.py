import os
from PyPDF2 import PdfReader

def parse_document(file_path: str, filename: str) -> str:
    """
    Parses a PDF or Text file and returns the extracted text.
    """
    ext = os.path.splitext(filename)[1].lower()
    
    if ext == '.pdf':
        return _parse_pdf(file_path)
    elif ext in ['.txt', '.md']:
        return _parse_txt(file_path)
    else:
        raise ValueError(f"Unsupported file format: {ext}")

def _parse_pdf(file_path: str) -> str:
    text = ""
    try:
        reader = PdfReader(file_path)
        for page in reader.pages:
            page_text = page.extract_text()
            if page_text:
                text += page_text + "\n"
    except Exception as e:
        print(f"Error reading PDF: {e}")
    return text

def _parse_txt(file_path: str) -> str:
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            return f.read()
    except Exception as e:
        print(f"Error reading TXT: {e}")
        return ""

def chunk_text(text: str, chunk_size: int = 1000, overlap: int = 200) -> list[str]:
    """
    Splits text into overlapping chunks.
    """
    if not text:
        return []
    
    chunks = []
    start = 0
    while start < len(text):
        end = start + chunk_size
        chunks.append(text[start:end])
        start += chunk_size - overlap
    return chunks
