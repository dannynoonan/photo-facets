from django.contrib import messages

from lockdownsf import metadata
from lockdownsf.services import gphotosapi


def log_and_store_message(request, level, message):
    if level in [messages.ERROR, messages.WARNING]:
        print(message)
    messages.add_message(request, level, message)


def extract_messages_from_storage(request):
    success_messages = []
    error_messages = []
    all_messages = messages.get_messages(request)
    if all_messages:
        for message in all_messages:
            if message.level_tag == 'success':
                success_messages.append(message.message)
            if message.level_tag == 'error':
                error_messages.append(message.message)
    return success_messages, error_messages


def update_mediaitems_with_gphotos_data(gpids_to_img_data, media_items, failed_media_items, status=None):
    if not status:
        status = metadata.Status.LOADED_AND_MAPPED
    matched_media_items = []
    for mapped_gpid, img_data in gpids_to_img_data.items():
        for media_item in media_items:
            if media_item.file_name == img_data.get('filename', ''):
                # update db
                media_item.external_id = mapped_gpid
                media_item.thumb_url = img_data.get('thumb_url', '')
                media_item.status = status.name
                media_item.save()
                # add to matched_media_items
                matched_media_items.append(media_item)
                # remove from failed_media_items
                for f_item in failed_media_items:
                    f_item_fn = f_item.split('/')[-1:][0]
                    if f_item_fn == media_item.file_name:
                        failed_media_items.remove(f_item)
                        continue
                continue

    return matched_media_items


def populate_thumb_urls_from_gphotosapi(mapped_media_items):
    # fetch media_items from gphotos api to populate thumb_urls
    media_item_ids = [m_item.external_id for m_item in mapped_media_items]
    gphotos_media_items = gphotosapi.get_photos_by_ids(media_item_ids)
    for gpmi in gphotos_media_items:
        for mmi in mapped_media_items:
            if not (gpmi.get('mediaItem', '') and gpmi['mediaItem'].get('id', '')):
                print(f"Error fetching mediaItem, mediaItem or mediaItem['id'] was None. Skipping to next.")
                continue
            if gpmi['mediaItem']['id'] == mmi.external_id:
                mmi.thumb_url = gpmi['mediaItem'].get('baseUrl', '')
                continue