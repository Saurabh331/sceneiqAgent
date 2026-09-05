import os
import google.auth
from google.auth.transport import requests as google_requests
from google.oauth2 import id_token
from fastapi import HTTPException, Security
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

oauth2_scheme = HTTPBearer()

def verify_user_token(credentials: HTTPAuthorizationCredentials = Security(oauth2_scheme)) -> dict:
    """
    Verifies the Google OAuth2 id_token sent by the frontend in the Authorization header.
    Returns the decoded token payload if valid.
    """
    token = credentials.credentials
    client_id = os.getenv("GOOGLE_CLIENT_ID")
    
    try:
        # Verify the token against Google's public certificates
        request = google_requests.Request()
        id_info = id_token.verify_oauth2_token(token, request, client_id)
        
        # Verify the issuer.
        if id_info['iss'] not in ['accounts.google.com', 'https://accounts.google.com']:
            raise ValueError('Wrong issuer.')
            
        return id_info
    except ValueError as e:
        raise HTTPException(status_code=401, detail=f"Invalid token: {e}")

def get_google_credentials():
    """
    Retrieves Google Cloud credentials using Application Default Credentials (ADC).
    """
    try:
        credentials, project = google.auth.default(scopes=["https://www.googleapis.com/auth/cloud-platform"])
        return credentials
    except Exception as e:
        print(f"Warning: Could not get default credentials. {e}")
        return None
