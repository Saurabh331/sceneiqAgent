import os
import json
from google import genai
from google.genai import types
from dotenv import load_dotenv

from .rag import retrieve_from_bq
load_dotenv()

PROJECT_ID = os.getenv("GOOGLE_CLOUD_PROJECT")
LOCATION = os.getenv("GOOGLE_CLOUD_LOCATION") or "us-central1"

if PROJECT_ID and PROJECT_ID != "mock-project-id":
    try:
        # Vertex AI automatically picks up Application Default Credentials (ADC)
        client = genai.Client(
            vertexai=True,
            project=PROJECT_ID,
            location=LOCATION,
        )
        MOCK_MODE = False
    except Exception as e:
        print(f"Warning: Failed to initialize Vertex AI client: {e}")
        client = None
        MOCK_MODE = True
else:
    client = None
    MOCK_MODE = True

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

def process_agentic_chat(session_id: str, user_query: str) -> dict:
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
        config = types.GenerateContentConfig(
            tools=tools_list,
            automatic_function_calling=types.AutomaticFunctionCallingConfig(disable=True)
        )
        chat = client.chats.create(model="gemini-1.5-flash", config=config)
        
        response = chat.send_message(
            f"You are a helpful Hollywood production assistant agent. Answer the user's question using the tools available to you. \n\nUser Question: {user_query}"
        )
        
        while response.function_calls:
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
                    
                tool_log.append(f"Observation: {tool_result[:200]}...")
                
                tool_response_part = types.Part.from_function_response(
                    name=func_name,
                    response={"result": tool_result}
                )
                
            response = chat.send_message(tool_response_part)

        tool_log.append("Action: Return final response to user.")
        return {"response": response.text, "tool_log": tool_log}
