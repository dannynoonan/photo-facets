from __future__ import print_function

from io import BytesIO
import imghdr
# import magic
from os import listdir
from os.path import dirname, exists, isfile, join
import pickle
from PIL import Image
import requests
import shutil

from googleapiclient.discovery import build
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request

# from lockdownsf import metadata
from lockdownsf.services import image_utils


API_NAME = 'photoslibrary'
API_VERSION = 'v1'
CREDENTIALS_FILE = join(dirname(__file__), 'gphotos_credentials.json')
GPHOTOS_UPLOAD_URL = 'https://photoslibrary.googleapis.com/v1/uploads'
# TOKEN_PICKLE_FILE = f"token_{API_NAME}_{API_VERSION}.pickle"
TOKEN_PICKLE_FILE = 'token.pickle'
# SCOPES = [
#     'https://www.googleapis.com/auth/photoslibrary.appendonly',
#     'https://www.googleapis.com/auth/photoslibrary.readonly'
# ]
SCOPES = [
    'https://www.googleapis.com/auth/photoslibrary',
    'https://www.googleapis.com/auth/photoslibrary.edit.appcreateddata'
]



def init_gphotos_service():
    creds = None
    if exists(TOKEN_PICKLE_FILE):
        with open(TOKEN_PICKLE_FILE, 'rb') as token:
            creds = pickle.load(token)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(CREDENTIALS_FILE, SCOPES)
            creds = flow.run_local_server()
        with open(TOKEN_PICKLE_FILE, 'wb') as token:
            pickle.dump(creds, token)

    gphotos_service = build(API_NAME, API_VERSION, credentials=creds)

    return gphotos_service


def init_new_album(album_title, gphotos_service=None):
    if not gphotos_service:
        gphotos_service = init_gphotos_service()

    if not album_title:
        print(f"Failed to init_new_album, album_title is required")
        return None

    # create new album
    request_body = {
        "album": { "title": album_title }
    }
    album_response = gphotos_service.albums().create(body=request_body).execute()

    print(f"Successfully created album [{album_response['title']}]")

    return album_response


def upload_and_map_images_to_album(album_response, image_list=None, image_dir_path=None, from_cloud=False, gphotos_service=None):
    # upload images from image_list or image_dir_path
    media_items_response = batch_upload_images(image_list=image_list, image_dir_path=image_dir_path, from_cloud=from_cloud)
    uploaded_media_items = media_items_response.get('newMediaItemResults', [])
    if not uploaded_media_items: 
        print(f"Failed to batch upload images from image_dir_path [{image_dir_path}]")
        return

    gpids_to_img_data = {}
    for m_item in uploaded_media_items:
        if m_item['status']['message'] == 'Success':
            print(f"media item [{m_item['mediaItem']}] is IN")
            gpids_to_img_data[m_item['mediaItem']['id']] = m_item['mediaItem']

    # map newly uploaded images into new album
    result = map_images_to_album(gpids_to_img_data, album_response['id'])

    print(f"Successfully uploaded [{len(gpids_to_img_data)}] images and mapped [{len(result['mapped_gpids_to_img_data'])}] images to album [{album_response['title']}]")

    if result.get('unmapped_gpids_to_img_data', ''):
        print(f"Failed to add [{len(result['unmapped_gpids_to_img_data'])}] images into album. This may be due to a duplicate version of an image already existing in your library. Make sure you are only trying to add images that don't already exist in your library.")
        # app_created_photos = get_app_created_photos_for_album(album_response['id'])

    # fetch gphotos images mapped to album in order to get baseUrl thumbnails (incredibly inefficient)
    # if result.get('mapped_gpids_to_img_data', ''):
    #     album_photos_response = get_photos_for_album(album_response['id']) 
    #     for response_photo in album_photos_response:
    #         for mapped_gpid, img_data in result['mapped_gpids_to_img_data'].items():
    #             if response_photo['id'] == mapped_gpid:
    #                 img_data['thumb_url'] = response_photo['baseUrl']
    #                 continue

    return result


