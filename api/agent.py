import os
import json
import time
import asyncio
from dotenv import load_dotenv

from google.cloud import storage
from .auth import get_google_credentials
from .rag import retrieve_from_bq

import vertexai
from vertexai.preview.reasoning_engines import LangchainAgent
from google import genai
from .logger import get_logger

logger = get_logger(__name__)

load_dotenv()

credentials = get_google_credentials()
API_KEY = os.getenv("GEMINI_API_KEY")
PROJECT_ID = os.getenv("GOOGLE_CLOUD_PROJECT", "mock-project-id")
LOCATION = os.getenv("BQ_REGION", "us-central1")

client = None
MOCK_MODE = False

if API_KEY and API_KEY != "mock":
    # Use API Key for Google AI Studio
    try:
        client = genai.Client(api_key=API_KEY)
        MOCK_MODE = False
    except Exception as e:
        print(f"Warning: Failed to initialize genai.Client with API_KEY: {e}")

if client is None and credentials:
    # Fallback to Vertex AI using GCP credentials
    project_id = os.getenv("GOOGLE_CLOUD_PROJECT")
    location = os.getenv("BQ_REGION", "us-central1")
    try:
        client = genai.Client(vertexai=True, project=project_id, location=location, credentials=credentials)
        MOCK_MODE = False
    except Exception as e:
        print(f"Warning: Failed to initialize Vertex AI genai.Client: {e}")

if client is None:
    client = None
    MOCK_MODE = True

# Initialize Vertex AI for Agent Engine
if not MOCK_MODE:
    vertexai.init(project=PROJECT_ID, location=LOCATION, credentials=credentials)

# --- Define Tools ---

def retrieve_from_script(session_id: str, query: str) -> str:
    """
    Retrieves information from the uploaded screenplay document.
    Always use this tool first when asked about the script's contents.
    Requires the session_id to identify the correct document.
    """
    if not session_id:
        return "No script has been uploaded. Do not attempt to search the script."
        
    chunks = retrieve_from_bq(session_id, query)
    if not chunks:
        return "No relevant context found in the BigQuery Vector Store."
        
    return "\n\n---\n\n".join(chunks)

def generate_storyboard_tool(session_id: str, scene_query: str) -> str:
    """
    Generates an image prompt for a storyboard frame based on a scene query.
    Call this when the user asks to generate a storyboard or visualize a scene.
    Requires the session_id.
    """
    if MOCK_MODE:
        return f"Mock storyboard prompt for '{scene_query}'"
        
    # Reuse RAG to get scene context
    chunks = retrieve_from_bq(session_id, scene_query)
    scene_context = "\n".join(chunks) if chunks else "No context found."
    
    prompt_instruction = f"Based on the following scene context, write a highly detailed, cinematic image generation prompt for a storyboard frame representing '{scene_query}'. Just output the prompt text.\n\nContext:\n{scene_context[:3000]}"
    
    from google import genai
    client = genai.Client(vertexai=True, project=PROJECT_ID, location=LOCATION, credentials=credentials)
    
    try:
        response = client.models.generate_content(model="gemini-2.5-flash", contents=prompt_instruction)
        return f"Storyboard Prompt Generated: {response.text.strip()}"
    except Exception as e:
        return f"Failed to generate storyboard prompt: {e}"

def script_doctor_tool(session_id: str, framework: str) -> str:
    """
    Runs the Script Doctor to analyze the pacing and structure of the script against a given framework (e.g., 'Hero\'s Journey').
    Requires the session_id.
    """
    if MOCK_MODE:
        return f"Mock Script Doctor Analysis using {framework}: The pacing is good, but Act 2 lags."
        
    chunks = retrieve_from_bq(session_id, "entire script plot summary", top_k=20)
    context = "\n".join(chunks) if chunks else "No context found."
    
    prompt = f"Analyze the pacing and structural beats of the following script chunks using the '{framework}' framework. Identify any pacing issues or missing beats.\n\n{context[:8000]}"
    
    from google import genai
    client = genai.Client(vertexai=True, project=PROJECT_ID, location=LOCATION, credentials=credentials)
    
    try:
        response = client.models.generate_content(model="gemini-2.5-flash", contents=prompt)
        return response.text
    except Exception as e:
        return f"Failed to run script doctor: {e}"

