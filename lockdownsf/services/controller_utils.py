from datetime import datetime
import pytz

from django.contrib import messages

from lockdownsf import metadata
from lockdownsf.services import gphotosapi, s3manager


def log_and_store_message(request, level, message):
    if level in [messages.ERROR, messages.WARNING]:
        print(message)
    messages.add_message(request, level, message)


def extract_messages_from_storage(request):
    response_messages = {
        'success': [],
        'warning': [],
        'error': []
    }
    all_messages = messages.get_messages(request)
    if all_messages:
        for message in all_messages:
            if message.level_tag == 'success':
                response_messages['success'].append(message.message)
            if message.level_tag == 'warning':
                response_messages['warning'].append(message.message)
            if message.level_tag == 'error':
                response_messages['error'].append(message.message)

    return response_messages


def update_photos_with_gphotos_data(gpids_to_img_data, photos, failed_photos, status):
    matched_photos = []
    for gpid, img_data in gpids_to_img_data.items():
        for photo in photos:
            # TODO this matching is problematic if a preexisting version of the same image is returned by gphotos api but that version has a different filename 
            if photo.file_name == img_data.get('filename', ''):
                # update db
                photo.external_id = gpid
                photo.status = status.name
                # add to matched_photos
                matched_photos.append(photo)
                # remove from failed_photos
                for fp in failed_photos:
                    fp_fn = fp.split('/')[-1:][0]
                    if fp_fn == photo.file_name:
                        failed_photos.remove(fp)
                        continue
                continue

    return matched_photos


def populate_fields_from_gphotosapi(mapped_photos, fields):
    # fetch media_items from gphotos api 
    photo_ids = [p.external_id for p in mapped_photos if p.external_id]
    gphotos_media_items = gphotosapi.get_photos_by_ids(photo_ids)
    # populate photo fields from gphotos media_items
    for gpmi in gphotos_media_items:
        for photo in mapped_photos:
            if not (gpmi.get('mediaItem', '') and gpmi['mediaItem'].get('id', '')):
                print(f"Error fetching mediaItem, mediaItem or mediaItem['id'] was None. Skipping to next.")
                continue            
            if gpmi['mediaItem']['id'] == photo.external_id:
                for field in fields:
                    if field == 'thumb_url':
                        photo.thumb_url = gpmi['mediaItem'].get('baseUrl', '')
                    if field == 'mime_type':
                        photo.mime_type = gpmi['mediaItem'].get('mimeType', '')
                    if field == 'description':
                        photo.description = gpmi['mediaItem'].get('description', '')
                    if field == 'width':
                        if gpmi['mediaItem'].get('mediaMetadata', ''):
                            photo.width = gpmi['mediaItem']['mediaMetadata'].get('width', '')
                    if field == 'height':
                        if gpmi['mediaItem'].get('mediaMetadata', ''):
                            photo.height = gpmi['mediaItem']['mediaMetadata'].get('height', '')
                    # if field == 'dt_taken':
                    #     if gpmi['mediaItem'].get('mediaMetadata', '')
                    #         photo.dt_taken = gpmi['mediaItem']['mediaMetadata'].get('creationTime', '')                
                continue


def copy_gphotos_image_to_s3(photo_external_id, tmp_dir):
    # fetch image data from gphotos api
    gphotos_image_response = gphotosapi.get_photo_by_id(photo_external_id)

    if not (gphotos_image_response and gphotos_image_response.get('baseUrl', '')):
        raise Exception("Failure to extract OCR text, no google photos image returned matching external_id [{photo_external_id}]")

    # assemble gphotos image file path
    img_file_path = gphotos_image_response['baseUrl']

    # append width & height data if available
    if gphotos_image_response.get('mediaMetadata', ''):
        width = gphotos_image_response['mediaMetadata'].get('width')
        height = gphotos_image_response['mediaMetadata'].get('height')
        if width and height:
            img_file_path = f"{img_file_path}=w{width}-h{height}"

    # upload gphotos image to s3
    s3_file_name = f"{tmp_dir}/{photo_external_id}"
    try:
        s3manager.upload_image_to_s3(img_file_path, s3_file_name)
        return s3_file_name
    except Exception as ex:
        raise Exception("Failure to extract OCR text, google photos image could not be uploaded to s3 for google external_id [{photo_external_id}]. Details: {ex}")