def batch_upload_images(image_list=None, image_dir_path=None, from_cloud=False, gphotos_service=None):
    if not gphotos_service:
        gphotos_service = init_gphotos_service()

    if not (image_list or image_dir_path):
        print(f"Failed to batch_upload_images, either image_list or image_dir_path must be set")
        return None

    new_media_items = []
    token = pickle.load(open(TOKEN_PICKLE_FILE, 'rb'))
    
    if not image_list:
        image_list = []
        # https://stackoverflow.com/questions/3207219/how-do-i-list-all-files-of-a-directory
        files_in_dir = [f for f in listdir(image_dir_path) if isfile(join(image_dir_path, f))]

        for f in files_in_dir:
            image_path = join(image_dir_path, f)
            image_list.append(image_path)

    for image_path in image_list:
        # if imghdr.what(image_path) not in image_file_types:
        #     print(f"file [{image_path}] is not a blessed image file type. skipping...")
        #     continue
        print(f"begin upload_image for filename [{image_path}]")
        # response = upload_image(image_path, token, from_cloud=from_cloud)
        # new_media_item = {
        #     'simpleMediaItem': {
        #         'uploadToken': response.content.decode('utf-8')
        #     }
        # }
        new_media_item = upload_image(image_path, token, from_cloud=from_cloud)
        new_media_items.append(new_media_item)

    request_body = {
        'newMediaItems': new_media_items
    }
    
    new_media_items_response = gphotos_service.mediaItems().batchCreate(body=request_body).execute()

    return new_media_items_response


def upload_image(image_path, token, from_cloud=False):
    image_filename = image_path.split('/')[-1:][0]  # er?
    headers = {
        'Authorization': 'Bearer ' + token.token,
        'Content-type': 'application/octet-stream',
        'X-Goog-Upload-Protocol': 'raw',
        'X-Goog-Upload-File-Name': image_filename
    }

    print(f"in upload_image, image_path [{image_path}] image_filename [{image_filename}]")
    new_media_item = {}

    if from_cloud:
        # get image from s3, post to gphotos
        get_response = requests.get(image_path, stream=True)
        # if get_response.status_code == 200:
        #     with open('img_placeholder', 'wb') as out_file:
        post_response = requests.post(GPHOTOS_UPLOAD_URL, data=get_response.content, headers=headers)

    else:
        in_mem_image = open(image_path, 'rb').read()
        # mime = magic.Magic(mime=True)
        # mime_type = mime.from_file(image_path)
        # headers['X-Goog-Upload-Content-Type'] = mime_type
        post_response = requests.post(GPHOTOS_UPLOAD_URL, data=in_mem_image, headers=headers)

    new_media_item = {
        'simpleMediaItem': {
            'uploadToken': post_response.content.decode('utf-8'),
        }
    }

    return new_media_item


# https://developers.google.com/photos/library/guides/manage-albums
# https://developers.google.com/photos/library/reference/rest/v1/albums/patch
def update_album(album_id, album_name=None, cover_photo_id=None, gphotos_service=None):
    if not gphotos_service:
        gphotos_service = init_gphotos_service()

    if not album_id:
        raise Exception(f"Failure to update_album, album_id required")

    if not (album_name or cover_photo_id):
        raise Exception(f"Failure to update_album [{album_id}], either album_name or cover_photo_id is required")

    # get album by id
    album = get_album(album_id)

    if not album:
        raise Exception(f"Failure to update_album, API call failed for Google Photos album id [{album_id}]")

    request_body = {}
    update_mask = []
    if album_name:
        request_body['title'] = album_name
        update_mask.append('title')
    if cover_photo_id:
        request_body['coverPhotoMediaItemId'] = cover_photo_id
        update_mask.append('coverPhotoMediaItemId')
    update_mask = ','.join(update_mask)
    
    response = gphotos_service.albums().patch(id=album_id, updateMask=update_mask, body=request_body).execute()

    return response


# https://developers.google.com/photos/library/reference/rest/v1/mediaItems/patch
def update_image_description(image_id, image_description, gphotos_service=None):
    if not gphotos_service:
        gphotos_service = init_gphotos_service()
    
    # get image by id
    gphotos_mediaitem = gphotos_service.mediaItems().get(mediaItemId=image_id).execute()

    if not gphotos_mediaitem:
        # TODO handle error
        return

    request_body = { 
        'description': image_description,
    }
    
    try:
        response = gphotos_service.mediaItems().patch(id=image_id, updateMask='description', body=request_body).execute()
        print(f"response: {response}")
    except Exception as ex:
        print(f"ex: {ex}")

    return


