import boto3
from datetime import datetime
import exifread
from inspect import getmembers
from io import BytesIO
import json
import math
import os
from PIL import Image, ExifTags
import requests
from pprint import pprint
import uuid

from django.contrib import messages
from django.core.paginator import Paginator
from django.db.models import Q
from django.http import HttpResponse, Http404
from django.shortcuts import render, redirect
from django.template import loader

from lockdownsf import metadata
from lockdownsf.models import Album, MediaItem, Neighborhood, Photo, Tag, User
from lockdownsf.services import gphotosapi, image_utils, s3manager
from lockdownsf.services.controller_utils import album_diff_detected, convert_album_to_json, copy_gphotos_image_to_s3, extract_messages_from_storage, log_and_store_message, media_item_diff_detected, populate_fields_from_gphotosapi, update_mediaitems_with_gphotos_data

OWNER = User.objects.get(email='andyshirey@gmail.com')
MAX_RESULTS_PER_PAGE = 40


def index(request):
    template = 'index.html'
    page_title = 'Photo facets home'

    # process messages
    response_messages = extract_messages_from_storage(request)

    # fetch all albums from db
    all_albums = Album.objects.filter(owner=OWNER, external_id__isnull=False, center_latitude__isnull=False, center_longitude__isnull=False)
    # active_tags = Tag.objects.filter(status='ACTIVE')

    if not all_albums:
        log_and_store_message(request, messages.ERROR, 'Failure to load albums to build photo collection')
        context = {
            'template': template,
            'page_title': page_title,
        }
        return render(request, template, context)

    # build json objects to be passed to live site js
    photo_collection_json = []
    all_albums_json = {} 
    for album in all_albums:
        # fetch all media_items per album; ignore albums lacking tagged media items 
        # album_media_items = album.mediaitem_set.filter(tags__isnull=False, tags__in=active_tags).distinct()
        album_media_items = album.mediaitem_set.filter(tags__isnull=False).distinct()
        if not album_media_items:
            continue
        # fetch media_items from gphotos api to populate image metadata
        fields_to_populate = ['thumb_url', 'mime_type', 'width', 'height']
        populate_fields_from_gphotosapi(album_media_items, fields_to_populate)
        album.media_items = album_media_items
        # populate json objects for live site js
        album_json = convert_album_to_json(album)
        photo_collection_json.append(album_json)
        all_albums_json[album.external_id] = album.name
    # build map meta json to be passed to page js
    map_meta_json = {}
    ctr_lat, ctr_lng, zoom_level, photos_having_gps = image_utils.avg_gps_info(all_albums)
    map_meta_json['latitude'] = ctr_lat
    map_meta_json['longitude'] = ctr_lng
    map_meta_json['zoom_level'] = zoom_level

    context = {
        'template': template,
        'page_title': page_title,
        'response_messages': response_messages,
        # 'all_albums': all_albums,
        'selected_album_id': None,
        'photo_collection_json': json.dumps(photo_collection_json, indent=4),
        'all_albums_json': json.dumps(all_albums_json, indent=4),
        'map_meta_json': json.dumps(map_meta_json, indent=4),
    }

    return render(request, template, context)


def album_map(request, album_id):
    template = 'index.html'
    page_title = 'Photo facets - album map'

    # process messages
    response_messages = extract_messages_from_storage(request)

    # fetch all albums from db
    all_albums = Album.objects.filter(owner=OWNER, external_id__isnull=False, center_latitude__isnull=False, center_longitude__isnull=False)

    if not all_albums:
        log_and_store_message(request, messages.ERROR, 'Failure to load albums to build photo collection')
        return redirect(f"/lockdownsf/")
    
    # build json objects to be passed to live site js
    all_albums_json = {}
    for album in all_albums:
        # ignore albums lacking tagged media items
        album_media_items = album.mediaitem_set.filter(tags__isnull=False).distinct()
        if not album_media_items:
            continue
        # TODO ignore media albums lacking active tags
        all_albums_json[album.external_id] = album.name

    try:
        selected_album = Album.objects.get(external_id=album_id)
    except Exception as ex:
        log_and_store_message(request, messages.ERROR, 'Failure to load album with google photos id [{album_id}]')
        return redirect(f"/lockdownsf/")

    # fetch tagged media_items for album
    selected_album_media_items = selected_album.mediaitem_set.filter(tags__isnull=False).distinct()
    if selected_album_media_items:
        # fetch media_items from gphotos api to populate image metadata
        fields_to_populate = ['thumb_url', 'mime_type', 'width', 'height']
        populate_fields_from_gphotosapi(selected_album_media_items, fields_to_populate)
        selected_album.media_items = selected_album_media_items

    # build single album photo_collection json to be passed to page js
    selected_album_json = convert_album_to_json(selected_album)
    photo_collection_json = [selected_album_json]
    # build map meta json to be passed to page js
    map_meta_json = {}
    map_meta_json['latitude'] = str(selected_album.center_latitude)
    map_meta_json['longitude'] = str(selected_album.center_longitude)
    map_meta_json['zoom_level'] = selected_album.map_zoom_level

    context = {
        'template': template,
        'page_title': page_title,
        'response_messages': response_messages,
        # 'all_albums': all_albums,
        'selected_album_id': selected_album.external_id,
        'photo_collection_json': json.dumps(photo_collection_json, indent=4),
        'all_albums_json': json.dumps(all_albums_json, indent=4),
        'map_meta_json': json.dumps(map_meta_json, indent=4),
    }

    return render(request, template, context)


def sign_s3(request):
    # S3_BUCKET = os.environ.get('S3_BUCKET')
    # S3_BUCKET = settings.S3_BUCKET_NAME

    # file_name = request.args.get('file_name')
    # file_type = request.args.get('file_type')

    # object_name = urllib.parse.quote_plus(request.GET['file_name'])
    file_name = request.GET['file_name']
    file_type = request.GET['file_type']

    s3 = boto3.client('s3',
         aws_access_key_id=metadata.AWS_ACCESS_KEY_ID,
         aws_secret_access_key=metadata.AWS_SECRET_ACCESS_KEY)

    presigned_post = s3.generate_presigned_post(
        Bucket = metadata.S3_BUCKET,
        Key = file_name,
        Fields = {"acl": "public-read", "Content-Type": file_type},
        Conditions = [
            {"acl": "public-read"},
            {"Content-Type": file_type}
        ],
        ExpiresIn = 3600
    )

    data = json.dumps({
        'data': presigned_post,
        'url': f"https://{metadata.S3_BUCKET}.s3.amazonaws.com/{file_name}",
    })

    return HttpResponse(data, content_type='json')


def manage(request):
    template = 'manage.html'
    page_title = 'Management console'

    # process messages
    response_messages = extract_messages_from_storage(request)

    # form backing data
    all_albums = Album.objects.filter(owner=OWNER, external_id__isnull=False)

    context = {
        'template': template,
        'page_title': page_title,
        'response_messages': response_messages,
        'all_albums': all_albums,
    }
    
    return render(request, template, context)


