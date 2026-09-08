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

from .logger import get_logger

logger = get_logger(__name__)

load_dotenv()

credentials = get_google_credentials()
API_KEY = os.getenv("GEMINI_API_KEY")
PROJECT_ID = os.getenv("GOOGLE_CLOUD_PROJECT", "mock-project-id")
LOCATION = os.getenv("BQ_REGION", "us-central1")

if API_KEY and API_KEY != "mock":
    MOCK_MODE = False
elif credentials:
    MOCK_MODE = False
else:
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

async def process_agentic_chat(session_id: str = None, user_query: str = "", system_instruction: str = None) -> dict:
    """
    Main orchestration loop for the agent using Vertex AI Reasoning Engine (LangchainAgent).
    """
    tool_log = []

    if MOCK_MODE:
        tool_log.append("Executing Agentic Loop (MOCK MODE)")
        tool_log.append(f"Action: Call 'retrieve_from_script' with query '{user_query}'")
        context = retrieve_from_script(session_id, user_query)
        tool_log.append(f"Observation: {context[:100]}...")
        final_answer = f"Based on the agent's research: \n\nContext found: {context[:300]}..."
        return {"response": final_answer, "tool_log": tool_log}
        
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
    
    # Execute the agent synchronously (using to_thread to avoid blocking FastAPI's loop)
    try:
        logger.info(f"Starting agent execution for session {session_id} with query: {user_query}")
        # LangchainAgent.query() returns a dictionary. Since return_intermediate_steps=True, 
        # it should contain 'output' and 'intermediate_steps'.
        response = await asyncio.to_thread(agent.query, input=user_query)
        
        final_text_raw = response.get("output", "")
        if isinstance(final_text_raw, list):
            parts = []
            for part in final_text_raw:
                if isinstance(part, dict) and "text" in part:
                    parts.append(part["text"])
                elif isinstance(part, str):
                    parts.append(part)
                else:
                    parts.append(str(part))
            final_text = "".join(parts)
        else:
            final_text = str(final_text_raw)
            
        intermediate_steps = response.get("intermediate_steps", [])
        
        for step in intermediate_steps:
            # step is usually a tuple (AgentAction, Observation)
            action, observation = step
            tool_name = action.get("tool") if isinstance(action, dict) else getattr(action, "tool", "unknown")
            tool_input = action.get("tool_input") if isinstance(action, dict) else getattr(action, "tool_input", "unknown")
            logger.info(f"Agent Action: Call '{tool_name}' with args: {tool_input}")
            tool_log.append(f"Action: Call '{tool_name}' with args: {tool_input}")
            tool_log.append(f"Observation: {str(observation)[:200]}...")
            
        tool_log.append("Action: Return final response to user.")
        logger.info("Agent execution completed successfully.")
        
        return {"response": final_text, "tool_log": tool_log}
        
    except Exception as e:
        logger.error(f"Agent Engine Error: {e}", exc_info=True)
        return {"response": f"An error occurred during agent execution: {e}", "tool_log": tool_log}
