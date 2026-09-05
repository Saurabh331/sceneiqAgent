import os
import json
import time
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

if API_KEY and API_KEY != "mock":
    # Use API Key for Google AI Studio
    # client = genai.Client(api_key=API_KEY)
    MOCK_MODE = False
elif credentials:
    # If no API key is provided, assume we want Vertex AI using GCP credentials
    project_id = os.getenv("GOOGLE_CLOUD_PROJECT")
    location = os.getenv("BQ_REGION", "us-central1")
    client = genai.Client(vertexai=True, project=project_id, location=location, credentials=credentials)
    MOCK_MODE = False
else:
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

def process_agentic_chat(session_id: str, user_query: str, system_instruction: str = None) -> dict:
    """
    Main orchestration loop for the agent using Gemini Tool Calling.
    """
    def retrieve_from_script(query: str) -> str:
        """
        Retrieves information from the uploaded screenplay document.
        Always use this tool first when asked about the script's contents.
        """
        return search_screenplay(session_id, query)

    available_tools = {
        "retrieve_from_script": retrieve_from_script,
        "parallel_search": parallel_search
    }

    tools_list = [retrieve_from_script, parallel_search]
    tool_log = []

    if MOCK_MODE:
        tool_log.append("Executing Agentic Loop (MOCK MODE)")
        if "budget" in user_query.lower() or "cost" in user_query.lower() or "real world" in user_query.lower():
            tool_log.append(f"Action: Call 'parallel_search' with query '{user_query}'")
            context = parallel_search(user_query)
        else:
            tool_log.append(f"Action: Call 'retrieve_from_script' with query '{user_query}'")
            context = retrieve_from_script(user_query)
            
        tool_log.append(f"Observation: {context[:100]}...")
        final_answer = f"Based on the agent's research: \n\nContext found: {context[:300]}..."
        return {"response": final_answer, "tool_log": tool_log}

    else:
        config_kwargs = {
            "tools": tools_list,
            "automatic_function_calling": types.AutomaticFunctionCallingConfig(disable=True)
        }
        if system_instruction:
            config_kwargs["system_instruction"] = system_instruction
            
        config = types.GenerateContentConfig(**config_kwargs)
        
        # Initialize contents array with user prompt
        contents = [
            f""" User Question: {user_query}"""
        ]
        
        response = send_message_with_retry(client, model="gemini-2.5-flash", contents=contents, config=config)
        
        while response.function_calls:
            # Append model's tool calls to the history
            contents.append(response.candidates[0].content)
            tool_response_parts = []
            
            for function_call in response.function_calls:
                func_name = function_call.name
                args = function_call.args
                
                tool_log.append(f"Action: Call '{func_name}' with args: {args}")
                
                if func_name in available_tools:
                    tool_func = available_tools[func_name]
                    try:
                        tool_result = tool_func(**args)
                    except Exception as e:
                        tool_result = f"Error executing tool: {e}"
                else:
                    tool_result = f"Error: Tool {func_name} not found."
                    
                tool_log.append(f"Observation: {str(tool_result)[:200]}...")
                
                tool_response_parts.append(
                    types.Part.from_function_response(
                        name=func_name,
                        response={"result": tool_result}
                    )
                )
                
            # Append the tool responses to the history
            contents.append(types.Content(role="user", parts=tool_response_parts))
            
            # Send back the results to get final generation
            response = send_message_with_retry(client, model="gemini-2.5-flash", contents=contents, config=config)

        tool_log.append("Action: Return final response to user.")
        return {"response": response.text, "tool_log": tool_log}
