import os
import streamlit as st
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

# Inject Cinematic CSS Theme
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@300;400;500;600;700&display=swap');

/* Global Font and Backgrounds */
html, body, [class*="css"]  {
    font-family: 'Plus Jakarta Sans', sans-serif !important;
}

.stApp {
    background-color: #05070B !important;
    background-image: radial-gradient(circle at 15% 50%, rgba(107, 33, 168, 0.05), transparent 25%),
                      radial-gradient(circle at 85% 30%, rgba(5, 150, 105, 0.03), transparent 25%);
}

/* Sidebar styling */
[data-testid="stSidebar"] {
    background-color: #0C0F16 !important;
    border-right: 1px solid rgba(255, 255, 255, 0.05);
}

/* Hide default Streamlit headers */
header {visibility: hidden;}
.stDeployButton {display:none;}
#MainMenu {visibility: hidden;}

/* Chat Messages */
[data-testid="stChatMessage"] {
    background: rgba(12, 15, 22, 0.6) !important;
    backdrop-filter: blur(16px);
    -webkit-backdrop-filter: blur(16px);
    border: 1px solid rgba(255, 255, 255, 0.05);
    border-radius: 12px;
    padding: 1rem;
    margin-bottom: 1rem;
    box-shadow: 0 4px 6px rgba(0,0,0,0.3);
}

/* Chat Input Floating Deck */
[data-testid="stChatInput"] {
    background: rgba(12, 15, 22, 0.8) !important;
    border-radius: 30px !important;
    border: 1px solid rgba(255, 255, 255, 0.1) !important;
    box-shadow: 0 25px 50px -12px rgba(0, 0, 0, 0.75) !important;
}

/* Headings and text */
h1, h2, h3, h4, p, span, div {
    color: #e5e7eb !important;
}
</style>
""", unsafe_allow_html=True)
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
        
        extract_props = st.checkbox("Extract Atomic Propositions (Slower)", value=True, help="Disable this for extremely large scripts to speed up ingestion.")
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
                            import time
                            while True:
                                status_res = requests.get(f"{API_BASE_URL}/documents/{st.session_state.session_id}/status", headers=headers)
                                if status_res.status_code == 200:
                                    status_data = status_res.json()
                                    if status_data.get("status") == "indexed":
                                        progress_text.success("Document processed and indexed successfully!")
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
        
        with st.expander("ℹ️ Help & Suggested Questions", expanded=False):
            st.markdown("""
            **How to use the Agent:**
            The SceneIQ agent has access to tools to help answer your questions. It will automatically route your request based on what you ask:
            - **Script Analysis:** For questions about the uploaded screenplay (e.g., characters, plot, scenes), the agent uses `retrieve_from_script`.
            - **Industry Knowledge:** For questions about filmmaking techniques, equipment, or industry standards, the agent uses `parallel_search`.
            - **Producer Tools:** To generate mock storyboards or image prompts for scenes, ask the agent to create a storyboard. It will use `generate_storyboard_tool`.
            - **Writer Tools:** For feedback on pacing, structure, and character arcs, ask the agent to act as a script doctor. It will use `script_doctor_tool`.
            
            **Suggested Questions:**
            - *Who are the main characters and what are their motivations?*
            - *Summarize the events of the climax.*
            - *What are the typical lighting setups for a film noir scene?*
            - *How much does it cost to rent an ARRI Alexa camera?*
            - *Generate a storyboard prompt for the opening scene.*
            - *Act as a script doctor and analyze the pacing of this script using the Hero's Journey framework.*
            """)
        
        # Display chat messages from history inside a scrollable container
        chat_container = st.container(height=500)
        for message in st.session_state.messages:
            with chat_container.chat_message(message["role"]):
                st.markdown(message["content"])
                if message.get("tool_log"):
                    with st.expander("Agent Thought Process", expanded=False):
                        for log in message["tool_log"]:
                            st.text(log)

        col1, col2 = st.columns([0.8, 0.2])
        with col2:
            # Only show retry if the last message was from the user (meaning assistant failed) 
            # or if we just want to let them retry the last query
            if st.session_state.messages and st.session_state.messages[-1]["role"] == "user":
                if st.button("🔄 Retry Last", use_container_width=True):
                    prompt = st.session_state.messages[-1]["content"]
                    st.session_state.messages.pop() # Remove the last user message so we don't duplicate it
                    st.rerun()

        # Accept user input
        if prompt := st.chat_input("Ask a question about the screenplay or filmmaking..."):
            st.session_state.messages.append({"role": "user", "content": prompt})
            with chat_container.chat_message("user"):
                st.markdown(prompt)

            with chat_container.chat_message("assistant"):
                with st.spinner("Thinking..."):
                    try:
                        headers = {"Authorization": f"Bearer {token_data['token']['id_token']}"}
                        payload = {
                            "session_id": st.session_state.session_id,
                            "query": prompt,
                            "system_instruction": "You are a filmmaking expert. Use retrieve_from_script for script info, parallel_search for industry info, generate_storyboard_tool for generating storyboards/image prompts, and script_doctor_tool for script analysis and pacing feedback."
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
                            st.session_state.messages.append({
                                "role": "assistant", 
                                "content": assistant_response,
                                "tool_log": tool_log
                            })
                            st.rerun()
                        else:
                            st.error(f"API Error: {response.text}")
                    except Exception as e:
                        st.error(f"Failed to connect to API. Error: {e}")

    with tab_producers:
        st.header("Filmmakers & Producers Tools")
        
        # Load scenes into session state if they aren't there
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
                    
        selected_scene = None
        if st.session_state.available_scenes:
            selected_scene = st.selectbox("Select a Scene", st.session_state.available_scenes)
            
        if selected_scene:
            if st.button("Generate Script Breakdown (Mock)"):
                with st.spinner("Processing..."):
                    headers = {"Authorization": f"Bearer {token_data['token']['id_token']}"}
                    payload = {"session_id": st.session_state.session_id or "demo", "scene_query": selected_scene}
                    res = requests.post(f"{API_BASE_URL}/tools/producers/breakdown", json=payload, headers=headers)
                    if res.status_code == 200:
                        st.json(res.json())
                    else:
                        st.error("Error calling endpoint")
                        
            if st.button("Generate Storyboard (Mock)"):
                with st.spinner("Generating Image Prompts..."):
                    headers = {"Authorization": f"Bearer {token_data['token']['id_token']}"}
                    payload = {"session_id": st.session_state.session_id or "demo", "scene_query": selected_scene}
                    res = requests.post(f"{API_BASE_URL}/tools/producers/storyboard", json=payload, headers=headers)
                    if res.status_code == 200:
                        data = res.json()
                        st.write(f"**Prompt:** {data.get('image_prompt')}")
                        if data.get("image_base64"):
                            import base64
                            st.image(base64.b64decode(data["image_base64"]))
                        else:
                            st.json(data)
                    else:
                        st.error("Error calling endpoint")

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