def album_listing(request):
    template = 'album_listing.html'
    page_title = 'Album listing'

    # process messages
    response_messages = extract_messages_from_storage(request)

    all_albums = Album.objects.filter(owner=OWNER, external_id__isnull=False)
    if all_albums:
        for album in all_albums:
            album.mediaitem_count = len(album.mediaitem_set.all())

    context = {
        'template': template,
        'page_title': page_title,
        'response_messages': response_messages,
        'all_albums': all_albums,
    }
    
    return render(request, template, context)

    
def album_view(request, album_external_id, page_number=None):
    template = 'album_view.html'
    page_title = 'Album details'

    # form backing data
    all_albums = Album.objects.filter(owner=OWNER, external_id__isnull=False)

    if not album_external_id:
        log_and_store_message(request, messages.ERROR, 'Failure to fetch album, no external_id was specified')
        context = {
            'template': template,
            'page_title': page_title,
            'response_messages': response_messages,
            'all_albums': all_albums,
        }
        return render(request, template, context)

    # fetch album and mapped media_items from db
    try:
        album = Album.objects.get(external_id=album_external_id)
        mapped_media_items = album.mediaitem_set.all().order_by('dt_taken')
    except Exception as ex:
        log_and_store_message(request, messages.ERROR, f"Failure to fetch album [{album_external_id}]. Details: {ex}")
        return redirect(f"/lockdownsf/manage/album_listing/")
    
    # diff media_items returned by gphotos api call to those mapped to db album
    gphotos_album = gphotosapi.get_album(album_external_id)
    if album_diff_detected(album, gphotos_album):
        diff_link = f"<a href=\"/lockdownsf/manage/album_diff/{album_external_id}/\">inspect differences</a>"
        log_and_store_message(request, messages.WARNING, 
            f"Differences detected between Google Photos API and photo-facets db versions of this album. Click to {diff_link}.")
    
    page_title = f"{page_title}: {album.name}"

    # pagination
    if page_number:
        page_number = int(page_number)
    else:
        page_number = 1
    total_results_count = len(mapped_media_items)
    paginator = Paginator(mapped_media_items, MAX_RESULTS_PER_PAGE)
    page_results = paginator.page(page_number) 
    prev_page_number = None
    next_page_number = None
    if page_results.has_previous():
        prev_page_number = page_number - 1
    if page_results.has_next():
        next_page_number = page_number + 1

    # fetch media_items from gphotos api to populate image metadata
    fields_to_populate = ['thumb_url', 'mime_type', 'width', 'height']
    populate_fields_from_gphotosapi(page_results, fields_to_populate)

    # process messages
    response_messages = extract_messages_from_storage(request)

    context = {
        'template': template,
        'page_title': page_title,
        'response_messages': response_messages,
        'all_albums': all_albums,
        'album': album,
        'page_number': page_number,
        'prev_page_number': prev_page_number,
        'next_page_number': next_page_number,
        'page_count_iterator': range(1, paginator.num_pages+1),
        'page_results': page_results,
        'page_results_start_index': page_results.start_index(),
        'page_results_end_index': page_results.end_index(),
        'total_results_count': total_results_count,
    }

    return render(request, template, context)


def album_edit(request):

    # assign form data to vars and validate input
    album_external_id = request.POST.get('album-external-id', '')
    # update_album_name_flag = request.POST.get('update-album-name-flag', '')
    album_name = request.POST.get('album-name', '')

    if not album_external_id:
        log_and_store_message(request, messages.ERROR, "Failed to update album, no album id was set.")
        return redirect(f"/lockdownsf/manage/album_listing/")

    # if update_album_name_flag:
    if not album_name:
        log_and_store_message(request, messages.ERROR, "Failed to update album, album name cannot be empty.")
        return redirect(f"/lockdownsf/manage/album_view/{album_external_id}/")

    # update album name in gphotos api
    try:
        album_response = gphotosapi.update_album(album_external_id, album_name=album_name)
        if not album_response:
            log_and_store_message(request, messages.ERROR,
                f"Failed to update album with Google Photos id [{album_external_id}], Google Photos API response was empty.")
            return redirect(f"/lockdownsf/manage/album_view/{album_external_id}/")
    except Exception as ex:
        log_and_store_message(request, messages.ERROR,
            f"Failed to update album with Google Photos id [{album_external_id}], call to Google Photos API failed. Details: {ex}")
        return redirect(f"/lockdownsf/manage/album_view/{album_external_id}/")

    # update album name in db (where it's needed since gphotos api doesn't support album search)
    try:
        album = Album.objects.get(external_id=album_external_id)
        album.name = album_name
        album.save()
    except Exception as ex:
        log_and_store_message(request, messages.ERROR,
            f"Failed to update album with Google Photos id [{album_external_id}]. Details: {ex}")
        return redirect(f"/lockdownsf/manage/album_listing/")
    
    # if everything fired without exceptions, return success
    log_and_store_message(request, messages.SUCCESS,
        f"Successfully updated album [{album_external_id}] in both Google Photos API and photo-facets db.")
    return redirect(f"/lockdownsf/manage/album_view/{album_external_id}/")


def album_select_new_media(request):
    template = 'album_select_new_media.html'
    page_title = 'Select photos for import into album'

    # assign form data to vars and validate input
    add_to_album_external_id = request.POST.get('add-to-album-external-id', '')

    # generate uuid for tmp s3 dir to store photos to if any are uploaded
    tmp_dir_uuid = uuid.uuid4()

    # form backing data
    all_albums = Album.objects.filter(owner=OWNER, external_id__isnull=False)

    context = {
        'template': template,
        'page_title': page_title,
        'all_albums': all_albums,
        'tmp_dir_uuid': tmp_dir_uuid,
        'add_to_album_external_id': add_to_album_external_id,
    }
    
    return render(request, template, context)


