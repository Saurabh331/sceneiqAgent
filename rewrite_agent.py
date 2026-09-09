import os

new_agent_content = '''import os
import json
import time
import asyncio
from dotenv import load_dotenv

from google.cloud import storage
from .auth import get_google_credentials
from .rag import retrieve_from_bq

import vertexai
from vertexai.preview.reasoning_engines import LangchainAgent

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
        
    return "\\n\\n---\\n\\n".join(chunks)

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
    scene_context = "\\n".join(chunks) if chunks else "No context found."
    
    prompt_instruction = f"Based on the following scene context, write a highly detailed, cinematic image generation prompt for a storyboard frame representing '{scene_query}'. Just output the prompt text.\\n\\nContext:\\n{scene_context[:3000]}"
    
    from google import genai
    client = genai.Client(vertexai=True, project=PROJECT_ID, location=LOCATION, credentials=credentials)
    
    try:
        response = client.models.generate_content(model="gemini-2.5-flash", contents=prompt_instruction)
        return f"Storyboard Prompt Generated: {response.text.strip()}"
    except Exception as e:
        return f"Failed to generate storyboard prompt: {e}"

def script_doctor_tool(session_id: str, framework: str) -> str:
    """
    Runs the Script Doctor to analyze the pacing and structure of the script against a given framework (e.g., 'Hero\\'s Journey').
    Requires the session_id.
    """
    if MOCK_MODE:
        return f"Mock Script Doctor Analysis using {framework}: The pacing is good, but Act 2 lags."
        
    chunks = retrieve_from_bq(session_id, "entire script plot summary", top_k=20)
    context = "\\n".join(chunks) if chunks else "No context found."
    
    prompt = f"Analyze the pacing and structural beats of the following script chunks using the '{framework}' framework. Identify any pacing issues or missing beats.\\n\\n{context[:8000]}"
    
    from google import genai
    client = genai.Client(vertexai=True, project=PROJECT_ID, location=LOCATION, credentials=credentials)
    
    try:
        response = client.models.generate_content(model="gemini-2.5-flash", contents=prompt)
        return response.text
    except Exception as e:
        return f"Failed to run script doctor: {e}"

def parallel_search(query: str) -> str:
    """
    Performs a web search to find external production context, industry trends, and budget constraints.
    Use this tool when the question requires information outside of the script (e.g., current real-world data).
    """
    import asyncio
    import os
    import nest_asyncio
    from fastmcp import Client
    
    nest_asyncio.apply()
    
    async def run_mcp():
        npx_cmd = "npx.cmd" if os.name == "nt" else "npx"
        mcp_config = {
            "mcpServers": {
                "parallel_search": {
                    "command": npx_cmd,
                    "args": ["-y", "@modelcontextprotocol/server-parallel-search"]
                }
            }
        }
        try:
            async with Client(mcp_config) as mcp_client:
                tools = await mcp_client.list_tools()
                if not tools:
                    return "No tools found in parallel_search MCP."
                
                # Assume the first tool is the web search tool
                tool_name = tools[0].name
                mcp_result = await mcp_client.call_tool_mcp(tool_name, arguments={"query": query})
                
                result_texts = []
                for content in mcp_result.content:
                    if content.type == "text":
                        result_texts.append(content.text)
                return "\\n".join(result_texts)
        except Exception as e:
            return f"Error executing FastMCP: {e}"
            
    try:
        return asyncio.run(run_mcp())
    except Exception as e:
        return f"Error executing parallel_search: {e}"

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
        final_answer = f"Based on the agent's research: \\n\\nContext found: {context[:300]}..."
        return {"response": final_answer, "tool_log": tool_log}
        
    base_instruction = "You are a filmmaking and entertainment industry AI assistant. You must ONLY answer questions related to filmmaking, the entertainment industry, screenwriting, production, etc. using your tools or general knowledge. If the user asks about unrelated topics, politely decline.\\n\\n"
    if session_id:
        base_instruction += f"IMPORTANT: You are analyzing a document with session_id = '{session_id}'. You MUST pass this exact session_id string to any tool that requires it as an argument.\\n"
    
    if system_instruction:
        base_instruction += f"\\n{system_instruction}"

    # Initialize the LangchainAgent from Vertex AI Reasoning Engine
    agent = LangchainAgent(
        model="gemini-2.5-flash",
        tools=[retrieve_from_script, generate_storyboard_tool, script_doctor_tool, parallel_search],
        agent_executor_kwargs={"return_intermediate_steps": True},
        system_instruction=base_instruction
    )
    
    # Execute the agent synchronously (using to_thread to avoid blocking FastAPI's loop)
    try:
        # LangchainAgent.query() returns a dictionary. Since return_intermediate_steps=True, 
        # it should contain 'output' and 'intermediate_steps'.
        response = await asyncio.to_thread(agent.query, input=user_query)
        
        final_text = response.get("output", "")
        intermediate_steps = response.get("intermediate_steps", [])
        
        for step in intermediate_steps:
            # step is usually a tuple (AgentAction, Observation)
            action, observation = step
            tool_log.append(f"Action: Call '{action.tool}' with args: {action.tool_input}")
            tool_log.append(f"Observation: {str(observation)[:200]}...")
            
        tool_log.append("Action: Return final response to user.")
        
        return {"response": final_text, "tool_log": tool_log}
        
    except Exception as e:
        print(f"Agent Engine Error: {e}")
        return {"response": f"An error occurred during agent execution: {e}", "tool_log": tool_log}
'''

with open('api/agent.py', 'w', encoding='utf-8') as f:
    f.write(new_agent_content)

print("api/agent.py rewritten.")
