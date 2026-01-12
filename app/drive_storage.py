import io
import json
import os
from dataclasses import dataclass
from typing import IO, Any, Dict, Optional, Tuple

from google.oauth2 import service_account
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseUpload
from google.auth.transport.requests import AuthorizedSession


DRIVE_SCOPES = ["https://www.googleapis.com/auth/drive"]


class DriveConfigError(RuntimeError):
    pass


def _load_service_account_info() -> Dict[str, Any]:
    raw = os.getenv("GOOGLE_SERVICE_ACCOUNT_JSON")
    if not raw:
        raise DriveConfigError("GOOGLE_SERVICE_ACCOUNT_JSON is not set")

    try:
        return json.loads(raw)
    except json.JSONDecodeError as exc:
        raise DriveConfigError("GOOGLE_SERVICE_ACCOUNT_JSON is not valid JSON") from exc


def _load_oauth_credentials() -> Optional[Credentials]:
    client_id = (os.getenv("GOOGLE_DRIVE_OAUTH_CLIENT_ID") or "").strip()
    client_secret = (os.getenv("GOOGLE_DRIVE_OAUTH_CLIENT_SECRET") or "").strip()
    refresh_token = (os.getenv("GOOGLE_DRIVE_OAUTH_REFRESH_TOKEN") or "").strip()
    token_uri = (os.getenv("GOOGLE_DRIVE_OAUTH_TOKEN_URI") or "https://oauth2.googleapis.com/token").strip()

    if not (client_id and client_secret and refresh_token):
        return None

    return Credentials(
        token=None,
        refresh_token=refresh_token,
        token_uri=token_uri,
        client_id=client_id,
        client_secret=client_secret,
        scopes=DRIVE_SCOPES,
    )


def get_drive_credentials():
    oauth_creds = _load_oauth_credentials()
    if oauth_creds is not None:
        return oauth_creds

    info = _load_service_account_info()
    return service_account.Credentials.from_service_account_info(info, scopes=DRIVE_SCOPES)


def get_drive_service():
    creds = get_drive_credentials()
    return build("drive", "v3", credentials=creds, cache_discovery=False)


def get_authorized_session() -> AuthorizedSession:
    creds = get_drive_credentials()
    return AuthorizedSession(creds)


@dataclass(frozen=True)
class DriveFile:
    file_id: str
    name: str
    mime_type: str
    size_bytes: Optional[int]


class GoogleDriveStorage:
    def __init__(self, parent_folder_id: str):
        if not parent_folder_id:
            raise DriveConfigError("GOOGLE_DRIVE_PARENT_FOLDER_ID is not set")
        self.parent_folder_id = parent_folder_id
        self._service = None

    @property
    def service(self):
        if self._service is None:
            self._service = get_drive_service()
        return self._service

    def get_or_create_folder(self, *, parent_id: str, name: str) -> str:
        query = (
            "mimeType='application/vnd.google-apps.folder' "
            "and trashed=false "
            f"and name='{name.replace("'", "\\'")}' "
            f"and '{parent_id}' in parents"
        )
        res = self.service.files().list(q=query, fields="files(id,name)", pageSize=1).execute()
        files = res.get("files", [])
        if files:
            return files[0]["id"]

        created = (
            self.service.files()
            .create(
                body={
                    "name": name,
                    "mimeType": "application/vnd.google-apps.folder",
                    "parents": [parent_id],
                },
                fields="id",
            )
            .execute()
        )
        return created["id"]

    def ensure_patient_and_consultation_folders(self, *, patient_folder_name: str, consultation_id: int) -> Tuple[str, str]:
        patient_folder_id = self.get_or_create_folder(parent_id=self.parent_folder_id, name=patient_folder_name)
        consultation_folder_id = self.get_or_create_folder(parent_id=patient_folder_id, name=str(consultation_id))
        return patient_folder_id, consultation_folder_id

    def upload_file(self, *, folder_id: str, filename: str, mime_type: str, fileobj: IO[bytes]) -> DriveFile:
        safe_mime = mime_type or "application/octet-stream"
        media = MediaIoBaseUpload(fileobj, mimetype=safe_mime, resumable=True)
        created = (
            self.service.files()
            .create(
                body={"name": filename, "parents": [folder_id]},
                media_body=media,
                fields="id,name,mimeType,size",
            )
            .execute()
        )
        size_raw = created.get("size")
        size_val = int(size_raw) if size_raw is not None else None
        return DriveFile(
            file_id=created["id"],
            name=created.get("name") or filename,
            mime_type=created.get("mimeType") or safe_mime,
            size_bytes=size_val,
        )

    def delete_file_permanently(self, *, file_id: str) -> None:
        self.service.files().delete(fileId=file_id).execute()


def classify_media_type(mime_type: str) -> str:
    mt = (mime_type or "").lower()
    if mt.startswith("image/"):
        return "image"
    if mt.startswith("audio/"):
        return "audio"
    if mt.startswith("video/"):
        return "video"
    return "other"
