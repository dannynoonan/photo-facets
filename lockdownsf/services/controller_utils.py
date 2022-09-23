from datetime import datetime
import pytz

from django.contrib import messages

from lockdownsf import metadata
from lockdownsf.services import s3manager


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


# def stage_image_for_upload(img_file_path, image_id, width, height, tmp_dir):
#     if width and height:
#         img_file_path = f"{img_file_path}=w{width}-h{height}"

#     # upload gphotos image to s3
#     s3_file_name = f"{tmp_dir}/{image_id}"
#     try:
#         s3manager.upload_image_to_s3(img_file_path, s3_file_name)
#         return s3_file_name
#     except Exception as ex:
#         raise Exception("Failure to upload image to s3. Details: {ex}")


def convert_album_to_json(album):
    if not (album and hasattr(album, 'photos')):
        return None

    photos_json = []
    for photo in album.photos:
        tags_json = [tag.name for tag in photo.tags.filter(status='ACTIVE').distinct()]
        photo_thumb_url = f"<img src='https://lockdownsf.s3.amazonaws.com/{photo.album.s3_dir}/{photo.file_name}' width='300'>"
        photo_json = {
            'id': str(photo.id),
            'longitude': str(photo.longitude),
            'latitude': str(photo.latitude),
            'thumb_url': photo_thumb_url,
            'tags': tags_json
        }
        photos_json.append(photo_json)
        
    album_json = {
        's3_dir': album.s3_dir,
        'longitude': str(album.center_longitude),
        'latitude': str(album.center_latitude),
        'zoom_level': str(album.map_zoom_level),
        'photos': photos_json,
    }

    return album_json