def parallel_search(query: str) -> str:
    """
    Performs a web search to find external production context, industry trends, real-time pricing, and budget constraints.
    CRITICAL: You MUST use this tool whenever the user's question requires real-world data, current events, equipment costs, or information outside of the provided script (e.g., "How much does it cost to rent an ARRI Alexa?").
    """
    try:
        import os
        from google import genai
        from google.genai import types
        
        project_id = os.getenv("GOOGLE_CLOUD_PROJECT", "mock-project-id")
        location = os.getenv("BQ_REGION", "us-central1")
        
        # In mock mode, just return a fake result
        if os.getenv("MOCK_MODE", "false").lower() == "true":
            return f"Search Result for '{query}': The ARRI Alexa typically costs between $1,000 and $3,000 per day to rent depending on the package."
            
        client = genai.Client(vertexai=True, project=project_id, location=location)
        response = client.models.generate_content(
            model='gemini-2.5-flash',
            contents=f"Please execute a web search to provide a highly accurate and up-to-date answer for the following query. Provide specific numbers or data where applicable: {query}",
            config=types.GenerateContentConfig(
                tools=[{"google_search": {}}]
            )
        )
        return response.text
    except Exception as e:
        return f"Error executing Google Search: {e}"

# --- Agent Orchestration ---

async def process_agentic_chat_stream(session_id: str = None, user_query: str = "", system_instruction: str = None):
    """
    Main orchestration loop for the agent using Vertex AI Reasoning Engine (LangchainAgent).
    Yields JSON strings containing intermediate steps and final response for streaming.
    """
    tool_log = []

    if MOCK_MODE:
        yield json.dumps({"type": "log", "content": "Executing Agentic Loop (MOCK MODE)"}) + "\n"
        await asyncio.sleep(0.5)
        yield json.dumps({"type": "log", "content": f"Action: Call 'retrieve_from_script' with query '{user_query}'"}) + "\n"
        context = retrieve_from_script(session_id, user_query)
        await asyncio.sleep(0.5)
        yield json.dumps({"type": "log", "content": f"Observation: {context[:100]}..."}) + "\n"
        final_answer = f"Based on the agent's research: \n\nContext found: {context[:300]}..."
        
        # Simulate text streaming
        for chunk in final_answer.split(" "):
            yield json.dumps({"type": "chunk", "content": chunk + " "}) + "\n"
            await asyncio.sleep(0.1)
        return
        
    base_instruction = "You are a filmmaking and entertainment industry AI assistant. You must ONLY answer questions related to filmmaking, the entertainment industry, screenwriting, production, etc. using your tools or general knowledge. If the user asks about unrelated topics, politely decline.\n\nCRITICAL TOOL USAGE RULE: When the user asks for real-world information, current data, external industry context, budget info, or real-time pricing (e.g., camera rental costs, equipment specs), you MUST use the `parallel_search` tool to find the answer. Do NOT guess or say you don't know without trying the `parallel_search` tool first.\n\n"
    if session_id:
        base_instruction += f"IMPORTANT: You are analyzing a document with session_id = '{session_id}'. You MUST pass this exact session_id string to any tool that requires it as an argument.\n"
    
    if system_instruction:
        base_instruction += f"\n{system_instruction}"

    # Initialize the LangchainAgent from Vertex AI Reasoning Engine
    agent = LangchainAgent(
        model="gemini-2.5-flash",
        tools=[retrieve_from_script, generate_storyboard_tool, script_doctor_tool, parallel_search],
        agent_executor_kwargs={"return_intermediate_steps": True},
        system_instruction=base_instruction
    )
    
    try:
        logger.info(f"Starting streaming agent execution for session {session_id} with query: {user_query}")
        
        # Fallback to streaming the final response chunk by chunk since native ReasoningEngine might not easily stream events
        response = await asyncio.to_thread(agent.query, input=user_query)
        
        intermediate_steps = response.get("intermediate_steps", [])
        for step in intermediate_steps:
            action, observation = step
            tool_name = action.get("tool") if isinstance(action, dict) else getattr(action, "tool", "unknown")
            tool_input = action.get("tool_input") if isinstance(action, dict) else getattr(action, "tool_input", "unknown")
            
            log_msg = f"Action: Call '{tool_name}' with args: {tool_input}"
            logger.info(f"Agent Action: {log_msg}")
            yield json.dumps({"type": "log", "content": log_msg}) + "\n"
            yield json.dumps({"type": "log", "content": f"Observation: {str(observation)[:200]}..."}) + "\n"
            
        yield json.dumps({"type": "log", "content": "Action: Return final response to user."}) + "\n"
        
        final_text_raw = response.get("output", "")
        if isinstance(final_text_raw, list):
            parts = [part["text"] if isinstance(part, dict) and "text" in part else str(part) for part in final_text_raw]
            final_text = "".join(parts)
        else:
            final_text = str(final_text_raw)
            
        # Stream the text chunks
        # To make it appear streaming and avoid timeouts, we yield words
        words = final_text.split(" ")
        for i, word in enumerate(words):
            yield json.dumps({"type": "chunk", "content": word + (" " if i < len(words) - 1 else "")}) + "\n"
            
    except Exception as e:
        logger.error(f"Agent Engine Error: {e}", exc_info=True)
        yield json.dumps({"type": "error", "content": f"An error occurred during agent execution: {e}"}) + "\n"
