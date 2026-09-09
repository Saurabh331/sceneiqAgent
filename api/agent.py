import os
import json
import time
import asyncio
from google import genai
from google.genai import types
from dotenv import load_dotenv

from .rag import retrieve_from_bq
from google.oauth2 import service_account
from google.cloud import storage
from google import genai
from google.genai.types import HttpOptions

from .auth import get_google_credentials

load_dotenv()

credentials = get_google_credentials()
API_KEY = os.getenv("GEMINI_API_KEY")

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

def send_message_with_retry(client, model, contents, config, max_retries=2):
    """Sends a message to the Gemini API with exponential backoff retry for 429 and 503 errors."""
    for attempt in range(max_retries):
        try:
            resp = client.models.generate_content(
                model=model,
                contents=contents,
                config=config
            )
            return resp
        except Exception as e:
            error_str = str(e)
            if "503" in error_str or "429" in error_str or "quota" in error_str.lower() or "limit" in error_str.lower():
                if attempt < max_retries - 1:
                    wait_time = 15 * (attempt + 1)
                    print(f"Encountered API error: {error_str[:100]}... Retrying in {wait_time} seconds (Attempt {attempt+1}/{max_retries})...")
                    time.sleep(wait_time)
                    continue
            raise e

def search_screenplay(session_id: str, query: str) -> str:
    """
    Retrieves information from the uploaded screenplay document to answer questions about the story, characters, and scenes.
    """
    chunks = retrieve_from_bq(session_id, query)
    if not chunks:
        return "No relevant context found in the BigQuery Vector Store."
        
    return "\n\n---\n\n".join(chunks)

def parallel_search(query: str) -> str:
    """
    Performs a web search to find external production context, industry trends, and budget constraints.
    Use this tool when the question requires information outside of the script (e.g., current real-world data).
    """
    return f"Mocked Web Search Results for '{query}': According to recent production data, similar requirements typically incur a 15% budget premium due to 2026 industry standards and union rules."

async def _run_gemini_loop(mcp_client, mcp_tool_map, gemini_tools, retrieve_from_script, user_query, system_instruction, tool_log) -> dict:
    base_instruction = (
        "You are a filmmaking and entertainment industry AI assistant. You must ONLY answer questions related to "
        "filmmaking, the entertainment industry, screenwriting, production, etc. using your parallel_search tool "
        "or general knowledge. If the user asks about unrelated topics, politely decline."
    )
    if system_instruction:
        full_instruction = base_instruction + "\n\n" + system_instruction
    else:
        full_instruction = base_instruction

    config_kwargs = {
        "tools": gemini_tools,
        "automatic_function_calling": types.AutomaticFunctionCallingConfig(disable=True),
        "system_instruction": full_instruction
    }
        
    config = types.GenerateContentConfig(**config_kwargs)
    contents = [f" User Question: {user_query}"]
    
    response = await asyncio.to_thread(send_message_with_retry, client, "gemini-2.5-flash", contents, config)
    
    while response.function_calls:
        contents.append(response.candidates[0].content)
        tool_response_parts = []
        
        for function_call in response.function_calls:
            func_name = function_call.name
            args = function_call.args or {}
            
            tool_log.append(f"Action: Call '{func_name}' with args: {args}")
            
            try:
                if func_name == "retrieve_from_script":
                    tool_result = retrieve_from_script(**args)
                elif func_name == "parallel_search":
                    tool_result = parallel_search(**args)
                elif mcp_client and func_name in mcp_tool_map:
                    mcp_result = await mcp_client.call_tool(func_name, arguments=args)
                    if hasattr(mcp_result, "content") and isinstance(mcp_result.content, list):
                        result_texts = [c.text for c in mcp_result.content if hasattr(c, "text")]
                        tool_result = "\n".join(result_texts)
                    else:
                        tool_result = str(mcp_result)
                else:
                    tool_result = parallel_search(args.get("query", str(args)))
            except Exception as e:
                tool_result = parallel_search(args.get("query", str(args)))
                
            tool_log.append(f"Observation: {str(tool_result)[:200]}...")
            
            tool_response_parts.append(
                types.Part.from_function_response(
                    name=func_name,
                    response={"result": tool_result}
                )
            )
            
        contents.append(types.Content(role="user", parts=tool_response_parts))
        response = await asyncio.to_thread(send_message_with_retry, client, "gemini-2.5-flash", contents, config)

    tool_log.append("Action: Return final response to user.")
    return {"response": response.text, "tool_log": tool_log}

async def process_agentic_chat(session_id: str = None, user_query: str = "", system_instruction: str = None) -> dict:
    """
    Main orchestration loop for the agent using Gemini Tool Calling and the Parallel Search MCP Server via FastMCP.
    """
    def retrieve_from_script(query: str) -> str:
        """
        Retrieves information from the uploaded screenplay document.
        Always use this tool first when asked about the script's contents.
        """
        if not session_id:
            return "No script has been uploaded. Do not attempt to search the script."
        return search_screenplay(session_id, query)
        
    tool_log = []

    if MOCK_MODE or client is None:
        tool_log.append("Executing Agentic Loop (MOCK MODE)")
        tool_log.append(f"Action: Call 'retrieve_from_script' with query '{user_query}'")
        context = retrieve_from_script(user_query)
            
        tool_log.append(f"Observation: {context[:100]}...")
        final_answer = f"Based on the agent's research: \n\nContext found: {context[:300]}..."
        return {"response": final_answer, "tool_log": tool_log}
        
    # Attempt connecting to Parallel Search MCP Server via FastMCP
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
        from fastmcp import Client
        from fastmcp.client.transports import MCPConfigTransport
        
        async with Client(MCPConfigTransport(mcp_config), timeout=10) as mcp_client:
            mcp_tools = await mcp_client.list_tools()
            gemini_tools = [retrieve_from_script]
            mcp_tool_map = {}
            
            for mcp_tool in mcp_tools:
                gemini_tools.append({
                    "function_declarations": [
                        {
                            "name": mcp_tool.name,
                            "description": mcp_tool.description,
                            "parameters": mcp_tool.inputSchema
                        }
                    ]
                })
                mcp_tool_map[mcp_tool.name] = mcp_tool
                
            return await _run_gemini_loop(
                mcp_client=mcp_client,
                mcp_tool_map=mcp_tool_map,
                gemini_tools=gemini_tools,
                retrieve_from_script=retrieve_from_script,
                user_query=user_query,
                system_instruction=system_instruction,
                tool_log=tool_log
            )
    except Exception as mcp_err:
        print(f"Info: FastMCP unavailable ({mcp_err}). Using native Gemini tools fallback.")
        gemini_tools = [retrieve_from_script, parallel_search]
        return await _run_gemini_loop(
            mcp_client=None,
            mcp_tool_map={},
            gemini_tools=gemini_tools,
            retrieve_from_script=retrieve_from_script,
            user_query=user_query,
            system_instruction=system_instruction,
            tool_log=tool_log
        )