def album_import_new_media(request):
    """Extract data from s3 photos and add them to gphotos and db: 
    - if new album:
    -   init and save Album to db with status NEWBORN and no external_id
    - else:
    -   fetch album from db
    - download the photos from s3
    - extract GPS and timestamp info from photos
    - init and save MediaItems to db, with status NEWBORN, no external_id, and not mapped to album
    - if new album:
    -   create gphotos album
    -   update Album in db with external_id and set status to LOADED
    - else:
    -   fetch album from gphotos
    - upload and map gphotos mediaItems to gphotos album
    - update MediaItems in db...
    -   if gphotos upload success: update external_ids and set status to LOADED_AND_MAPPED  
    -   if gphotos loading failed: set status to LOADED (and no external_id to set)
    - calculate GPS
    - if new album:
    -   update Album in db with gps data and set status to LOADED_AND_MAPPED
    - else:
    -   update Album in db with new gps data
    - delete photos from s3
    """
    
    # TODO workflow is dependent on filename uniqueness, which is one reason it's best to stick with 
    # folder upload rather than drag-and-drop

    # assign form data to vars and validate input
    images_to_upload = request.POST.getlist('images-to-upload', [])
    print(f"images_to_upload: [{images_to_upload}]")
    album_external_id = request.POST.get('select-album-external-id', '')
    album_name = request.POST.get('new-album-name', '')
    tmp_dir_uuid = request.POST.get('tmp-dir-uuid', '')
    
    if not images_to_upload:
        log_and_store_message(request, messages.ERROR,
            "Failed to import photos, no photos were queued for upload. At least one photo is required.")
        return redirect(f"/lockdownsf/manage/album_select_new_media/")

    # if adding photos to existing album: fetch album from db
    if album_external_id:
        try:
            album = Album.objects.get(external_id=album_external_id)
        except Exception as ex:
            log_and_store_message(request, messages.ERROR,
                "Failed to import photos, no album found matching external id [{album_external_id}]. Details: {ex}")
            return redirect(f"/lockdownsf/manage/album_select_new_media/")
    
    # if adding photos to new album: create new album in db
    else:
        if not album_name:
            log_and_store_message(request, messages.ERROR,
                "Failed to create album, no album title was specified.")
            return redirect(f"/lockdownsf/manage/album_select_new_media/")

        # insert Album into db with status NEWBORN and no external_id
        album = Album(name=album_name, owner=OWNER, status=metadata.Status.NEWBORN.name)
        album.save()

    # for both new and existing album workflow: download photos from s3, extract GPS and timestamp info 
    media_items = []
    image_file_names = []
    for image_path in images_to_upload:
        image_file_name = image_path.split('/')[-1:][0]
        # store file_names to list used to delete from s3 later TODO redundant but avoids combining success/failure lists later
        image_file_names.append(image_file_name)

        # download each photo from s3
        response = requests.get(image_path, stream=True)
        pil_image = Image.open(BytesIO(response.content))

        # extract GPS and timestamp info
        exif_data = image_utils.get_exif_data(pil_image)
        lat = 0
        lng = 0
        dt_taken = None
        if exif_data:
            if exif_data.get('GPSInfo', ''):
                lat, lng = image_utils.get_lat_lng(exif_data.get('GPSInfo', ''))
            if exif_data.get('DateTimeOriginal', ''):
                dt_taken = datetime.strptime(exif_data['DateTimeOriginal'], '%Y:%m:%d %H:%M:%S')
        else: 
            log_and_store_message(request, messages.ERROR, f"Failure to get exif_data for image_path [{image_path}]")

        # extract OCR text
        # extracted_text_search, extracted_text_display = s3manager.extract_text(image_file_name, metadata.S3_BUCKET)

        # init and save MediaItems to db, with status NEWBORN, no external_id, and not yet mapped to Album
        media_item = MediaItem(
            file_name=image_file_name, owner=OWNER, mime_type=pil_image.format, dt_taken=dt_taken, 
            latitude=lat, longitude=lng, status=metadata.Status.NEWBORN.name)
            # extracted_text_search=extracted_text_search, extracted_text_display=extracted_text_display)
        media_item.save()
        media_items.append(media_item)

    # if adding photos to existing album: fetch album from gphotos 
    if album_external_id:
        album_response = gphotosapi.get_album(album_external_id)

        if not album_response or not album_response['id']:
            log_and_store_message(request, messages.ERROR, 
                "Failure to import photos, unable to fetch album with id [{album_external_id}] from Google Photos API. Has this album been removed directly from Google Photos without being deleted in the Photo Facets app?")
            # TODO do I need to delete partially loaded photos here, otherwise key collisions on subsequent reload?
            return redirect(f"/lockdownsf/manage/album_select_new_media/")

    # if adding photos to new album: create gphotos album, update album external_id and status in db
    else:
        album_response = gphotosapi.init_new_album(album_name)

        if not album_response or not album_response['id']:
            log_and_store_message(request, messages.ERROR, "@@@@@@ ERROR GRASSHOPPER DISASSEMBLE")
            return redirect(f"/lockdownsf/manage/album_select_new_media/")

        # update Album in db with status LOADED and external_id set
        album.external_id = album_response['id']
        album.status = metadata.Status.LOADED.name
        album.save()

    # for both new and existing album workflow: upload and map gphotos mediaItems to gphotos album
    mapped_images_response = gphotosapi.upload_and_map_images_to_album(album_response, image_list=images_to_upload, from_cloud=True)

    # for both new and existing album workflow: update MediaItems in db...
    # -> if gphotos upload success: update external_ids, set status to LOADED_AND_MAPPED
    # -> if gphotos upload failure: set status to LOADED
    mapped_media_items = []
    unmapped_media_items = []
    failed_media_items = images_to_upload
    if mapped_images_response:
        # update images mapped to an album
        if mapped_images_response.get('mapped_gpids_to_img_data', ''):
            mapped_media_items = update_mediaitems_with_gphotos_data(
                mapped_images_response['mapped_gpids_to_img_data'], media_items, failed_media_items, status=metadata.Status.LOADED_AND_MAPPED)
            # set album and save to db
            for mapped_media_item in mapped_media_items:
                mapped_media_item.album = album
                mapped_media_item.save()
        # update images that failed to map to album
        if mapped_images_response.get('unmapped_gpids_to_img_data', ''):
            unmapped_media_items = update_mediaitems_with_gphotos_data(
                mapped_images_response['unmapped_gpids_to_img_data'], media_items, failed_media_items, status=metadata.Status.LOADED)

    # for both new and existing album workflow: calculate album lat/lng and furthest N-S or E-W distance between points
    # freshly fetch album to get all of its mappings - technically unnecessary for new albums, but just cleaner/streamlined this way
    album = Album.objects.get(external_id=album.external_id)
    ctr_lat, ctr_lng, zoom_level, photos_having_gps = image_utils.avg_gps_info(album.mediaitem_set.all())
    # update Album in db with center lat/lng, zoom level, and status LOADED_AND_MAPPED
    album.center_latitude = ctr_lat
    album.center_longitude = ctr_lng
    album.map_zoom_level = zoom_level
    album.photos_having_gps = photos_having_gps
    album.status = metadata.Status.LOADED_AND_MAPPED.name
    album.save()

    # for both new and existing album workflow: response messaging
    # if adding photos to existing album
    log_and_store_message(request, messages.SUCCESS,
        f"Successfully mapped [{len(mapped_media_items)}] new media items to album [{album.name}]")
    if unmapped_media_items:
        log_and_store_message(request, messages.ERROR,
            f"Successfully loaded [{len(unmapped_media_items)}] media items, but failed to map these to album [{album.name}]")
        log_and_store_message(request, messages.ERROR, f"Unmapped media items: [{unmapped_media_items}]")
    if failed_media_items:
        log_and_store_message(request, messages.ERROR,
            f"Failed to load [{len(failed_media_items)}] media items into google photos library.")
        log_and_store_message(request, messages.ERROR, f"Failed media items: [{failed_media_items}]")

    # delete photos from s3
    s3manager.delete_dir(tmp_dir_uuid, image_file_names)
    
    return redirect(f"/lockdownsf/manage/album_view/{album.external_id}/")


