import os
import streamlit as st
import time
import requests
from streamlit_oauth import OAuth2Component
from dotenv import load_dotenv

# Load local environment variables (.env file)
load_dotenv()

# Constants
API_BASE_URL = "http://localhost:8000"
CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID")
CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET")
AUTHORIZE_URL = "https://accounts.google.com/o/oauth2/v2/auth"
TOKEN_URL = "https://oauth2.googleapis.com/token"
REVOKE_URL = "https://oauth2.googleapis.com/revoke"

st.set_page_config(page_title="SceneIQ MVP", page_icon="🎬", layout="wide")

# Initialize the Streamlit OAuth Component
oauth2 = OAuth2Component(
    client_id=CLIENT_ID,
    client_secret=CLIENT_SECRET,
    authorize_endpoint=AUTHORIZE_URL,
    token_endpoint=TOKEN_URL,
    refresh_token_endpoint=TOKEN_URL
)

# Check if the user is already authenticated
if "auth" not in st.session_state:
    st.title("SceneIQ Agent 🤖")
    st.subheader("Login to access the SceneIQ Agent")
    st.write("Please authenticate with your Google Account to proceed.")
    
    # Render the native login button
    result = oauth2.authorize_button(
        name="Continue with Google",
        redirect_uri="http://localhost:8501/",
        scope="openid email profile",
        key="google_auth",
        use_container_width=True
    )
    
    if result:
        # Save the token and profile credentials to session state
        st.session_state["auth"] = result
        st.rerun()

