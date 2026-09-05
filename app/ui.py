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
        st.header("Document Ingestion")
        uploaded_file = st.file_uploader("Upload Screenplay", type=["pdf", "txt", "md"])
        
        if uploaded_file is not None:
            if st.button("Process Document"):
                with st.spinner("Uploading document to Google Gemini..."):
                    try:
                        # Optionally attaching the OAuth Bearer token in the headers for security
                        headers = {"Authorization": f"Bearer {token_data['token']['id_token']}"}
                        files = {"file": (uploaded_file.name, uploaded_file.getvalue(), uploaded_file.type)}
                        response = requests.post(f"{API_BASE_URL}/documents", files=files, headers=headers)
                        
                        if response.status_code == 200:
                            data = response.json()
                            st.session_state.session_id = data.get("document_id")
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
                        filmmaking_prompt = """
    You are an expert Hollywood script supervisor, creative producer, and script doctor. 
    Analyze the attached script thoroughly and provide a detailed, professional breakdown 
    divided into the following key production and creative insights:

    ### 1. Logline & Structural Analysis
    * **Logline:** Provide a compelling 1-2 sentence logline for the project.
    * **Pacing & Rhythm:** Map out the narrative momentum (where does it drag, where does it rush?).
    * **Tone & Genre Consistency:** Identify the primary and secondary genres. Note any tonal shifts that feel jarring.

    ### 2. Character Matrix & Casting Insights
    * **Character Breakdown:** Create a markdown table listing all speaking characters, their approximate age, archetypes, and estimated total screen time (High/Medium/Low).
    * **Protagonist Journey:** Summarize the main character's arc, external goal, and internal need.

    ### 3. Production Elements & Budget Driver Breakdown
    * **Location Breakdown:** List all unique locations, categorized by INT vs. EXT, and DAY vs. NIGHT. Highlight the top 3 most frequently used locations.
    * **Cost Drivers:** Flag potentially expensive production elements (e.g., heavy VFX, complex stunts, water scenes, child actors).
    * **Props & Vehicles:** List critical props or vehicles that are central to the plot.

    ### 4. Script Doctoring & Recommendations
    * **Strengths & Weaknesses:** What are the top strongest elements and any noticeable plot holes?
    * **Actionable Next Steps:** Give 3 specific creative recommendations to improve the next draft.
    """
                        headers = {"Authorization": f"Bearer {token_data['token']['id_token']}"}
                        payload = {
                            "session_id": st.session_state.session_id,
                            "query": prompt,
                            "system_instruction": filmmaking_prompt
                        }
                        response = requests.post(f"{API_BASE_URL}/chat", json=payload, headers=headers)
                        
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