def album_delete(request):

    # assign form data to vars and validate input
    album_external_id = request.POST.get('album-external-id', '')

    if not album_external_id:
        log_and_store_message(request, messages.ERROR, 'Unable to delete album, album_external_id was not set.')

    else:
        try:
            # fetch album from db, then delete it
            album = Album.objects.get(external_id=album_external_id)
            album.delete()

            # generate success and failure messages
            log_and_store_message(request, messages.SUCCESS, f"Successfully deleted album [{album.name}]")
            # build html containing link to deleted Google Photos album
            # doing this here to leverage the simple text limitations of messages framework 
            link_to_deleted_album = f"<ul><li><a href=\"https://photos.google.com/lr/album/{album_external_id}\" target=\"new\">{album.name}</a></li></ul>"
            log_and_store_message(request, messages.SUCCESS, 
                f"Note this album still exists in Google Photos. To also delete it there, visit this link: {link_to_deleted_album}")

        except Exception as ex:
            log_and_store_message(request, messages.ERROR, 
                f"Failed to delete album with external_id [{album_external_id}]. Exception: {ex}")

    return redirect(f"/lockdownsf/manage/album_listing/")


def album_media_items_delete(request):

    # assign form data to vars and validate input 
    album_external_id = request.POST.get('album-external-id', '')
    media_item_external_ids = request.POST.getlist('media-item-external-ids', '')

    if not album_external_id:
        log_and_store_message(request, messages.ERROR, 
            f"Failure to delete media items from album, no album_external_id was specified")
        return redirect(f"/lockdownsf/manage/album_listing/")

    if not media_item_external_ids:
        log_and_store_message(request, messages.ERROR, 
            f"Failure to delete media items from album [{album_external_id}], no media items were specified")
        return redirect(f"/lockdownsf/manage/album_view/{album_external_id}/")

    successful_media_item_ids = []
    failed_media_item_ids = []
    album_label = album_external_id

    # fetch media_items from db, delete them, and track deleted items in list 
    for media_item_id in media_item_external_ids:
        try:
            media_item = MediaItem.objects.get(external_id=media_item_id)
            media_item.delete()
            successful_media_item_ids.append(media_item_id)

        except Exception as ex:
            failed_media_item_ids.append(media_item_id)

    # fetch album and update GPS data based on remaining media items
    try:
        album = Album.objects.get(external_id=album_external_id)
        album_label = album.name  
        ctr_lat, ctr_lng, zoom_level, photos_having_gps = image_utils.avg_gps_info(album.mediaitem_set.all())
        album.center_latitude = ctr_lat
        album.center_longitude = ctr_lng
        album.map_zoom_level = zoom_level
        album.photos_having_gps = photos_having_gps
        album.save()
    except Exception as ex:
        log_and_store_message(request, messages.ERROR, 
            f"After deleting media items from album [{album_external_id}], failure to fetch album or update its GPS info in db. Details: {ex}")
        
    # generate success and failure messages
    if successful_media_item_ids:
        log_and_store_message(request, messages.SUCCESS, 
            f"Successfully deleted [{len(successful_media_item_ids)}] media items from album [{album_label}]")
        # build html containing links to deleted Google Photos media
        # doing this here to leverage the simple text limitations of messages framework 
        links_to_deleted_media_items = "<ul>"
        for media_item_id in successful_media_item_ids:
            links_to_deleted_media_items = f"{links_to_deleted_media_items}<li><a href=\"https://photos.google.com/lr/album/{album_external_id}/photo/{media_item_id}\" target=\"new\">{media_item_id}</a></li>"
        links_to_deleted_media_items = f"{links_to_deleted_media_items}</ul>"
        log_and_store_message(request, messages.SUCCESS, 
            f"Note that these media items still exist in Google Photos. To also delete them there, visit these links: {links_to_deleted_media_items}")
    if failed_media_item_ids:
        log_and_store_message(request, messages.ERROR, 
            f"Failed to delete [{len(failed_media_item_ids)}] media items from album [{album_label}]")
        log_and_store_message(request, messages.ERROR, f"Failed media items: [{failed_media_item_ids}]")

    return redirect(f"/lockdownsf/manage/album_view/{album_external_id}/")


def album_diff(request, album_external_id):
    template = 'album_diff.html'
    page_title = 'Compare and sync album data (Google Photos API vs photo-facets db)'

    # process messages
    response_messages = extract_messages_from_storage(request)

    # form backing data
    all_albums = Album.objects.filter(owner=OWNER, external_id__isnull=False)

    # fetch album and mapped media_items from db
    try:
        db_album = Album.objects.get(external_id=album_external_id)
        db_album_media_items = db_album.mediaitem_set.all().order_by('dt_taken')
    except Exception as ex:
        log_and_store_message(request, messages.ERROR, 
            f"Failure to fetch album to diff, no album found in db with external_id [{album_external_id}]. Details: {ex}")
        return redirect(f"/lockdownsf/manage/album_listing/")
    
    # fetch album and its mapped media items from gphotos api
    gphotos_album = gphotosapi.get_album(album_external_id)
    if not gphotos_album or not gphotos_album.get('id', ''):
        log_and_store_message(request, messages.ERROR, 
            f"Failure to fetch album to diff, no album found in Google Photos with external_id [{album_external_id}]. Details: {ex}")
        return redirect(f"/lockdownsf/manage/album_listing/")
    gphotos_album_media_items = gphotosapi.get_photos_for_album(album_external_id, gphotos_album.get('mediaItemsCount', ''))

    # diff album returned by gphotos api call to db album
    import ipdb; ipdb.set_trace()

    context = {
        'template': template,
        'page_title': page_title,
        'response_messages': response_messages,
        'all_albums': all_albums,
        'db_album': db_album,
        'db_album_media_items': db_album_media_items,
        'gphotos_album': gphotos_album,
        'gphotos_album_media_items': gphotos_album_media_items,
    }
    
    return render(request, template, context)


