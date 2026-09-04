import os
from google.oauth2.credentials import Credentials

def get_google_credentials() -> Credentials:
    """
    Constructs Google OAuth2 Credentials using refresh token and client secrets
    provided via environment variables.
    """
    client_id = os.getenv("GOOGLE_CLIENT_ID")
    client_secret = os.getenv("GOOGLE_CLIENT_SECRET")
    refresh_token = os.getenv("GOOGLE_REFRESH_TOKEN")
    
    if not client_id or not client_secret or not refresh_token:
        # Fallback to None (ADC) if any are missing, or you could raise an error here.
        # But for robustness we'll just log and let ADC handle it if they aren't fully set up yet.
        print("Warning: Missing one or more OAuth credentials in environment (GOOGLE_CLIENT_ID, GOOGLE_CLIENT_SECRET, GOOGLE_REFRESH_TOKEN).")
        return None
        
    return Credentials(
        token=None,
        refresh_token=refresh_token,
        token_uri="https://oauth2.googleapis.com/token",
        client_id=client_id,
        client_secret=client_secret,
        scopes=["https://www.googleapis.com/auth/cloud-platform"]
    )
