from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
import configparser as cp
import os
import json

# Read values from config.conf
config = cp.ConfigParser()
config.read('config.conf')

# Extract data from the DEFAULT section
client_id = config['GOOGLE'].get('CLIENT_ID')
client_secret = config['GOOGLE'].get('CLIENT_SECRET')
project_id = config['GOOGLE'].get('PROJECT_ID')
SCOPES = ['https://www.googleapis.com/auth/drive.file']

#create Credenstials.json
def writeCredentialsJson():
    # Prepare data to be written to credentials.json
    data = {"installed":
            {
                "client_id":client_id,
                "project_id":project_id,
                "auth_uri":"https://accounts.google.com/o/oauth2/auth",
                "token_uri":"https://oauth2.googleapis.com/token",
                "auth_provider_x509_cert_url":"https://www.googleapis.com/oauth2/v1/certs","client_secret":client_secret,
                "redirect_uris":["localhost"]
            }
        }

    # Ensure the directory exists
    os.makedirs('json', exist_ok=True)   

    # Write data to credentials.json
    with open('json/credentials.json', 'w') as json_file:
        json.dump(data, json_file, indent=4)

# Generate token.json
def genTokenJson():
    creds = None
    # The file token.json stores the user's access and refresh tokens, and is
    # created automatically when the authorization flow completes for the first
    # time.
    if os.path.exists('json/token.json'):
        creds = Credentials.from_authorized_user_file('json/token.json', SCOPES)
    # If there are no (valid) credentials available, let the user log in.
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file('json/credentials.json', SCOPES)
            creds = flow.run_local_server(port=0)
        # Save the credentials for the next run
        with open('json/token.json', 'w') as token:
            token.write(creds.to_json())
    return creds