def mediaitem_search(request):
    template = 'mediaitem_search.html'
    page_title = 'Search for photos'

    # process messages
    response_messages = extract_messages_from_storage(request)

    # form backing data
    all_albums = Album.objects.filter(owner=OWNER, external_id__isnull=False)
    all_tags = Tag.objects.filter(owner=OWNER)

    # assign form data to vars and assemble query filters
    search_criteria = {}
    and_filters = {}
    or_filters = ''
    page_number = 1
    if request.GET.get('page-number'):
        page_number = int(request.GET.get('page-number'))
    if request.GET.get('search-album'):
        search_album = Album.objects.get(external_id=request.GET.get('search-album'))
        and_filters['album'] = search_album.id
        search_criteria['search_album_name'] = search_album.name
        search_criteria['search_album_id'] = search_album.external_id
    if request.GET.get('search-tag'):
        search_tag = Tag.objects.get(name=request.GET.get('search-tag'))
        and_filters['tags'] = search_tag.id
        search_criteria['search_tag_name'] = search_tag.name
    if request.GET.get('search-text'):
        search_text = request.GET.get('search-text').lower()
        or_filters = Q(extracted_text_search__icontains = search_text) | Q(external_id__icontains = search_text) | Q(file_name__icontains = search_text) | Q(description__icontains = search_text)
        search_criteria['search_text'] = search_text

    # fetch media_items from db
    matching_mediaitems = MediaItem.objects.filter(**and_filters).order_by('-dt_taken')
    if or_filters:
        matching_mediaitems = matching_mediaitems.filter(or_filters).order_by('-dt_taken')
    
    # pagination
    total_results_count = len(matching_mediaitems)
    paginator = Paginator(matching_mediaitems, MAX_RESULTS_PER_PAGE)
    page_results = paginator.page(page_number) 
    prev_page_number = None
    next_page_number = None
    if page_results.has_previous():
        prev_page_number = page_number - 1
    if page_results.has_next():
        next_page_number = page_number + 1

    # fetch media_items from gphotos api to populate image metadata
    fields_to_populate = ['thumb_url', 'mime_type', 'width', 'height']
    populate_fields_from_gphotosapi(page_results, fields_to_populate)

    context = {
        'template': template,
        'page_title': page_title,
        'response_messages': response_messages,
        'all_albums': all_albums,
        'all_tags': all_tags,
        'search_criteria': search_criteria,
        'page_number': page_number,
        'prev_page_number': prev_page_number,
        'next_page_number': next_page_number,
        'page_count_iterator': range(1, paginator.num_pages+1),
        'page_results': page_results,
        'page_results_start_index': page_results.start_index(),
        'page_results_end_index': page_results.end_index(),
        'total_results_count': total_results_count,
    }

    return render(request, template, context)


def mediaitem_view(request, mediaitem_external_id):
    template = 'mediaitem_view.html'
    page_title = 'Photo details'

    # form backing data
    all_albums = Album.objects.filter(owner=OWNER, external_id__isnull=False)
    all_tags = Tag.objects.filter(owner=OWNER)

    # fetch media_item from db
    try:
        mediaitem = MediaItem.objects.get(external_id=mediaitem_external_id)
    except Exception as ex:
        log_and_store_message(request, messages.ERROR,
            f"Failure to fetch media item, no match for external_id [{mediaitem_external_id}]")
        
        return redirect(f"/lockdownsf/manage/mediaitem_search/")

    # diff media_item returned by gphotos api to that mapped to db album
    gphotos_media_item = gphotosapi.get_photo_by_id(mediaitem_external_id)
    if media_item_diff_detected(mediaitem, gphotos_media_item):
        diff_link = f"<a href=\"/lockdownsf/manage/mediaitem_diff/{mediaitem_external_id}/\">inspect differences</a>"
        log_and_store_message(request, messages.WARNING, 
            f"Differences detected between Google Photos API and photo-facets db versions of this media item. Click to {diff_link}.")

    # fetch album from db to determine previous and next media_items for sequential navigation
    mapped_media_items = mediaitem.album.mediaitem_set.all().order_by('dt_taken')

    # store all mapped media_item_ids to list, get index of current media item
    album_media_item_ids = [m.external_id for m in mapped_media_items]
    curr_index = album_media_item_ids.index(mediaitem_external_id)

    # get media item ids for previous and next index
    prev_media_item_id = None
    next_media_item_id = None
    if curr_index > 0:
        prev_media_item_id = album_media_item_ids[curr_index - 1]
    if curr_index < len(album_media_item_ids) - 1:
        next_media_item_id = album_media_item_ids[curr_index + 1]

    # fetch media_items from gphotos api to populate image metadata
    fields_to_populate = ['thumb_url', 'mime_type', 'width', 'height']
    populate_fields_from_gphotosapi([mediaitem], fields_to_populate)

    # mediaitem_location = { 
    #     'lat': str(mediaitem.latitude), 
    #     'lng': str(mediaitem.longitude) 
    # }

    # process messages
    response_messages = extract_messages_from_storage(request)

    context = {
        'template': template,
        'page_title': page_title,
        'response_messages': response_messages,
        'all_albums': all_albums,
        'all_tags': all_tags,
        'mediaitem_external_id': mediaitem_external_id,
        'mediaitem': mediaitem,
        'prev_media_item_id': prev_media_item_id,
        'next_media_item_id': next_media_item_id,
        # 'mediaitem_location_json': json.dumps(mediaitem_location, indent=4),
    }

    return render(request, template, context)


def mediaitem_edit(request):

    # assign form data to vars 
    media_item_external_id = request.POST.get('media-item-external-id', '')
    update_description_flag = request.POST.get('update-description-flag', '')
    new_description = request.POST.get('description', '')
    update_tags_flag = request.POST.get('update-tags-flag', '')
    new_tag_ids = request.POST.getlist('tag_ids', [])

    # handle missing data
    if not media_item_external_id:
        log_and_store_message(request, messages.ERROR, f"Failure to update media item, external_id was not set")
        
        return redirect(f"/lockdownsf/manage/mediaitem_search/")

    if not (update_description_flag or update_tags_flag):
        # javascript should prevent this scenario, but...
        log_and_store_message(request, messages.ERROR, 
            f"Failure to update media item, no data changes were submitted")
        
        return redirect(f"/lockdownsf/manage/mediaitem_view/{media_item_external_id}/")

    # fetch media_item from db
    try:
        media_item = MediaItem.objects.get(external_id=media_item_external_id)
    except Exception as ex:
        log_and_store_message(request, messages.ERROR,
            f"Failure to update media item, no match for external_id [{media_item_external_id}]")
        
        return redirect(f"/lockdownsf/manage/mediaitem_search/")

    # description updates - update db object and gphotos api field
    if update_description_flag:
        # db object update
        media_item.description = new_description

        # gphotos api update
        try:
            response = gphotosapi.update_image_description(media_item_external_id, new_description)
            log_and_store_message(request, messages.SUCCESS,
                f"Successfully updated media item [{media_item_external_id}] with new description [{new_description}] in google photos api")
        except Exception as ex:
            log_and_store_message(request, messages.ERROR,
                f"Failure to update media item [{media_item_external_id}] with description [{new_description}] in google photos api. Exception: {ex}")

    # tags updates - update db object
    if update_tags_flag:
        # process form data
        if new_tag_ids:
            new_tag_ids = [int(tag_id) for tag_id in new_tag_ids]
        old_tag_ids = [old_tag.id for old_tag in media_item.tags.all()]
        tag_ids_to_remove = list(set(old_tag_ids) - set(new_tag_ids))
        tag_ids_to_add = list(set(new_tag_ids) - set(old_tag_ids))

        # delete old tags that aren't in new list
        for tag_id_to_remove in tag_ids_to_remove:
            try:
                tag_to_remove = Tag.objects.get(pk=tag_id_to_remove)
                media_item.tags.remove(tag_to_remove)
            except Exception as ex:
                log_and_store_message(request, messages.ERROR,
                    f"Failure to remove tag, no tag with id [{tag_id_to_remove}] found in db")

        # add new tags that aren't in old list
        for tag_id_to_add in tag_ids_to_add:
            try:
                tag_to_add = Tag.objects.get(pk=tag_id_to_add)
                media_item.tags.add(tag_to_add)
            except Exception as ex:
                log_and_store_message(request, messages.ERROR,
                    f"Failure to add tag, no tag with id [{tag_id_to_add}] found in db")

    # write accumulated changes to db
    try:
        media_item.save()
        log_and_store_message(request, messages.SUCCESS,
            f"Successfully updated media item [{media_item_external_id}] to db") 
    except Exception as ex:
        log_and_store_message(request, messages.ERROR,
            f"Failure to update media item [{media_item_external_id}] to db. Exception: {ex}")

    return redirect(f"/lockdownsf/manage/mediaitem_view/{media_item_external_id}/")


