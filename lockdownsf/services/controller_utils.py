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


def update_mediaitems_with_gphotos_data(gpids_to_img_data, media_items, failed_media_items, status):
    matched_media_items = []
    for gpid, img_data in gpids_to_img_data.items():
        for media_item in media_items:
            # TODO this matching is problematic if a preexisting version of the same image is returned by gphotos api but that version has a different filename 
            if media_item.file_name == img_data.get('filename', ''):
                # update db
                media_item.external_id = gpid
                media_item.status = status.name
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


# def populate_thumb_urls_from_gphotosapi(mapped_media_items):
#     # fetch media_items from gphotos api to populate thumb_urls
#     media_item_ids = [m_item.external_id for m_item in mapped_media_items]
#     gphotos_media_items = gphotosapi.get_photos_by_ids(media_item_ids)
#     for gpmi in gphotos_media_items:
#         for mmi in mapped_media_items:
#             if not (gpmi.get('mediaItem', '') and gpmi['mediaItem'].get('id', '')):
#                 print(f"Error fetching mediaItem, mediaItem or mediaItem['id'] was None. Skipping to next.")
#                 continue
#             if gpmi['mediaItem']['id'] == mmi.external_id:
#                 mmi.thumb_url = gpmi['mediaItem'].get('baseUrl', '')
#                 continue


def populate_fields_from_gphotosapi(mapped_media_items, fields):
    # fetch media_items from gphotos api 
    media_item_ids = [m_item.external_id for m_item in mapped_media_items if m_item.external_id]
    gphotos_media_items = gphotosapi.get_photos_by_ids(media_item_ids)
    # populate media_item fields from gphotos media_items
    for gpmi in gphotos_media_items:
        for mmi in mapped_media_items:
            if not (gpmi.get('mediaItem', '') and gpmi['mediaItem'].get('id', '')):
                print(f"Error fetching mediaItem, mediaItem or mediaItem['id'] was None. Skipping to next.")
                continue            
            if gpmi['mediaItem']['id'] == mmi.external_id:
                for field in fields:
                    if field == 'thumb_url':
                        mmi.thumb_url = gpmi['mediaItem'].get('baseUrl', '')
                    if field == 'mime_type':
                        mmi.mime_type = gpmi['mediaItem'].get('mimeType', '')
                    if field == 'description':
                        mmi.description = gpmi['mediaItem'].get('description', '')
                    if field == 'width':
                        if gpmi['mediaItem'].get('mediaMetadata', ''):
                            mmi.width = gpmi['mediaItem']['mediaMetadata'].get('width', '')
                    if field == 'height':
                        if gpmi['mediaItem'].get('mediaMetadata', ''):
                            mmi.height = gpmi['mediaItem']['mediaMetadata'].get('height', '')
                    # if field == 'dt_taken':
                    #     if gpmi['mediaItem'].get('mediaMetadata', '')
                    #         mmi.dt_taken = gpmi['mediaItem']['mediaMetadata'].get('creationTime', '')                
                continue