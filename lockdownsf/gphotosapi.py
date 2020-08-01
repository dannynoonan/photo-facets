from __future__ import print_function
import pickle
import os.path
from googleapiclient.discovery import build
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
import ipdb

API_NAME = 'photoslibrary'
API_VERSION = 'v1'
CREDENTIALS_FILE = os.path.join(os.path.dirname(__file__), 'gphotos_credentials.json')
SCOPES = ['https://www.googleapis.com/auth/photoslibrary.readonly']


def init_gphotos_service():
    # credentialsFile = os.path.join(os.path.dirname(__file__), 'gphotos_credentials.json')  # Please set the filename of credentials.json
    pickleFile = 'token.pickle'  # Please set the filename of pickle file.
    
    creds = None
    if os.path.exists(pickleFile):
        with open(pickleFile, 'rb') as token:
            creds = pickle.load(token)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(CREDENTIALS_FILE, SCOPES)
            creds = flow.run_local_server()
        with open(pickleFile, 'wb') as token:
            pickle.dump(creds, token)

    gphotos_service = build(API_NAME, API_VERSION, credentials=creds)

    return gphotos_service


# https://stackoverflow.com/questions/58928685/google-photos-api-python-working-non-deprecated-example
# https://www.youtube.com/watch?v=lj1uzJQnX38
def get_albums(gphotos_service=None):
    if not gphotos_service:
        gphotos_service = init_gphotos_service()

    album_response = gphotos_service.albums().list(fields="albums,nextPageToken", pageSize=10).execute()
    album_items = album_response.get('albums', [])
    albums = []
    if album_items:
        for a_item in album_items:
            photos = get_photos_for_album(a_item['id'], gphotos_service)        
            album = {
                'id': a_item['id'],
                'title': a_item['title'],
                'photos': photos,
            }
            albums.append(album)

    return albums


def get_album(album_id, gphotos_service=None):
    if not gphotos_service:
        gphotos_service = init_gphotos_service()

    album_response = gphotos_service.albums().get(albumId=album_id).execute()

    # ipdb.set_trace()

    album = None
    if album_response:      
        album = {
            'id': album_response['id'],
            'title': album_response['title']
        }

    return album


# https://stackoverflow.com/questions/52565028/mediaitems-search-not-working-with-albumid
def get_photos_for_album(album_id, gphotos_service=None):
    if not gphotos_service:
        gphotos_service = init_gphotos_service()
        
    search_body = {
        "albumId": album_id,
        "pageSize": 10
    }
    media_response = gphotos_service.mediaItems().search(body=search_body).execute()
    photos = []
    media_items = media_response.get('mediaItems', [])
    for m_item in media_items:
        photo = {
            'id': m_item['id'],
            'filename': m_item['filename'],
        }
        photos.append(photo)

    return photos