else:
    # 🔓 User is authenticated. Display the main dashboard.
    token_data = st.session_state["auth"]
    
    # Optional: Extract user details from ID Token if available in library response
    user_email = token_data.get("token", {}).get("email", "Authenticated User")
    
    st.sidebar.write(f"Logged in as: {user_email}")
    
    # Add a logout button
    if st.sidebar.button("Logout"):
        del st.session_state["auth"]
        st.rerun()

    st.title("🎬 SceneIQ MVP")
    st.write("Upload a screenplay (PDF or Text) and ask questions about characters, scenes, and story arcs.")

    # Session state initialization
    if "session_id" not in st.session_state:
        st.session_state.session_id = None
    if "messages" not in st.session_state:
        st.session_state.messages = []

    # Sidebar for uploading
    with st.sidebar:
        st.divider()
        if st.button("Clear Chat Context", use_container_width=True):
            st.session_state.messages = []
            st.rerun()
        st.header("Document Ingestion")
        uploaded_file = st.file_uploader("Upload Screenplay", type=["pdf", "txt", "md"])
        
        extract_props = st.checkbox("Extract Atomic Propositions (Slower, High Cost)", value=True, help="Disable this for extremely large scripts to speed up ingestion.")
        model_choice = st.radio("Select Embedding Model", ["Vertex AI (Small Documents)", "Hugging Face (Large Documents)"])
        embedding_type = "vertexai" if "Vertex AI" in model_choice else "huggingface"
        
        if uploaded_file is not None:
            if st.button("Process Document"):
                with st.spinner("Uploading and processing document..."):
                    try:
                        headers = {"Authorization": f"Bearer {token_data['token']['id_token']}"}
                        files = {"file": (uploaded_file.name, uploaded_file.getvalue(), uploaded_file.type)}
                        data = {
                            "extract_props": "true" if extract_props else "false",
                            "embedding_type": embedding_type
                        }
                        response = requests.post(f"{API_BASE_URL}/documents", files=files, data=data, headers=headers)
                        
                        if response.status_code == 200:
                            resp_data = response.json()
                            st.session_state.session_id = resp_data.get("document_id")
                            
                            progress_text = st.empty()
                            while True:
                                status_res = requests.get(f"{API_BASE_URL}/documents/{st.session_state.session_id}/status", headers=headers)
                                if status_res.status_code == 200:
                                    status_data = status_res.json()
                                    if status_data.get("status") == "indexed":
                                        progress_text.success("Document processed and indexed successfully!")
                                        st.session_state.messages = []
                                        break
                                    elif status_data.get("status") == "failed":
                                        progress_text.error("Document ingestion failed.")
                                        break
                                    else:
                                        progress_text.info("Processing in background... please wait.")
                                else:
                                    progress_text.warning("Checking status...")
                                time.sleep(3)
                        else:
                            st.error(f"Error: {response.text}")
                    except Exception as e:
                        st.error(f"Failed to connect to API. Is it running? Error: {e}")

    # Main Interface Tabs
    tab_chat, tab_producers, tab_writers, tab_enthusiasts = st.tabs(["💬 Chat", "🎬 Producers", "✍️ Writers", "🍿 Enthusiasts"])

    with tab_chat:
        st.header("SceneIQ Chat")
        
        # Display chat messages from history
        for message in st.session_state.messages:
            with st.chat_message(message["role"]):
                st.markdown(message["content"])

        # Accept user input
        if prompt := st.chat_input("Ask a question about the screenplay or filmmaking..."):
            st.session_state.messages.append({"role": "user", "content": prompt})
            with st.chat_message("user"):
                st.markdown(prompt)

            with st.chat_message("assistant"):
                with st.spinner("Thinking..."):
                    try:
                        headers = {"Authorization": f"Bearer {token_data['token']['id_token']}"}
                        payload = {
                            "session_id": st.session_state.session_id,
                            "query": prompt,
                            "system_instruction": "You are a filmmaking expert. Use retrieve_from_script for script info and parallel_search for industry info."
                        }
                        response = requests.post(f"{API_BASE_URL}/chat", json=payload, headers=headers)
                        
                        if response.status_code == 200:
                            data = response.json()
                            assistant_response = data.get("response", "Error: No response generated.")
                            tool_log = data.get("tool_log", [])
                            
                            if tool_log:
                                with st.expander("Agent Thought Process", expanded=False):
                                    for log in tool_log:
                                        st.text(log)
                                        
                            st.markdown(assistant_response)
                            st.session_state.messages.append({"role": "assistant", "content": assistant_response})
                        else:
                            st.error(f"API Error: {response.text}")
                    except Exception as e:
                        st.error(f"Failed to connect to API. Error: {e}")

    with tab_producers:
        st.header("Filmmakers & Producers Tools")
        if st.button("Generate Script Breakdown (Mock)"):
            with st.spinner("Processing..."):
                headers = {"Authorization": f"Bearer {token_data['token']['id_token']}"}
                payload = {"session_id": st.session_state.session_id or "demo", "scene_query": "Act 1"}
                res = requests.post(f"{API_BASE_URL}/tools/producers/breakdown", json=payload, headers=headers)
                if res.status_code == 200:
                    st.json(res.json())
                else:
                    st.error("Error calling endpoint")
                    
        st.subheader("Batch Storyboard Generation")
        if "available_scenes" not in st.session_state:
            st.session_state.available_scenes = []
            
        if st.button("Load Scenes"):
            with st.spinner("Extracting scenes..."):
                headers = {"Authorization": f"Bearer {token_data['token']['id_token']}"}
                sess_id = st.session_state.session_id or "demo"
                res = requests.get(f"{API_BASE_URL}/tools/producers/scenes?session_id={sess_id}", headers=headers)
                if res.status_code == 200:
                    st.session_state.available_scenes = res.json().get("scenes", [])
                    st.success(f"Found {len(st.session_state.available_scenes)} scenes.")
                else:
                    st.error("Failed to load scenes.")
                    
        if st.session_state.available_scenes:
            selected_scenes = st.multiselect("Select Scenes", st.session_state.available_scenes, default=st.session_state.available_scenes)
            
            if st.button("Generate Storyboards Document"):
                if not selected_scenes:
                    st.warning("Please select at least one scene.")
                else:
                    headers = {"Authorization": f"Bearer {token_data['token']['id_token']}"}
                    payload = {"session_id": st.session_state.session_id or "demo", "scenes": selected_scenes}
                    res = requests.post(f"{API_BASE_URL}/tools/producers/storyboard/batch", json=payload, headers=headers)
                    if res.status_code == 200:
                        task_id = res.json().get("task_id")
                        st.info("Task submitted! Generating in background...")
                        
                        progress_bar = st.progress(0)
                        status_text = st.empty()
                        
                        while True:
                            status_res = requests.get(f"{API_BASE_URL}/tools/producers/storyboard/status/{task_id}", headers=headers)
                            if status_res.status_code == 200:
                                status_data = status_res.json()
                                stat = status_data.get("status")
                                prog = status_data.get("progress", 0)
                                total = status_data.get("total", len(selected_scenes))
                                
                                progress_val = prog / total if total > 0 else 0
                                progress_bar.progress(progress_val)
                                status_text.write(f"Status: {stat} ({prog}/{total})")
                                
                                if stat == "completed":
                                    url = status_data.get("url")
                                    if url and url.startswith("/"):
                                        url = f"{API_BASE_URL}{url}"
                                    st.success("Generation Complete!")
                                    st.markdown(f"[**Download Storyboard PDF here**]({url})")
                                    break
                                elif stat == "failed":
                                    st.error("Task failed.")
                                    break
                            time.sleep(2)
                    else:
                        st.error("Failed to submit batch generation task.")

    with tab_writers:
        st.header("Writers & Script Editors Tools")
        if st.button("Run Script Doctor (Mock)"):
            with st.spinner("Analyzing Pacing..."):
                headers = {"Authorization": f"Bearer {token_data['token']['id_token']}"}
                payload = {"session_id": st.session_state.session_id or "demo", "framework": "Hero's Journey"}
                res = requests.post(f"{API_BASE_URL}/tools/writers/script_doctor", json=payload, headers=headers)
                if res.status_code == 200:
                    st.json(res.json())

    with tab_enthusiasts:
        st.header("Film Enthusiasts Tools")
        if st.button("Cinematic Deep Research (Mock)"):
            with st.spinner("Synthesizing..."):
                headers = {"Authorization": f"Bearer {token_data['token']['id_token']}"}
                payload = {"session_id": st.session_state.session_id or "demo", "query": "Themes of betrayal in Act 2"}
                res = requests.post(f"{API_BASE_URL}/tools/enthusiasts/research", json=payload, headers=headers)
                if res.status_code == 200:
                    st.json(res.json())