def mediaitem_diff(request, mediaitem_external_id):
    template = 'mediaitem_diff.html'
    page_title = 'Compare and sync media item data (Google Photos API vs photo-facets db)'

    # process messages
    response_messages = extract_messages_from_storage(request)

    # form backing data
    all_albums = Album.objects.filter(owner=OWNER, external_id__isnull=False)

    # fetch media_item from db
    try:
        db_media_item = MediaItem.objects.get(external_id=mediaitem_external_id)
    except Exception as ex:
        log_and_store_message(request, messages.ERROR,
            f"Failure to fetch media item to diff, no match found in db for external_id [{mediaitem_external_id}]")
        return redirect(f"/lockdownsf/manage/mediaitem_search/")

    # fetch media item from gphotos api 
    gphotos_media_item = gphotosapi.get_photo_by_id(mediaitem_external_id)

    context = {
        'template': template,
        'page_title': page_title,
        'response_messages': response_messages,
        'all_albums': all_albums,
        'db_media_item': db_media_item,
        'gphotos_media_item': gphotos_media_item,
    }
    
    return render(request, template, context)


def tag_listing(request):
    template = 'tag_listing.html'
    page_title = 'Tag listing'

    # process messages
    response_messages = extract_messages_from_storage(request)

    # form backing data
    all_albums = Album.objects.filter(owner=OWNER, external_id__isnull=False)
    all_tag_statuses = [ts.name for ts in metadata.TagStatus]
        
    all_tags = Tag.objects.all().order_by('name')
    for tag in all_tags:
        tag.mediaitem_count = len(tag.mediaitem_set.all())
        
    context = {
        'template': template,
        'page_title': page_title,
        'response_messages': response_messages,
        'all_albums': all_albums,
        'all_tag_statuses': all_tag_statuses,
        'all_tags': all_tags,
    }
    
    return render(request, template, context)


def tag_create(request):

    # assign form data to vars and validate input
    new_tag_name = request.POST.get('new-tag-name', '')
    if not new_tag_name:
        log_and_store_message(request, messages.ERROR, f"Failed to create new tag, no tag name was specified.")

        return redirect(f"/lockdownsf/manage/tag_listing/")

    try:
        new_tag = Tag(name=new_tag_name, status=metadata.TagStatus.ACTIVE.name, owner=OWNER)
        new_tag.save()
        log_and_store_message(request, messages.SUCCESS, f"Successfully created new tag [{new_tag.name}].")
    
        return redirect(f"/lockdownsf/manage/tag_listing/")

    except Exception as ex:
        log_and_store_message(request, messages.ERROR, f"Failed to create new tag [{new_tag_name}]. Exception: {ex}")

        return redirect(f"/lockdownsf/manage/tag_listing/")


def tag_edit(request):

    # assign form data to vars and validate input
    tag_id = request.POST.get('tag-id', '')
    if not tag_id:
        log_and_store_message(request, messages.ERROR, f"Failed to edit tag, no tag id was specified.")

        return redirect(f"/lockdownsf/manage/tag_listing/")

    tag_status_field = f"tag-status-select-{tag_id}"
    tag_status = request.POST.get(tag_status_field, '')

    for key, value in request.POST.items():
        print(f"key: {key} | value: {value}") 

    if not tag_status:
        log_and_store_message(request, messages.ERROR, f"Failed to update tag, no status was specified.")

        return redirect(f"/lockdownsf/manage/tag_listing/")

    try:
        tag = Tag.objects.get(pk=tag_id)
        tag.status = tag_status
        tag.save()
        log_and_store_message(request, messages.SUCCESS, f"Successfully updated tag [{tag.name}].")
    
        return redirect(f"/lockdownsf/manage/tag_listing/")

    except Exception as ex:
        log_and_store_message(request, messages.ERROR, f"Failed to fetch and update tag with tag_id [{tag_id}]. Exception: {ex}")

        return redirect(f"/lockdownsf/manage/tag_listing/")