def map_images_to_album(gpids_to_img_data, album_id, gphotos_service=None):
    if not gphotos_service:
        gphotos_service = init_gphotos_service()
    
    image_ids = gpids_to_img_data.keys()

    request_body = {
        'mediaItemIds': image_ids
    }

    try:
        # response is empty {} so not assigning it to var
        gphotos_service.albums().batchAddMediaItems(albumId=album_id, body=request_body).execute()
        result = { 
            'mapped_image_ids': image_ids 
        }
        return result
    except:
        mapped_gpids_to_img_data = {}
        unmapped_gpids_to_img_data = {}

        for image_id in image_ids:
            try:
                request_body = {
                    'mediaItemIds': [image_id]
                }
                gphotos_service.albums().batchAddMediaItems(albumId=album_id, body=request_body).execute()
                mapped_gpids_to_img_data[image_id] = gpids_to_img_data[image_id]
            except:
                unmapped_gpids_to_img_data[image_id] = gpids_to_img_data[image_id]

        result = { 
            'mapped_gpids_to_img_data': mapped_gpids_to_img_data,
            'unmapped_gpids_to_img_data': unmapped_gpids_to_img_data 
        }

        # app_created_photos = get_app_created_photos_for_album(album_response['id'])

        return result


def get_album(album_id, gphotos_service=None):
    if not gphotos_service:
        gphotos_service = init_gphotos_service()

    album_response = gphotos_service.albums().get(albumId=album_id).execute()

    return album_response
    
    # album = None
    # if album_response:      
    #     album = {
    #         'id': album_response['id'],
    #         'title': album_response['title']
    #     }

    # return album


# https://stackoverflow.com/questions/52565028/mediaitems-search-not-working-with-albumid
def get_photos_for_album(album_id, media_item_count, gphotos_service=None):
    if not gphotos_service:
        gphotos_service = init_gphotos_service()
        
    search_body = {
        "albumId": album_id,
        "pageSize": media_item_count,
    }
    response = gphotos_service.mediaItems().search(body=search_body).execute()

    return response.get('mediaItems', [])


# not in use
# https://stackoverflow.com/questions/58928685/google-photos-api-python-working-non-deprecated-example
# https://www.youtube.com/watch?v=lj1uzJQnX38
def get_albums(gphotos_service=None):
    if not gphotos_service:
        gphotos_service = init_gphotos_service()

    response = gphotos_service.albums().list(fields="albums,nextPageToken", pageSize=10).execute()
    album_items = response.get('albums', [])
    albums = []
    if album_items:
        for a_item in album_items:
            album = {
                'id': a_item['id'],
                'title': a_item['title'],
            }
            albums.append(album)

    return albums


# not in use
def get_photo_by_id(image_id, gphotos_service=None):
    if not gphotos_service:
        gphotos_service = init_gphotos_service()
    
    response = gphotos_service.mediaItems().get(mediaItemId=image_id).execute()

    return response


# not in use
def get_photos_by_ids(image_ids, gphotos_service=None):
    if not gphotos_service:
        gphotos_service = init_gphotos_service()

    if not image_ids:
        return []
        
    response = gphotos_service.mediaItems().batchGet(mediaItemIds=image_ids).execute()   

    return response.get('mediaItemResults', [])


# TODO not even tested, let alone used
def share_album(album_id, gphotos_service=None):
    if not gphotos_service:
        gphotos_service = init_gphotos_service()

    request_body = {
        'sharedAlbumOptions': {
            'isCollaborative': True,
            'isCommentable': True
        }
    }
    response = gphotos_service.albums().share(albumId=album_id, body=request_body).execute()

    return response


# TODO not even tested, let alone used
def get_app_created_photos_for_album(album_id, gphotos_service=None):
    if not gphotos_service:
        gphotos_service = init_gphotos_service()

    # SCOPES = ['https://www.googleapis.com/auth/photoslibrary.readonly.appcreateddata']

    search_body = {
        "albumId": album_id,
        'filters': {
            'excludeNonAppCreatedData': True 
        }
    }

    response = gphotos_service.mediaItems().search(body=search_body).execute()

    return response.get('mediaItems', [])
