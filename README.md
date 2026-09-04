# SceneIQ

SceneIQ is an agentic screenplay intelligence platform designed to convert screenplays and production documents into searchable, grounded, and actionable production knowledge.

## Features
- **Natural Language Queries:** Ask questions about characters, scenes, locations, story arcs, and complexity.
- **Agentic Reasoning:** Utilizes Google Gemini and the Google Agent Development Kit (ADK) for intelligent orchestration and multi-agent pipelines.
- **Live Web Context:** Runtime integration with the Parallel Search API ensures grounded, up-to-date external references.
- **Custom Retrieval Layer:** Highly optimized extraction of screenplay variables.

## Tech Stack
- Google Gemini 
- Google Agent Development Kit (ADK)
- Parallel Search API
- Python

## Getting Started
1. Clone the repository: `git clone https://github.com/Saurabh331/SceneIQ.git`
2. Install dependencies: `pip install -r requirements.txt`
3. Set up your environment variables for Gemini and Parallel Search.

## Authentication Setup (Google OAuth)

SceneIQ uses a unified OAuth flow to authenticate with Gemini, Vertex AI, and BigQuery. You must configure your `.env` file with Google OAuth credentials.

### Step 1: Create OAuth Credentials
1. Go to the [Google Cloud Console](https://console.cloud.google.com/).
2. Navigate to **APIs & Services** > **OAuth consent screen** and configure it (External or Internal).
3. Navigate to **APIs & Services** > **Credentials**.
4. Click **+ CREATE CREDENTIALS** > **OAuth client ID**.
5. Set Application type to **Desktop app** and create.
6. Copy the **Client ID** and **Client Secret** into your `.env` file as `GOOGLE_CLIENT_ID` and `GOOGLE_CLIENT_SECRET`.

### Step 2: Generate a Refresh Token
1. Go to the [Google OAuth 2.0 Playground](https://developers.google.com/oauthplayground/).
2. Click the **Gear icon** ⚙️, check **"Use your own OAuth credentials"**, and paste your Client ID and Secret.
3. In Step 1, input the scope: `https://www.googleapis.com/auth/cloud-platform`
4. Click **Authorize APIs** and log in with your Google account.
5. In Step 2, click **Exchange authorization code for tokens**.
6. Copy the **Refresh token** into your `.env` file as `GOOGLE_REFRESH_TOKEN`.

## Running the Application

You will need to run the backend API and the frontend UI in separate terminals.

1. **Start the API Server**:
   ```bash
   uvicorn api.main:app --reload
   ```

2. **Start the Streamlit UI**:
   ```bash
   streamlit run app/ui.py
   ```

3. Open the provided Local URL in your browser, upload a screenplay, and start chatting!