def extract_ocr_text(request):

    # assign form data to vars and validate input
    request_scope = request.POST.get('request-scope', '')
    external_id = request.POST.get('external-id', '')

    if not (request_scope and external_id):
        log_and_store_message(request, messages.ERROR, 
            "Failure to extract OCR text, both request_scope and external_id are required")

        return redirect(f"/lockdownsf/manage/")  # TODO where should this go?

    if request_scope not in ['album', 'media_item']:
        log_and_store_message(request, messages.ERROR, 
            "Failure to extract OCR text, request_scope must be 'album' or 'media_item'")

        return redirect(f"/lockdownsf/manage/")  # TODO where should this go?
    
    if request_scope == 'media_item':
        # fetch media item from db
        try:
            media_item = MediaItem.objects.get(external_id=external_id)
        except Exception as ex:
            log_and_store_message(request, messages.ERROR, 
                "Failure to extract OCR text, no image found in db matching external_id [{external_id}]")
            return redirect(f"/lockdownsf/manage/")  # TODO where should this go?

        # copy image from gphotos to s3 for OCR extraction
        try:
            copy_gphotos_image_to_s3(external_id)
        except Exception as ex:
            log_and_store_message(request, messages.ERROR, ex)
            return redirect(f"/lockdownsf/manage/mediaitem_view/{external_id}/")

        # extract OCR text from image on s3
        extracted_text_search, extracted_text_display = s3manager.extract_text(external_id, metadata.S3_BUCKET)

        # add extracted text to media_item and save 
        media_item.extracted_text_search = extracted_text_search
        media_item.extracted_text_display = extracted_text_display
        media_item.save()

        # TODO remove image from s3

        return redirect(f"/lockdownsf/manage/mediaitem_view/{external_id}/")

    if request_scope == "album":
        # fetch media items mapped to album from db
        try:
            album = Album.objects.get(external_id=external_id)
            album_media_items = album.mediaitem_set.all()
        except Exception as ex:
            log_and_store_message(request, messages.ERROR, 
                "Failure to extract OCR text, problem fetching images associated to album with external_id [{external_id}]")
            return redirect(f"/lockdownsf/manage/album_view/{external_id}/")  # should this redirect to another url?

        for media_item in album_media_items:
            # copy image from gphotos to s3 for OCR extraction
            try:
                copy_gphotos_image_to_s3(media_item.external_id)
            except Exception as ex:
                log_and_store_message(request, messages.ERROR, ex)
                continue

            # extract OCR text from image on s3
            extracted_text_search, extracted_text_display = s3manager.extract_text(media_item.external_id, metadata.S3_BUCKET)

            # add extracted text to media_item and save 
            media_item.extracted_text_search = extracted_text_search
            media_item.extracted_text_display = extracted_text_display
            media_item.save()

            # TODO remove image from s3

        return redirect(f"/lockdownsf/manage/album_view/{external_id}/")







def neighborhood_listing(request):
    template = 'neighborhood_listing.html'

    all_neighborhoods = Neighborhood.objects.all()

    for neighborhood in all_neighborhoods:
        neighborhood.photo_count = len(neighborhood.photo_set.all())

    context = {
        'template': template,
        'all_neighborhoods': all_neighborhoods,
    }

    return render(request, template, context)


def add_neighborhood(request):
    template = 'neighborhood_add.html'

    all_neighborhoods = Neighborhood.objects.all()

    context = {
        'template': template,
        'all_neighborhoods': all_neighborhoods,
    }

    return render(request, template, context)


def edit_neighborhood(request, neighborhood_slug):
    template = 'neighborhood_edit.html'

    all_neighborhoods = Neighborhood.objects.all()

    if not neighborhood_slug or neighborhood_slug == "none":
        context = {
            'template': template,
            'all_neighborhoods': all_neighborhoods,
        }
        return render(request, template, context)

    try:
        neighborhood = Neighborhood.objects.get(slug=neighborhood_slug)
        neighborhood_photos = neighborhood.photo_set.all() 

        context = {
            'template': template,
            'all_neighborhoods': all_neighborhoods,
            'neighborhood': neighborhood,
            'neighborhood_photos': neighborhood_photos,
        }
    except Exception as ex:
        context = {
            'template': template,
            'all_neighborhoods': all_neighborhoods,
            'neighborhood_slug': neighborhood_slug,
            'exception': ex,
        }

    return render(request, template, context)


def save_neighborhood(request):
    template = 'neighborhood_save.html'

    all_neighborhoods = Neighborhood.objects.all()

    # bind vars to form data 
    neighborhood_slug = request.POST.get('neighborhood-slug', '')
    neighborhood_name = request.POST.get('neighborhood-name', '')
    # center_latitude = request.POST.get('neighborhood-center-latitude', '')
    # center_longitude = request.POST.get('neighborhood-center-longitude', '')
    original_neighborhood_slug = request.POST.get('original-neighborhood-slug', '')
    request_origin_template = request.POST.get('request-origin-template', '')

    # add new neighborhood
    if request_origin_template == 'neighborhood_add.html':
        try:
            # verify no pre-existing neighborhood has the slug value submitted 
            pre_existing_neighborhood = Neighborhood.objects.get(slug=neighborhood_slug)
            if pre_existing_neighborhood:
                context = {
                    'template': request_origin_template,
                    'all_neighborhoods': all_neighborhoods,
                    'unavailable_neighborhood_slug': neighborhood_slug,
                    'neighborhood_name': neighborhood_name,
                    # 'center_latitude': center_latitude,
                    # 'center_longitude': center_longitude,
                }
                return render(request, request_origin_template, context)
        except:
            # if no pre-existing neighborhood has the slug value submitted, proceed
            try:
                # init new neighborhood
                neighborhood = Neighborhood(slug=neighborhood_slug, name=neighborhood_name)
                    # center_latitude=center_latitude, center_longitude=center_longitude)
                neighborhood.save()
                context = {
                    'template': template,
                    'all_neighborhoods': all_neighborhoods,
                    'neighborhood': neighborhood,
                }
                return render(request, template, context)
            except Exception as ex:
                dump = getmembers(request)
                context = {
                    'template': request_origin_template,
                    'all_neighborhoods': all_neighborhoods,
                    'exception': ex,
                    'dump': dump,
                }
                return render(request, request_origin_template, context)

    # update existing neighborhood
    if request_origin_template == 'neighborhood_edit.html':
        # TODO this could throw exception if page out of sync with db
        neighborhood = Neighborhood.objects.get(slug=original_neighborhood_slug)
        neighborhood_photos = neighborhood.photo_set.all() 
        # if neighborhood slug has changed...
        if neighborhood_slug != original_neighborhood_slug:
            try:          
                # verify no other neighborhood has the updated slug value submitted 
                other_neighborhood = Neighborhood.objects.filter(slug=neighborhood_slug) 
                if other_neighborhood:
                    context = {
                        'template': request_origin_template,
                        'all_neighborhoods': all_neighborhoods,
                        'unavailable_neighborhood_slug': neighborhood_slug,
                        'neighborhood': neighborhood,
                        'neighborhood_photos': neighborhood_photos,
                    }
                    return render(request, request_origin_template, context)
            except Exception as ex:
                dump = getmembers(request)
                context = {
                    'template': request_origin_template,
                    'all_neighborhoods': all_neighborhoods,
                    'exception': ex,
                    'dump': dump,
                }
                return render(request, request_origin_template, context)

        # if no pre-existing neighborhood has the updated slug value submitted, proceed
        try:
            # update neighborhood
            neighborhood.slug = neighborhood_slug
            neighborhood.name = neighborhood_name
            # neighborhood.center_latitude = center_latitude
            # neighborhood.center_longitude = center_longitude
            neighborhood.save()
            neighborhood_photos = neighborhood.photo_set.all() 

            context = {
                'template': template,
                'all_neighborhoods': all_neighborhoods,
                'neighborhood': neighborhood,
                'neighborhood_photos': neighborhood_photos,
            }
            return render(request, template, context)
        except Exception as ex:
            dump = getmembers(request)
            context = {
                'template': request_origin_template,
                'all_neighborhoods': all_neighborhoods,
                'exception': ex,
                'dump': dump,
            }
            return render(request, request_origin_template, context)
    

