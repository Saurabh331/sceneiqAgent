import json
import urllib.request

url = 'https://raw.githubusercontent.com/GoogleCloudPlatform/generative-ai/main/gemini/agent-engine/intro_agent_engine.ipynb'
try:
    with urllib.request.urlopen(url) as response:
        notebook = json.loads(response.read().decode())
        
    code_cells = []
    for cell in notebook.get('cells', []):
        if cell['cell_type'] == 'code':
            source = ''.join(cell['source'])
            if source.strip():
                code_cells.append(source)
                
    with open('notebook_code.py', 'w', encoding='utf-8') as f:
        f.write('\n\n# --- CELL ---\n\n'.join(code_cells))
        
    print(f"Extracted {len(code_cells)} code cells to notebook_code.py")
except Exception as e:
    print(f"Error: {e}")
