# SceneIQ

SceneIQ is an agentic screenplay intelligence platform designed to convert screenplays and production documents into searchable, grounded, and actionable production knowledge. It features specialized toolsets for Filmmakers, Writers, and Film Enthusiasts.

## 🏛️ End-to-End Architecture Flow

The application leverages a modern AI architecture combining Retrieval-Augmented Generation (RAG) with real-world tool execution (MCP).

**1. Streamlit UI (Frontend Layer)**
- Users interact with the platform through a Streamlit web interface.
- It provides a chat interface and dedicated tabs for specialized tools (Producers, Writers, Enthusiasts).
- Sends requests containing user queries and (optional) session IDs to the FastAPI backend.

**2. FastAPI Backend (Orchestration Layer)**
- Serves as the central router (`api/main.py`) connecting the UI to various logic modules.
- Evaluates which tool or agent loop to invoke based on the requested endpoint (e.g., `/tools/producers/breakdown` vs `/chat`).

**3. Context Retrieval (Data Layer)**
Before sending prompts to the LLM, the backend gathers relevant context from two primary sources:
- **BigQuery Vector Search:** Natively queries stored script embeddings in BigQuery to find the exact scenes, characters, and plot points relevant to the request.
- **Parallel Search MCP:** Uses the Model Context Protocol (via FastMCP) to execute web searches for real-world data (e.g., industry trends, union rules, real-world budget constraints) that aren't inside the script.

**4. Google Gemini (Reasoning & Generation Layer)**
- **Gemini 2.5 Pro:** Used for deep creative reasoning, plot synthesis, and complex analysis (e.g., Script Doctor, Deep Cinematic Research).
- **Gemini 2.5 Flash:** Used for high-speed lookups, structured schema extractions, and rapid chat responses (e.g., Automated Production Scheduler, Bespoke Dialog Partner).
- **Gemini Visual/Imagen:** Handles multimodal tasks like cross-referencing audition videos (via GenAI Files API) or generating storyboard concepts.
- The backend enforces strict JSON schemas in the API calls to guarantee structured outputs.

**5. Downstream Applications (Output Layer)**
- The generated insights, structured JSON, or images are sent back to the FastAPI layer, which returns them to the Streamlit UI to be rendered as tables, charts, chats, or visual blueprints.

## 🛠️ Specialized Tool Modules

### 1. Filmmakers & Producers
- **AI Storyboarder:** Extracts scene data from BigQuery and generates visual frame references using Gemini.
- **Production Scheduler:** Parses scenes, characters, props, and VFX into structured CSV-ready formats.
- **Interactive Casting:** Cross-references audition videos against character profiles stored in BigQuery.

### 2. Writers & Script Editors
- **Dynamic Script Doctor:** Compares script structural beats against classic dramatic frameworks using parallel search.
- **Bespoke Dialog Partner:** Lets writers chat directly with characters based on their dialogue history and subtext.
- **Localization Engine:** Translates scripts while preserving regional slang and emotional tone.

### 3. Film Enthusiasts & Academics
- **Cinematic Deep Research:** Synthesizes academic-level breakdowns with precise page-level citations.
- **CYOA Simulator:** Converts linear scripts into interactive role-playing games based on lore.
- **Director's Commentary:** Maps timestamps and production notes to script chunks.

## 🚀 Getting Started

1. Clone the repository: `git clone https://github.com/Saurabh331/SceneIQ.git`
2. Install dependencies: `pip install -r requirements.txt`
3. Configure your `.env` file with Google OAuth credentials (`GOOGLE_CLIENT_ID`, `GOOGLE_CLIENT_SECRET`, `GOOGLE_REFRESH_TOKEN`).
4. Start the API Server: `uvicorn api.main:app --reload`
5. Start the Streamlit UI: `streamlit run app/ui.py`
6. Open the HTML animation file to visualize the flow: `architecture_diagram.html`
