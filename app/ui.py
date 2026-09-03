import streamlit as st
import requests

# Constants
API_BASE_URL = "http://localhost:8000"

st.set_page_config(page_title="SceneIQ MVP", page_icon="🎬", layout="wide")

st.title("🎬 SceneIQ MVP")
st.write("Upload a screenplay (PDF or Text) and ask questions about characters, scenes, and story arcs.")

# Session state initialization
if "session_id" not in st.session_state:
    st.session_state.session_id = None
if "messages" not in st.session_state:
    st.session_state.messages = []

# Sidebar for uploading
with st.sidebar:
    st.header("Document Ingestion")
    uploaded_file = st.file_uploader("Upload Screenplay", type=["pdf", "txt", "md"])
    
    if uploaded_file is not None:
        if st.button("Process Document"):
            with st.spinner("Uploading document to Google Gemini..."):
                try:
                    files = {"file": (uploaded_file.name, uploaded_file.getvalue(), uploaded_file.type)}
                    response = requests.post(f"{API_BASE_URL}/documents", files=files)
                    
                    if response.status_code == 200:
                        data = response.json()
                        st.session_state.session_id = data.get("session_id")
                        st.success(f"Document processed successfully! ({data.get('chunks_count')} chunks ingested to BigQuery)")
                        # Clear chat history when new document is uploaded
                        st.session_state.messages = []
                    else:
                        st.error(f"Error: {response.text}")
                except Exception as e:
                    st.error(f"Failed to connect to API. Is it running? Error: {e}")

# Chat interface
st.header("SceneIQ Chat")

if st.session_state.session_id:
    # Display chat messages from history
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

    # Accept user input
    if prompt := st.chat_input("Ask a question about the screenplay..."):
        # Add user message to chat history
        st.session_state.messages.append({"role": "user", "content": prompt})
        
        # Display user message
        with st.chat_message("user"):
            st.markdown(prompt)

        # Generate and display assistant response
        with st.chat_message("assistant"):
            with st.spinner("Analyzing screenplay..."):
                try:
                    payload = {
                        "session_id": st.session_state.session_id,
                        "query": prompt
                    }
                    response = requests.post(f"{API_BASE_URL}/chat", json=payload)
                    
                    if response.status_code == 200:
                        data = response.json()
                        assistant_response = data.get("response", "Error: No response generated.")
                        tool_log = data.get("tool_log", [])
                        
                        # Show tool execution process
                        if tool_log:
                            with st.expander("Agent Thought Process", expanded=False):
                                for log in tool_log:
                                    st.text(log)
                                    
                        st.markdown(assistant_response)
                        
                        # Add assistant message to chat history
                        st.session_state.messages.append({"role": "assistant", "content": assistant_response})
                    else:
                        st.error(f"API Error: {response.text}")
                except Exception as e:
                    st.error(f"Failed to connect to API. Is it running? Error: {e}")
else:
    st.info("Please upload and process a screenplay in the sidebar to begin chatting.")
