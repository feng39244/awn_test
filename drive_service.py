from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from google.auth.transport.requests import Request as GoogleRequest
from google.oauth2.credentials import Credentials
import os
import pickle

# Configuration
SCOPES = ['https://www.googleapis.com/auth/drive.readonly']
CREDENTIALS_FILE = 'credentials.json'
TOKEN_FILE = 'token.pickle'

def get_drive_service():
    """
    Authenticate and return a Google Drive API service instance.
    """
    creds = None
    # Load existing credentials if they exist
    if os.path.exists(TOKEN_FILE):
        with open(TOKEN_FILE, 'rb') as token:
            creds = pickle.load(token)
    
    # Refresh or authenticate if credentials are invalid or missing
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(GoogleRequest())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(CREDENTIALS_FILE, SCOPES)
            creds = flow.run_local_server(port=0)
        # Save the credentials for future use
        with open(TOKEN_FILE, 'wb') as token:
            pickle.dump(creds, token)
    
    # Build and return the Drive API service
    return build('drive', 'v3', credentials=creds)

def list_files(service, filter_name="patient"):
    """
    List files from Google Drive filtered by name.
    
    Args:
        service: Google Drive API service instance
        filter_name: String to filter file names (default: "patient")
    
    Returns:
        List of file metadata dictionaries
    """
    query = f"'{filter_name}' in name"
    results = service.files().list(
        q=query,
        pageSize=10,
        fields="nextPageToken, files(id, name, mimeType, webViewLink)"
    ).execute()
    return results.get('files', [])

def main():
    """Test the Google Drive service by listing files with a name filter."""
    try:
        # Get the Drive service
        service = get_drive_service()
        
        # List files filtered by "patient" (or change as needed)
        filter_name = "patient"
        files = list_files(service, filter_name)
        
        # Print results
        if not files:
            print(f"No files found matching '{filter_name}'.")
        else:
            print(f"Files matching '{filter_name}':")
            print("-" * 50)
            for file in files:
                print(f"Name: {file['name']}")
                print(f"ID: {file['id']}")
                print(f"MIME Type: {file['mimeType']}")
                print(f"Link: {file['webViewLink']}")
                print("-" * 50)
    except Exception as e:
        print(f"An error occurred: {e}")

if __name__ == "__main__":
    main()