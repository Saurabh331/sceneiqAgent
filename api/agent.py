import os
import json
import google.generativeai as genai
from dotenv import load_dotenv

from .rag import retrieve_chunks

load_dotenv()

# Check for API key
API_KEY = os.getenv("GEMINI_API_KEY")
if API_KEY and API_KEY != "mock":
    genai.configure(api_key=API_KEY)
    MOCK_MODE = False
else:
    MOCK_MODE = True

def search_screenplay(session_id: str, query: str) -> str:
    """
    Retrieves information from the uploaded screenplay document to answer questions about the story, characters, and scenes.
    """
    chunks = retrieve_chunks(session_id, query)
    if not chunks:
        return "No relevant context found in the screenplay."
    return "\n\n---\n\n".join(chunks[:3])

def parallel_search(query: str) -> str:
    """
    Performs a web search to find external production context, industry trends, and budget constraints.
    Use this tool when the question requires information outside of the script (e.g., current real-world data).
    """
    # MOCK implementation of Parallel Search API
    return f"Mocked Web Search Results for '{query}': According to recent production data, similar requirements typically incur a 15% budget premium due to 2026 industry standards and union rules."

def process_agentic_chat(session_id: str, user_query: str) -> dict:
    """
    Main orchestration loop for the agent using Gemini Tool Calling.
    Returns the response and a log of the tools used.
    """
    # Since we can't easily pass the session_id directly into the tool function signature that Gemini calls 
    # without making it a required parameter for the LLM to guess, we'll wrap it in a lambda or local function.
    # However, Gemini function calling requires type hints and docstrings.
    
    # Define a custom tool for Gemini that inherently knows the session_id
    def retrieve_from_script(query: str) -> str:
        """
        Retrieves information from the uploaded screenplay document.
        Always use this tool first when asked about the script's contents.
        
        Args:
            query: The specific question or topic to search for in the script.
        """
        return search_screenplay(session_id, query)

    # Dictionary mapping function names to actual functions for execution
    available_tools = {
        "retrieve_from_script": retrieve_from_script,
        "parallel_search": parallel_search
    }

    tools_list = [retrieve_from_script, parallel_search]
    tool_log = []

    if MOCK_MODE:
        # Simulate Agentic behavior if no valid API key is present
        tool_log.append("Executing Agentic Loop (MOCK MODE)")
        
        # Decide which tool to use based on naive keywords
        if "budget" in user_query.lower() or "cost" in user_query.lower() or "real world" in user_query.lower():
            tool_log.append(f"Action: Call 'parallel_search' with query '{user_query}'")
            context = parallel_search(user_query)
        else:
            tool_log.append(f"Action: Call 'retrieve_from_script' with query '{user_query}'")
            context = retrieve_from_script(user_query)
            
        tool_log.append(f"Observation: {context[:100]}...")
        
        final_answer = (
            f"Based on the agent's research, here is the answer: \n\n"
            f"If you're asking about the script, we found relevant excerpts. "
            f"If you're asking about production, we consulted the web. "
            f"\n\nContext found: {context[:300]}..."
        )
        return {"response": final_answer, "tool_log": tool_log}

    else:
        # Actual Gemini Agent Orchestration
        model = genai.GenerativeModel(
            model_name="gemini-1.5-flash", 
            tools=tools_list
        )
        
        chat = model.start_chat(enable_automatic_function_calling=False)
        
        response = chat.send_message(
            f"You are a helpful Hollywood production assistant agent. Answer the user's question using the tools available to you. \n\nUser Question: {user_query}"
        )
        
        # Manually handle tool calls to log them
        while response.function_call:
            func_name = response.function_call.name
            args = type(response.function_call).to_dict(response.function_call).get('args', {})
            
            tool_log.append(f"Action: Call '{func_name}' with args: {args}")
            
            if func_name in available_tools:
                tool_func = available_tools[func_name]
                try:
                    tool_result = tool_func(**args)
                except Exception as e:
                    tool_result = f"Error executing tool: {e}"
            else:
                tool_result = f"Error: Tool {func_name} not found."
                
            tool_log.append(f"Observation: {tool_result[:100]}...")
            
            # Send the observation back to the model
            response = chat.send_message(
                genai.protos.Part(
                    function_response=genai.protos.FunctionResponse(
                        name=func_name,
                        response={"result": tool_result}
                    )
                )
            )

        tool_log.append("Action: Return final response to user.")
        return {"response": response.text, "tool_log": tool_log}