def select_photo(request):
    template = 'photo_select.html'
    
    all_neighborhoods = Neighborhood.objects.all()
    photo_uuid = uuid.uuid4()
    
    context = {
        'template': template,
        'all_neighborhoods': all_neighborhoods,
        'photo_uuid': str(photo_uuid),
        'all_aspect_formats': metadata.all_aspect_formats,
        'all_scene_types': metadata.all_scene_types,
        'all_business_types': metadata.all_business_types,
        'all_other_labels': metadata.all_other_labels,
    }

    return render(request, template, context)
        

def save_photo(request):
    template = 'photo_save.html'

    all_neighborhoods = Neighborhood.objects.all()

    #try:
    # bind and process form vars needed for both the 'add' and 'edit' workflows
    request_origin_template = request.POST.get('request-origin-template', '')
    neighborhood_slug = request.POST.get('photo-neighborhood-slug', '')
    uuid = request.POST.get('photo-uuid', '')
    scene_type = request.POST.get('photo-scene-type', '')
    business_type = request.POST.get('photo-business-type', '')
    other_labels = request.POST.get('photo-other-labels', '')

    # photo_edit workflow: process additional form vars, fetch and update photo
    if request_origin_template == "photo_edit.html":
        extracted_text_display = request.POST.get('photo-extracted-text', '')
        extracted_text_search = extracted_text_display.replace('<br/>', ' ')
        try:
            photo = Photo.objects.get(uuid=uuid)
            # update properties
            photo.neighborhood_slug = neighborhood_slug
            photo.scene_type = scene_type
            photo.business_type = business_type
            photo.other_labels = other_labels
            photo.extracted_text_formatted = extracted_text_display
            photo.extracted_text_raw = extracted_text_search
            photo.save()

            file_path = ''

        except Exception as ex:
            print('ex: ' + str(ex))
            dump = getmembers(request)
            context = {
                'dump': dump,
                'exception': ex
            }
            return render(request, template, context)

    # photo_select workflow: process additional form vars, resize image, run OCR analysis 
    elif request_origin_template == "photo_select.html":
        source_file_name = request.POST.get('photo-file-name', '')
        file_path = request.POST.get('photo-file-path', '') 
        date_taken = request.POST.get('photo-date-taken', '')
        file_format = request.POST.get('photo-file-format', '')
        latitude = request.POST.get('photo-latitude', '')
        longitude = request.POST.get('photo-longitude', '')
        width = request.POST.get('photo-width', '')
        height = request.POST.get('photo-height', '')
        aspect_format = request.POST.get('photo-aspect-format', '')

        # process raw vars 
        neighborhood = Neighborhood.objects.get(slug=neighborhood_slug)
        dt_taken = datetime.strptime(date_taken, '%Y:%m:%d %H:%M:%S')
        file_format = metadata.image_file_formats.get(file_format, 'xxx')
        if width:
            width = int(width)
        else:
            width = 0
        if height:
            height = int(height)
        else:
            height = 0

        # analyze photo
        extracted_text_search, extracted_text_display = s3manager.extract_text(uuid, metadata.S3_BUCKET)

        # init and save photo
        photo = Photo(uuid=uuid, source_file_name=source_file_name, neighborhood=neighborhood, 
            dt_taken=dt_taken, file_format=file_format, latitude=latitude, longitude=longitude, 
            width_pixels=width, height_pixels=height, aspect_format=aspect_format,
            scene_type=scene_type, business_type=business_type, other_labels=other_labels,
            extracted_text_raw=extracted_text_search, extracted_text_formatted=extracted_text_display)
        photo.save()

        # resize photos for s3 upload
        aspect_ratio = width / height
        img_dimensions = image_utils.calculate_resized_images(aspect_ratio, width, height)

        # load original image
        response = requests.get(file_path, stream=True)
        orig_img = Image.open(BytesIO(response.content))

        print('@@@@@@@ orig_img.format: ' + str(orig_img.format))
        print('@@@@@@@ orig_img.size: ' + str(orig_img.size))

        s3manager.resize_and_upload(orig_img, 'large', img_dimensions['large'], uuid)
        s3manager.resize_and_upload(orig_img, 'medium', img_dimensions['medium'], uuid)
        s3manager.resize_and_upload(orig_img, 'small', img_dimensions['small'], uuid)

    else:
        context = {
            'template': template,
            'all_neighborhoods': all_neighborhoods,
            'exception': 'Source template was neither photo_select nor photo_edit, unable to save photo.',
        }

        return render(request, template, context)

    context = {
        'template': template,
        'all_neighborhoods': all_neighborhoods,
        'photo': photo,
        'file_path': file_path,
    }

    return render(request, template, context)

    # except Exception as ex:
    #     print('ex: ' + str(ex))
    #     dump = getmembers(request)
    #     context = {
    #         'dump': dump,
    #         'exception': ex
    #     }
    #     return render(request, template, context)


def edit_photo(request, photo_uuid):
    template = 'photo_edit.html'

    all_neighborhoods = Neighborhood.objects.all()

    photo = Photo.objects.get(pk=photo_uuid)

    context = {
        'template': template,
        'all_neighborhoods': all_neighborhoods,
        'all_scene_types': metadata.all_scene_types,
        'all_business_types': metadata.all_business_types,
        'all_other_labels': metadata.all_other_labels,
        'photo': photo,
    }

    return render(request, template, context)


def search_photos(request):
    template = 'photo_search.html'

    all_neighborhoods = Neighborhood.objects.all()

    # bind vars to form data 
    search_criteria = {}
    and_filters = {}
    or_filters = ''
    if request.GET.get('search-scene-type'):
        search_criteria['scene_type'] = request.GET.get('search-scene-type')
        and_filters['scene_type'] = search_criteria['scene_type']
    if request.GET.get('search-business-type'):
        search_criteria['business_type'] = request.GET.get('search-business-type')
        and_filters['business_type'] = search_criteria['business_type']
    if request.GET.get('search-other-labels'):
        search_criteria['other_label'] = request.GET.get('search-other-labels')
        and_filters['other_labels__contains'] = search_criteria['other_label']
    if request.GET.get('search-text'):
        search_criteria['search_text'] = request.GET.get('search-text')
        or_filters = Q(extracted_text_raw__contains = search_criteria['search_text']) | Q(uuid__contains = search_criteria['search_text']) | Q(source_file_name__contains = search_criteria['search_text'])

    matching_photos = Photo.objects.filter(**and_filters)
    if or_filters:
        matching_photos = matching_photos.filter(or_filters)

    context = {
        'template': template,
        'all_neighborhoods': all_neighborhoods,
        'all_scene_types': metadata.all_scene_types,
        'all_business_types': metadata.all_business_types,
        'all_other_labels': metadata.all_other_labels,
        'search_criteria': search_criteria,
        'matching_photos': matching_photos,
    }

    return render(request, template, context)
