import json
import os
import sys

from google_auth_oauthlib.flow import InstalledAppFlow


SCOPES = ["https://www.googleapis.com/auth/drive"]


def main() -> int:
    """
    Generates a Google OAuth refresh token for Drive API access.

    Usage (Windows PowerShell):
      $env:GOOGLE_OAUTH_CLIENT_SECRET_JSON='{"installed":{...}}'
      D:/homeopathy/.venv/Scripts/python.exe tools/get_drive_refresh_token.py

    Or pass a client secret file path:
      D:/homeopathy/.venv/Scripts/python.exe tools/get_drive_refresh_token.py path/to/client_secret.json

    Output:
      Prints values you should copy into Render Environment Variables.
    """

    client_secret_path = sys.argv[1] if len(sys.argv) > 1 else None
    raw = os.getenv("GOOGLE_OAUTH_CLIENT_SECRET_JSON")

    if client_secret_path:
        flow = InstalledAppFlow.from_client_secrets_file(client_secret_path, scopes=SCOPES)
    elif raw:
        data = json.loads(raw)
        flow = InstalledAppFlow.from_client_config(data, scopes=SCOPES)
    else:
        print("Provide GOOGLE_OAUTH_CLIENT_SECRET_JSON env var or a client_secret.json path.")
        return 2

    creds = flow.run_local_server(port=0, prompt="consent")

    if not creds.refresh_token:
        print("ERROR: No refresh token returned. Make sure you used prompt=consent and a fresh consent.")
        return 3

    # Print Render-friendly env vars
    print("GOOGLE_DRIVE_OAUTH_CLIENT_ID=", creds.client_id, sep="")
    print("GOOGLE_DRIVE_OAUTH_CLIENT_SECRET=", creds.client_secret, sep="")
    print("GOOGLE_DRIVE_OAUTH_REFRESH_TOKEN=", creds.refresh_token, sep="")
    print("GOOGLE_DRIVE_OAUTH_TOKEN_URI=", creds.token_uri, sep="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
