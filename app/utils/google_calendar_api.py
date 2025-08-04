# app/utils/google_calendar_api.py

import os
import pickle
from google_auth_oauthlib.flow import Flow
from google.auth.transport.requests import Request as GoogleAuthRequest
from googleapiclient.discovery import build
from datetime import datetime, timedelta
import pytz
import requests # Diperlukan untuk revoke_google_access

# Import konstanta Google dari config dan client ID/secret dari data_manager
from app.utils.config import GOOGLE_SCOPES, GOOGLE_TOKEN_DIR, TZ, GOOGLE_REDIRECT_URI
from app.utils.data_manager import GOOGLE_CLIENT_ID, GOOGLE_CLIENT_SECRET

# ===============================
# Google Calendar API Manager
# ===============================

def _get_google_credentials_path(user_id: int) -> str:
    """Mengembalikan path ke file kredensial Google untuk user tertentu."""
    os.makedirs(GOOGLE_TOKEN_DIR, exist_ok=True)
    return os.path.join(GOOGLE_TOKEN_DIR, f"token_{user_id}.pickle")

def get_google_service(user_id: int):
    """
    Mendapatkan service Google Calendar API untuk user tertentu.
    Akan memuat kredensial dari file jika ada dan valid, atau None jika otentikasi diperlukan.
    """
    creds = None
    token_path = _get_google_credentials_path(user_id)

    if os.path.exists(token_path):
        try:
            with open(token_path, 'rb') as token:
                creds = pickle.load(token)
        except (EOFError, pickle.UnpicklingError):
            # File kosong atau korup, hapus dan anggap tidak ada token
            os.remove(token_path)
            creds = None
            print(f"Corrupted or empty Google token file for user {user_id} removed.")


    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            try:
                creds.refresh(GoogleAuthRequest())
                with open(token_path, 'wb') as token:
                    pickle.dump(creds, token)
                print(f"Google token for user {user_id} refreshed and saved.")
            except Exception as e:
                print(f"Error refreshing Google token for user {user_id}: {e}")
                return None # Gagal refresh
        else:
            print(f"Google token for user {user_id} not found or invalid. Authentication required.")
            return None # Perlu otentikasi baru

    if creds:
        try:
            service = build('calendar', 'v3', credentials=creds)
            return service
        except Exception as e:
            print(f"Error building Google Calendar service for user {user_id}: {e}")
            return None
    return None

def generate_auth_url_for_user(user_id: int) -> str:
    """
    Menghasilkan URL otorisasi Google untuk user tertentu.
    User_id akan disematkan sebagai parameter 'state' di URL.
    """
    # Debug print ini akan menunjukkan apakah GOOGLE_REDIRECT_URI memiliki nilai None
    # print(f"DEBUG: GOOGLE_REDIRECT_URI value: {GOOGLE_REDIRECT_URI}") # Untuk debugging jika diperlukan

    flow_config = {
        "web": { # Kita menggunakan jenis "Web application" di Google Cloud Console
            "client_id": GOOGLE_CLIENT_ID,
            "client_secret": GOOGLE_CLIENT_SECRET,
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://oauth2.googleapis.com/token",
            "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
            "redirect_uris": [GOOGLE_REDIRECT_URI]
        }
    }
    
    flow = Flow.from_client_config(flow_config, scopes=GOOGLE_SCOPES, state=str(user_id))
    flow.redirect_uri = GOOGLE_REDIRECT_URI # Pastikan redirect_uri disetel
    
    # Menghasilkan URL otorisasi. access_type='offline' penting untuk mendapatkan refresh_token
    # include_granted_scopes='true' dihapus untuk menghindari konflik scope
    authorization_url, _ = flow.authorization_url(access_type='offline')
    
    return authorization_url

def save_google_token_from_callback(user_id: int, auth_code: str):
    """
    Menukar kode otorisasi dari Google dengan token dan menyimpannya.
    Ini dipanggil oleh web server Flask setelah menerima callback.
    """
    flow_config = {
        "web": {
            "client_id": GOOGLE_CLIENT_ID,
            "client_secret": GOOGLE_CLIENT_SECRET,
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://oauth2.googleapis.com/token",
            "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
            "redirect_uris": [GOOGLE_REDIRECT_URI]
        }
    }
    
    flow = Flow.from_client_config(flow_config, scopes=GOOGLE_SCOPES, state=str(user_id))
    flow.redirect_uri = GOOGLE_REDIRECT_URI
    
    creds = flow.fetch_token(code=auth_code) # Menukar kode dengan token
    
    # Simpan kredensial
    with open(_get_google_credentials_path(user_id), 'wb') as token_file:
        pickle.dump(creds, token_file)
    
    return True

def revoke_google_access(user_id: int):
    """Menghapus token Google yang tersimpan untuk user tertentu."""
    token_path = _get_google_credentials_path(user_id)
    if os.path.exists(token_path):
        try:
            with open(token_path, 'rb') as token_file:
                creds = pickle.load(token_file)
            if creds and creds.token: # Coba cabut token dari Google
                requests.post('https://oauth2.googleapis.com/revoke',
                              params={'token': creds.token},
                              headers={'content-type': 'application/x-www-form-urlencoded'})
            os.remove(token_path)
            print(f"Google token for user {user_id} revoked and deleted locally.")
            return True
        except Exception as e:
            print(f"Error revoking/deleting Google token for user {user_id}: {e}")
            return False
    return False


async def create_google_event(service, event_data: dict, calendar_id='primary'):
    """Membuat event di Google Calendar."""
    try:
        event = service.events().insert(calendarId=calendar_id, body=event_data).execute()
        print(f"Google event created: {event.get('htmlLink')}")
        return event.get('id') # Mengembalikan Google Event ID
    except Exception as e:
        print(f"Error creating Google Calendar event: {e}")
        return None

async def update_google_event(service, google_event_id: str, event_data: dict, calendar_id='primary'):
    """Mengupdate event di Google Calendar."""
    try:
        event = service.events().update(calendarId=calendar_id, eventId=google_event_id, body=event_data).execute()
        print(f"Google event updated: {event.get('htmlLink')}")
        return True
    except Exception as e:
        print(f"Error updating Google Calendar event (ID: {google_event_id}): {e}")
        return False

async def delete_google_event(service, google_event_id: str, calendar_id='primary'):
    """Menghapus event dari Google Calendar."""
    try:
        service.events().delete(calendarId=calendar_id, eventId=google_event_id).execute()
        print(f"Google event deleted: {google_event_id}")
        return True
    except Exception as e:
        print(f"Error deleting Google Calendar event (ID: {google_event_id}): {e}")
        return False

async def get_google_events(service, time_min: datetime, time_max: datetime, calendar_id='primary'):
    """Mendapatkan event dari Google Calendar dalam rentang waktu tertentu."""
    try:
        # Pastikan datetime objects adalah timezone-aware
        if time_min.tzinfo is None:
            time_min = TZ.localize(time_min)
        if time_max.tzinfo is None:
            time_max = TZ.localize(time_max)

        events_result = service.events().list(
            calendarId=calendar_id,
            timeMin=time_min.isoformat(), # Sudah TZ-aware, jadi tidak perlu 'Z'
            timeMax=time_max.isoformat(), # Sudah TZ-aware, jadi tidak perlu 'Z'
            singleEvents=True,
            orderBy='startTime'
        ).execute()
        events = events_result.get('items', [])
        return events
    except Exception as e:
        print(f"Error getting Google Calendar events: {e}")
        return []
