# import os 
# import pickle
# import json
# from googleapiclient.discovery import build
# from google.auth.transport.requests import Request
# from google_auth_oauthlib.flow import InstalledAppFlow
# import google_auth_httplib2  # This gotta be installed for build() to work

# https://github.com/ido-ran/google-photos-api-python-quickstart/blob/master/quickstart.py
# def run_things():
#     # Setup the Photo v1 API
#     SCOPES = ['https://www.googleapis.com/auth/photoslibrary.readonly']
#     creds = None
#     if (os.path.exists("token.pickle")):
#         print('token.pickle exists!')
#         with open("token.pickle", "rb") as tokenFile:
#             print('attempt to map tokenFile to creds')
#             creds = pickle.load(tokenFile)
#     else:
#         print('token.pickle DOES NOT EXIST')
#     if not creds or not creds.valid:
#         if (creds and creds.expired and creds.refresh_token):
#             print('creds and creds.expired and creds.refresh_token')
#             creds.refresh(Request())
#         else:
#             print('NOT creds and creds.expired and creds.refresh_token')
#             flow = InstalledAppFlow.from_client_secrets_file('client_secret.json', SCOPES)
#             creds = flow.run_local_server(port = 0)
#         with open("token.pickle", "wb") as tokenFile:
#             pickle.dump(creds, tokenFile)
#     service = build('photoslibrary', 'v1', credentials = creds)

#     # Call the Photo v1 API
#     results = service.albums().list(
#         pageSize=10, fields="nextPageToken,albums(id,title)").execute()
#     items = results.get('albums', [])
#     if not items:
#         print('No albums found.')
#     else:
#         print('Albums:')
#         for item in items:
#             print('{0} ({1})'.format(item['title'].encode('utf8'), item['id']))


# from os.path import join, dirname
# from googleapiclient.discovery import build
# from httplib2 import Http
# from oauth2client import file, client, tools


# # https://stackoverflow.com/questions/50573196/access-google-photo-api-with-python-using-google-api-python-client
# def run_things():
#     SCOPES = 'https://www.googleapis.com/auth/photoslibrary.readonly'
#     store = file.Storage(join(dirname(__file__), 'token-for-google.json'))
#     creds = store.get()
#     if not creds or creds.invalid:
#         flow = client.flow_from_clientsecrets(join(dirname(__file__), 'client_id.json'), SCOPES)
#         # flow = client.flow_from_clientsecrets('client_id.json', SCOPES)
#         creds = tools.run_flow(flow, store)
#     google_photos = build('photoslibrary', 'v1', http=creds.authorize(Http()))

#     day, month, year = ('0', '6', '2019')  # Day or month may be 0 => full month resp. year
#     date_filter = [{"day": day, "month": month, "year": year}]  # No leading zeroes for day an month!
#     nextpagetoken = 'Dummy'
#     while nextpagetoken != '':
#         nextpagetoken = '' if nextpagetoken == 'Dummy' else nextpagetoken
#         results = google_photos.mediaItems().search(
#                 body={"filters":  {"dateFilter": {"dates": [{"day": day, "month": month, "year": year}]}},
#                     "pageSize": 10, "pageToken": nextpagetoken}).execute()
#         # The default number of media items to return at a time is 25. The maximum pageSize is 100.
#         items = results.get('mediaItems', [])
#         nextpagetoken = results.get('nextPageToken', '')
#         for item in items:
#                 print(f"{item['filename']} {item['mimeType']} '{item.get('description', '- -')}'"
#                         f" {item['mediaMetadata']['creationTime']}\nURL: {item['productUrl']}")

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

    service = build(API_NAME, API_VERSION, credentials=creds)

    return service


# https://stackoverflow.com/questions/58928685/google-photos-api-python-working-non-deprecated-example
# https://stackoverflow.com/questions/52565028/mediaitems-search-not-working-with-albumid
# https://www.youtube.com/watch?v=lj1uzJQnX38
def get_albums(service):

    if not service:
        service = init_gphotos_service()

    album_results = service.albums().list(fields="albums,nextPageToken", pageSize=10).execute()
    album_items = album_results.get('albums', [])
    albums = []
    if album_items:
        for a_item in album_items:
            search_body = {
                "albumId": a_item['id'],
                "pageSize": 10
            }
            media_results = service.mediaItems().search(body=search_body).execute()
            photos = []
            media_items = media_results.get('mediaItems', [])
            for m_item in media_items:
                photo = {
                    'id': m_item['id'],
                    'filename': m_item['filename'],
                }
                photos.append(photo)
            
            album = {
                'id': a_item['id'],
                'title': a_item['title'],
                'photos': photos,
            }
            albums.append(album)

    return albums