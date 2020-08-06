from lockdownsf import metadata


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