def convert_album_to_json(album):
    if not (album and hasattr(album, 'photos')):
        return None

    photos_json = []
    for photo in album.photos:
        tags_json = [tag.name for tag in photo.tags.filter(status='ACTIVE').distinct()]
        photo_json = {
            'external_id': photo.external_id,
            'longitude': str(photo.longitude),
            'latitude': str(photo.latitude),
            'thumb_url': photo.thumb_url,
            'tags': tags_json
        }
        photos_json.append(photo_json)
        
    album_json = {
        'external_id': album.external_id,
        'longitude': str(album.center_longitude),
        'latitude': str(album.center_latitude),
        'zoom_level': str(album.map_zoom_level),
        'photos': photos_json,
    }

    return album_json


# def diff_photo(db_photo, gphotos_media_item):
#     fields_with_differences = []
#     if not (db_photo and gphotos_media_item):
#         # fields_with_differences = ['description', 'mime_type', 'file_name', 'dt_taken']
#         fields_with_differences = ['description', 'file_name']
#     else:
#         # description - massage empty data (TODO figure out better way to do this)
#         if not db_photo.description:
#             db_photo.description = ''
#         if db_photo.description != gphotos_media_item.get('description', ''):
#             fields_with_differences.append('description')
#         # file_name
#         if db_photo.file_name != gphotos_media_item.get('filename', ''):
#             fields_with_differences.append('file_name')
#         # date taken 
#         if not gphotos_media_item.get('dt_taken', ''):
#             if db_photo.dt_taken:
#                 # db dt_taken is set but gphotos creationTime is not
#                 fields_with_differences.append('dt_taken')
#         else:
#             if not db_photo.dt_taken:
#                 # gphotos creationTime is set but db dt_taken is not
#                 fields_with_differences.append('dt_taken')
#             else:
#                 # if both gphotos creationTime and db dt_taken are set, massage data for comparison
#                 if db_photo.dt_taken != gphotos_media_item['dt_taken']:
#                     fields_with_differences.append('dt_taken')
#         # mime type
#         # if db_photo.mime_type != gphotos_media_item.get('mimeType', ''):
#         #     fields_with_differences.append('mime_type')

#     return fields_with_differences


# def album_diff_detected(db_album, gphotos_album):
#     # verify that neither album version is falsy
#     if not (db_album and gphotos_album):
#         return True
#     # album name - massage empty data (TODO figure out better way to do this)
#     if not db_album.name:
#         db_album.name = ''
#     if not gphotos_album.get('title', ''):
#         gphotos_album['title'] = ''
#     if not gphotos_album.get('title', '') or gphotos_album['title'] != db_album.name:
#         return True
#     # compare photo counts between db and gphotos versions
#     if not gphotos_album.get('mediaItemsCount', ''):
#         gphotos_album['mediaItemsCount'] = 0
#     else:
#         gphotos_album['mediaItemsCount'] = int(gphotos_album['mediaItemsCount'])  # TODO need a try/except?
#     if gphotos_album['mediaItemsCount'] != len(db_album.photo_set.all()):
#         return True

#     return False


# flatten gphotos_media_item data to simplify comparisons and django template access
def massage_gphotos_media_item(gphotos_media_item):
    # description - assign default value, trim whitespace
    if not gphotos_media_item.get('description', ''):
        gphotos_media_item['description'] = ''
    gphotos_media_item['description'] = gphotos_media_item['description'].strip()
    # date taken
    if gphotos_media_item.get('mediaMetadata', ''):
        gphotos_media_item['creationTime'] = gphotos_media_item['mediaMetadata'].get('creationTime', '')
        if gphotos_media_item['creationTime']:
            gphotos_media_item['dt_taken'] = datetime.strptime(gphotos_media_item['creationTime'], '%Y-%m-%dT%H:%M:%SZ')
            gphotos_media_item['dt_taken'] = pytz.utc.localize(gphotos_media_item['dt_taken'])