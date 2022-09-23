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

from googleapiclient.errors import HttpError

from django.conf import settings
from django.contrib import messages
from django.core.paginator import Paginator
from django.db import IntegrityError
from django.db.models import Q
from django.http import HttpResponse, Http404
from django.shortcuts import render, redirect
from django.template import loader

from lockdownsf.metadata import Status, TagStatus, MAX_RESULTS_PER_PAGE
from lockdownsf.models import Album, Photo, Tag, User
from lockdownsf.services import gphotosapi, image_utils, s3manager
from lockdownsf.services.controller_utils import (
    convert_album_to_json, extract_messages_from_storage, log_and_store_message)


DEFAULT_OWNER = User.objects.get(email=os.environ['DEFAULT_OWNER_EMAIL'])


# https://github.com/lotrekagency/django-google-site-verification/blob/master/google_site_verification/views.py
def google_site_verification(request):
    template = 'google_site_verification.html'

    context = {
        'google_site_verification': settings.GOOGLE_SITE_VERIFICATION
    }

    return render(request, template, context, content_type='text/html')


def index(request):
    template = 'index.html'
    page_title = 'Photo facets home'

    # config vars
    gmaps_api_key = settings.GOOGLE_MAPS_API_KEY

    # process messages
    response_messages = extract_messages_from_storage(request)

    # fetch all albums from db
    all_albums = Album.objects.filter(owner=DEFAULT_OWNER, center_latitude__isnull=False, center_longitude__isnull=False)
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
        # fetch all photos per album; ignore albums lacking tagged photos 
        # album_photos = album.photo_set.filter(tags__isnull=False, tags__in=active_tags).distinct()
        album_photos = album.photo_set.filter(tags__isnull=False).distinct()
        if not album_photos:
            continue
        # fetch media items from gphotos api to populate photo metadata
        # fields_to_populate = ['thumb_url', 'mime_type', 'width', 'height']
        # populate_fields_from_gphotosapi(album_photos, fields_to_populate)
        # album.photos = album_photos
        # populate json objects for live site js
        album_json = convert_album_to_json(album)
        photo_collection_json.append(album_json)
        all_albums_json[album.id] = album.name
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
        'gmaps_api_key': gmaps_api_key,
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

    # config vars
    gmaps_api_key = settings.GOOGLE_MAPS_API_KEY

    # process messages
    response_messages = extract_messages_from_storage(request)

    # fetch all albums from db
    all_albums = Album.objects.filter(owner=DEFAULT_OWNER, center_latitude__isnull=False, center_longitude__isnull=False)

    if not all_albums:
        log_and_store_message(request, messages.ERROR, 'Failure to load albums to build photo collection')
        return redirect(f"/lockdownsf/")
    
    # build json objects to be passed to live site js
    all_albums_json = {}
    for album in all_albums:
        # ignore albums lacking tagged photos
        album_photos = album.photo_set.filter(tags__isnull=False).distinct()
        if not album_photos:
            continue
        all_albums_json[album.id] = album.name

    try:
        selected_album = Album.objects.get(pk=album_id)
    except Exception as ex:
        log_and_store_message(request, messages.ERROR, 
            f"[{ex.__class__.__name__}]: Failure to load album with google photos id [{album_id}]. Details: {ex}")
        return redirect(f"/lockdownsf/")

    # fetch tagged photos for album
    selected_album_photos = selected_album.photo_set.filter(tags__isnull=False).distinct()
    if selected_album_photos:
        # fetch media items from gphotos api to populate photo metadata
        # fields_to_populate = ['thumb_url', 'mime_type', 'width', 'height']
        # populate_fields_from_gphotosapi(selected_album_photos, fields_to_populate)
        selected_album.photos = selected_album_photos

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
        'gmaps_api_key': gmaps_api_key,
        # 'all_albums': all_albums,
        'selected_album_id': selected_album.id,
        'photo_collection_json': json.dumps(photo_collection_json, indent=4),
        'all_albums_json': json.dumps(all_albums_json, indent=4),
        'map_meta_json': json.dumps(map_meta_json, indent=4),
    }

    return render(request, template, context)


def sign_s3(request):

    # object_name = urllib.parse.quote_plus(request.GET['file_name'])
    file_name = request.GET['file_name']
    file_type = request.GET['file_type']

    print(f"settings.AWS_ACCESS_KEY_ID: [{settings.AWS_ACCESS_KEY_ID}]")
    print(f"settings.AWS_SECRET_ACCESS_KEY [{settings.AWS_SECRET_ACCESS_KEY}]")
    print(f"settings.S3_BUCKET [{settings.S3_BUCKET}]")

    s3 = boto3.client('s3',
         aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
         aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY)

    presigned_post = s3.generate_presigned_post(
        Bucket = settings.S3_BUCKET,
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
        'url': f"https://{settings.S3_BUCKET}.s3.amazonaws.com/{file_name}",
    })

    return HttpResponse(data, content_type='json')


def manage(request):
    template = 'manage.html'
    page_title = 'Management console'

    # process messages
    response_messages = extract_messages_from_storage(request)

    # form backing data
    all_albums = Album.objects.filter(owner=DEFAULT_OWNER)

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

    all_albums = Album.objects.filter(owner=DEFAULT_OWNER)
    if all_albums:
        for album in all_albums:
            album.photo_count = len(album.photo_set.all())

    context = {
        'template': template,
        'page_title': page_title,
        'response_messages': response_messages,
        'all_albums': all_albums,
    }
    
    return render(request, template, context)

    
def album_view(request, album_id, page_number=None):
    template = 'album_view.html'
    page_title = 'Album details'

    # form backing data
    all_albums = Album.objects.filter(owner=DEFAULT_OWNER)

    if not album_id:
        log_and_store_message(request, messages.ERROR, 'Failure to fetch album, no album_id was specified')
        # process messages
        response_messages = extract_messages_from_storage(request)
        context = {
            'template': template,
            'page_title': page_title,
            'response_messages': response_messages,
            'all_albums': all_albums,
        }
        return render(request, template, context)

    # fetch album and mapped photos from db
    try:
        album = Album.objects.get(pk=album_id)
        mapped_photos = album.photo_set.all().order_by('dt_taken')
    except Exception as ex:
        log_and_store_message(request, messages.ERROR, 
            f"[{ex.__class__.__name__}]: Failure to fetch album [{album_id}]. Details: {ex}")
        return redirect(f"/lockdownsf/manage/album_listing/")
    
    page_title = f"{page_title}: {album.name}"

    # pagination
    if page_number:
        page_number = int(page_number)
    else:
        page_number = 1
    total_results_count = len(mapped_photos)
    paginator = Paginator(mapped_photos, MAX_RESULTS_PER_PAGE)
    page_results = paginator.page(page_number) 
    prev_page_number = None
    next_page_number = None
    if page_results.has_previous():
        prev_page_number = page_number - 1
    if page_results.has_next():
        next_page_number = page_number + 1

    # fetch media items from gphotos api to populate image metadata
    fields_to_populate = ['thumb_url', 'mime_type', 'width', 'height']
    # populate_fields_from_gphotosapi(page_results, fields_to_populate)

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
    album_id = request.POST.get('album-id', '')
    # update_album_name_flag = request.POST.get('update-album-name-flag', '')
    album_name = request.POST.get('album-name', '')

    if not album_id:
        log_and_store_message(request, messages.ERROR, "Failed to update album, no album id was set.")
        return redirect(f"/lockdownsf/manage/album_listing/")

    # if update_album_name_flag:
    if not album_name:
        log_and_store_message(request, messages.ERROR, "Failed to update album, album name cannot be empty.")
        return redirect(f"/lockdownsf/manage/album_view/{album_id}/")

    # update album name in db
    try:
        album = Album.objects.get(pk=album_id)
        album.name = album_name
        album.save()
    except Exception as ex:
        log_and_store_message(request, messages.ERROR,
            f"[{ex.__class__.__name__}]: Failed to update album with id [{album_id}]. Details: {ex}")
        return redirect(f"/lockdownsf/manage/album_listing/")
    
    # if everything fired without exceptions, return success
    log_and_store_message(request, messages.SUCCESS,
        f"Successfully updated album [{album_id}] in photo-facets db.")
    return redirect(f"/lockdownsf/manage/album_view/{album_id}/")


def album_select_new_photos(request):
    template = 'album_select_new_photos.html'
    page_title = 'Select photos for import into album'

    # process messages
    response_messages = extract_messages_from_storage(request)

    # assign form data to vars and validate input
    add_to_album_id = request.POST.get('add-to-album-id', '')
    if not add_to_album_id:
        add_to_album_id = request.GET.get('add-to-album-id', '')

    # generate uuid for tmp s3 dir to store photos to if any are uploaded
    tmp_dir_uuid = str(uuid.uuid4())

    # form backing data
    all_albums = Album.objects.filter(owner=DEFAULT_OWNER)

    context = {
        'template': template,
        'page_title': page_title,
        'response_messages': response_messages,
        'all_albums': all_albums,
        'tmp_dir_uuid': tmp_dir_uuid,
        'add_to_album_id': add_to_album_id,
    }
    
    return render(request, template, context)


def album_import_new_photos(request):
    """Extract data from s3 photos and add them to db: 
    - if new album:
    -   init and save Album to db with status NEWBORN 
    - else:
    -   fetch Album from db
    - download the photos from s3
    - extract GPS and timestamp info from photos
    - init and save Photos to db, including Album mapping, with status set to LOADED_AND_MAPPED
    - calculate aggregate GPS data for Album, set status to LOADED_AND_MAPPED
    - if existing Album: 
    -   copy photo files to Album's pre-existing s3 dir
    -   delete original photos and temp dir
    """
    
    # TODO workflow is dependent on filename uniqueness, which is one reason it's best to stick with 
    # folder upload rather than drag-and-drop

    # assign form data to vars and validate input
    images_to_upload = request.POST.getlist('images-to-upload', [])
    print(f"images_to_upload: [{images_to_upload}]")
    album_id = request.POST.get('select-album-id', '')
    album_name = request.POST.get('new-album-name', '')
    album_s3_dir_uuid = request.POST.get('tmp-dir-uuid', '')
    
    if not images_to_upload:
        log_and_store_message(request, messages.ERROR,
            "Failed to import photos, no photos were queued for upload. At least one photo is required.")
        return redirect(f"/lockdownsf/manage/album_select_new_photos/")

    # if adding photos to existing album: fetch album from db
    if album_id:
        try:
            album = Album.objects.get(pk=album_id)
        except Exception as ex:
            log_and_store_message(request, messages.ERROR,
                f"[{ex.__class__.__name__}]: Failed to import photos, no album found matching album_id [{album_id}]. Details: {ex}")
            return redirect(f"/lockdownsf/manage/album_select_new_photos/")
    
    # if adding photos to new album: create new album in db
    else:
        if not album_name:
            log_and_store_message(request, messages.ERROR,
                "Failed to create album, no album title was specified.")
            return redirect(f"/lockdownsf/manage/album_select_new_photos/")

        # insert Album into db with status NEWBORN
        album = Album(name=album_name, owner=DEFAULT_OWNER, status=Status.NEWBORN.name)
        album.s3_dir = album_s3_dir_uuid 
        album.save()

    # for both new and existing album workflow: download photos from s3, extract GPS and timestamp info 
    photos = []
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
        # extracted_text_search, extracted_text_display = s3manager.extract_text(image_file_name, settings.S3_BUCKET)

        # init and save Photos to db, with status NEWBORN, not yet mapped to Album
        photo = Photo(
            album=album, owner=DEFAULT_OWNER, file_name=image_file_name, mime_type=pil_image.format, dt_taken=dt_taken, 
            latitude=lat, longitude=lng, status=Status.LOADED_AND_MAPPED.name)
            # extracted_text_search=extracted_text_search, extracted_text_display=extracted_text_display)
        photo.save()
        photos.append(photo)

    # for both new and existing album workflow: calculate album lat/lng and furthest N-S or E-W distance between points
    # freshly fetch album to get all of its mappings - technically unnecessary for new albums, but just cleaner/streamlined this way
    album = Album.objects.get(pk=album.id)
    ctr_lat, ctr_lng, zoom_level, photos_having_gps = image_utils.avg_gps_info(album.photo_set.all())
    # update Album in db with center lat/lng, zoom level, and status LOADED_AND_MAPPED
    album.center_latitude = ctr_lat
    album.center_longitude = ctr_lng
    album.map_zoom_level = zoom_level
    album.photos_having_gps = photos_having_gps
    album.status = Status.LOADED_AND_MAPPED.name
    album.save()

    log_and_store_message(request, messages.SUCCESS,
        f"Successfully mapped [{len(photos)}] new photos to album [{album.name}]")

    # if adding to existing album, move photos to correct s3 bucket
    if album_s3_dir_uuid != album.s3_dir:
        s3manager.move_photos(album_s3_dir_uuid, album.s3_dir, image_file_names)
    
    return redirect(f"/lockdownsf/manage/album_view/{album.id}/")


def album_delete(request):

    # assign form data to vars and validate input
    album_id = request.POST.get('album-id', '')

    if not album_id:
        log_and_store_message(request, messages.ERROR, 'Unable to delete album, no album_id was specified.')

    else:
        try:
            # fetch album from db, then delete it and its associated s3 data
            album = Album.objects.get(pk=album_id)
            album_s3_dir = album.s3_dir
            album.delete()
            s3manager.delete_dir(album_s3_dir)
            # generate success and failure messages
            log_and_store_message(request, messages.SUCCESS, f"Successfully deleted album [{album.name}]")
        except Exception as ex:
            log_and_store_message(request, messages.ERROR, 
                f"[{ex.__class__.__name__}]: Failed to delete album with album_id [{album_id}]. Details: {ex}")

    return redirect(f"/lockdownsf/manage/album_listing/")


def album_photos_delete(request):

    # assign form data to vars and validate input 
    album_id = request.POST.get('album-id', '')
    photo_ids = request.POST.getlist('photo-ids', '')

    if not album_id:
        log_and_store_message(request, messages.ERROR, 
            f"Failure to delete photos from album, no album_id was specified")
        return redirect(f"/lockdownsf/manage/album_listing/")

    if not photo_ids:
        log_and_store_message(request, messages.ERROR, 
            f"Failure to delete photos from album [{album_id}], no photos were specified")
        return redirect(f"/lockdownsf/manage/album_view/{album_id}/")

    success_photo_ids = []
    failed_photo_ids = []
    album_label = album_id

    # fetch photos from db, delete them, and track deleted items in list 
    for photo_id in photo_ids:
        try:
            photo = Photo.objects.get(pk=photo_id)
            s3_dir = photo.album.s3_dir
            photo.delete()
            s3manager.delete_file(f"{s3_dir}/{photo.file_name}")
            success_photo_ids.append(photo_id)
        except Exception as ex:
            print(f"Failed to delete photo id [{photo.id}] file_name [{photo.file_name}] album id [{album_id}] from either db or from s3 dir [{s3_dir}]. Details: {ex}")
            failed_photo_ids.append(photo_id)

    # fetch album and update GPS data based on remaining photos
    try:
        album = Album.objects.get(pk=album_id)
        album_label = album.name  
        ctr_lat, ctr_lng, zoom_level, photos_having_gps = image_utils.avg_gps_info(album.photo_set.all())
        album.center_latitude = ctr_lat
        album.center_longitude = ctr_lng
        album.map_zoom_level = zoom_level
        album.photos_having_gps = photos_having_gps
        album.save()
    except Exception as ex:
        log_and_store_message(request, messages.ERROR, 
            f"[{ex.__class__.__name__}]: After deleting photos from album [{album_id}], failure to fetch album or update its GPS info in db. Details: {ex}")
        
    # generate success and failure messages
    if success_photo_ids:
        log_and_store_message(request, messages.SUCCESS, 
            f"Successfully deleted [{len(success_photo_ids)}] photos from album [{album_label}]")
    if failed_photo_ids:
        log_and_store_message(request, messages.ERROR, 
            f"Failed to delete [{len(failed_photo_ids)}] photos from album [{album_label}]")
        log_and_store_message(request, messages.ERROR, f"Failed photos: [{failed_photo_ids}]")

    return redirect(f"/lockdownsf/manage/album_view/{album_id}/")


def photo_search(request):
    template = 'photo_search.html'
    page_title = 'Search for photos'

    # process messages
    response_messages = extract_messages_from_storage(request)

    # form backing data
    all_albums = Album.objects.filter(owner=DEFAULT_OWNER)
    all_tags = Tag.objects.filter(owner=DEFAULT_OWNER)

    # assign form data to vars and assemble query filters
    search_criteria = {}
    and_filters = {}
    or_filters = ''
    page_number = 1
    if request.GET.get('page-number'):
        page_number = int(request.GET.get('page-number'))
    if request.GET.get('search-album'):
        search_album = Album.objects.get(pk=request.GET.get('search-album'))
        and_filters['album'] = search_album.id
        search_criteria['search_album_name'] = search_album.name
        search_criteria['search_album_id'] = search_album.id
    if request.GET.get('search-tag'):
        search_tag = Tag.objects.get(name=request.GET.get('search-tag'))
        and_filters['tags'] = search_tag.id
        search_criteria['search_tag_name'] = search_tag.name
    if request.GET.get('search-text'):
        search_text = request.GET.get('search-text').lower()
        or_filters = Q(extracted_text_search__icontains = search_text) | Q(file_name__icontains = search_text) | Q(description__icontains = search_text)
        search_criteria['search_text'] = search_text

    # fetch photos from db
    matching_photos = Photo.objects.filter(**and_filters).order_by('-dt_taken')
    if or_filters:
        matching_photos = matching_photos.filter(or_filters).order_by('-dt_taken')
    
    # pagination
    total_results_count = len(matching_photos)
    paginator = Paginator(matching_photos, MAX_RESULTS_PER_PAGE)
    page_results = paginator.page(page_number) 
    prev_page_number = None
    next_page_number = None
    if page_results.has_previous():
        prev_page_number = page_number - 1
    if page_results.has_next():
        next_page_number = page_number + 1

    # fetch media items from gphotos api to populate image metadata
    fields_to_populate = ['thumb_url', 'mime_type', 'width', 'height']
    # populate_fields_from_gphotosapi(page_results, fields_to_populate)

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


def photo_view(request, photo_id):
    template = 'photo_view.html'
    page_title = 'Photo details'

    # form backing data
    all_albums = Album.objects.filter(owner=DEFAULT_OWNER)
    all_tags = Tag.objects.filter(owner=DEFAULT_OWNER)

    # fetch photo from db
    try:
        photo = Photo.objects.get(pk=photo_id)
    except Exception as ex:
        log_and_store_message(request, messages.ERROR,
            f"[{ex.__class__.__name__}]: Failure to fetch photo, no match for photo_id [{photo_id}]")
        return redirect(f"/lockdownsf/manage/photo_search/")

    # fetch album from db to determine previous and next photos for sequential navigation
    mapped_photos = photo.album.photo_set.all().order_by('dt_taken')

    # store all mapped photo_ids to list, get index of current photo
    album_photo_ids = [p.id for p in mapped_photos]
    curr_index = album_photo_ids.index(photo_id)

    # get photo_ids for previous and next index
    prev_photo_id = None
    next_photo_id = None
    if curr_index > 0:
        prev_photo_id = album_photo_ids[curr_index - 1]
    if curr_index < len(album_photo_ids) - 1:
        next_photo_id = album_photo_ids[curr_index + 1]

    # fetch media items from gphotos api to populate image metadata
    fields_to_populate = ['thumb_url', 'mime_type', 'width', 'height']
    # populate_fields_from_gphotosapi([photo], fields_to_populate)

    # photo_location = { 
    #     'lat': str(photo.latitude), 
    #     'lng': str(photo.longitude) 
    # }

    # process messages
    response_messages = extract_messages_from_storage(request)

    context = {
        'template': template,
        'page_title': page_title,
        'response_messages': response_messages,
        'all_albums': all_albums,
        'all_tags': all_tags,
        'photo_id': photo_id, # TODO this is legacy I think
        'photo': photo,
        'prev_photo_id': prev_photo_id,
        'next_photo_id': next_photo_id,
        # 'photo_location_json': json.dumps(photo_location, indent=4),
    }

    return render(request, template, context)


def photo_edit(request):

    # assign form data to vars 
    photo_id = request.POST.get('photo-id', '')
    update_description_flag = request.POST.get('update-description-flag', '')
    new_description = request.POST.get('description', '')
    update_tags_flag = request.POST.get('update-tags-flag', '')
    new_tag_ids = request.POST.getlist('tag-ids', [])
    update_file_name_flag = request.POST.get('update-file-name-flag', '')
    new_file_name = request.POST.get('file-name', '')
    update_dt_taken_flag = request.POST.get('update-dt-taken-flag', '')
    new_dt_taken = request.POST.get('dt-taken', '')

    # handle missing data
    if not photo_id:
        log_and_store_message(request, messages.ERROR, f"Failure to update photo, photo_id was not set")
        return redirect(f"/lockdownsf/manage/photo_search/")

    if not (update_description_flag or update_tags_flag or update_file_name_flag or update_dt_taken_flag):
        log_and_store_message(request, messages.ERROR, 
            f"Failure to update photo, no data changes were submitted")
        return redirect(f"/lockdownsf/manage/photo_view/{photo_id}/")

    # fetch photo from db
    try:
        photo = Photo.objects.get(pk=photo_id)
    except Exception as ex:
        log_and_store_message(request, messages.ERROR,
            f"[{ex.__class__.__name__}]: Failure to update photo, no match for photo_id [{photo_id}]")
        return redirect(f"/lockdownsf/manage/photo_search/")

    # description update - update db object 
    if update_description_flag:
        # db object update
        photo.description = new_description

    # tags updates - update db object
    if update_tags_flag:
        # process form data
        if new_tag_ids:
            new_tag_ids = [int(tag_id) for tag_id in new_tag_ids]
        old_tag_ids = [old_tag.id for old_tag in photo.tags.all()]
        tag_ids_to_remove = list(set(old_tag_ids) - set(new_tag_ids))
        tag_ids_to_add = list(set(new_tag_ids) - set(old_tag_ids))

        # delete old tags that aren't in new list
        for tag_id_to_remove in tag_ids_to_remove:
            try:
                tag_to_remove = Tag.objects.get(pk=tag_id_to_remove)
                photo.tags.remove(tag_to_remove)
            except Exception as ex:
                log_and_store_message(request, messages.ERROR,
                    f"[{ex.__class__.__name__}]: Failure to remove tag, no tag with id [{tag_id_to_remove}] found in db")

        # add new tags that aren't in old list
        for tag_id_to_add in tag_ids_to_add:
            try:
                tag_to_add = Tag.objects.get(pk=tag_id_to_add)
                photo.tags.add(tag_to_add)
            except Exception as ex:
                log_and_store_message(request, messages.ERROR,
                    f"[{ex.__class__.__name__}]: Failure to add tag, no tag with id [{tag_id_to_add}] found in db")

    # file_name update - update db object 
    if update_file_name_flag:
        # db object update
        photo.file_name = new_file_name

    # dt_taken update - update db object 
    if update_dt_taken_flag:
        # transform datetime value and update db object 
        # new_dt_taken = datetime.strptime(new_dt_taken, '%Y-%m-%dT%H:%M:%SZ') 
        photo.dt_taken = new_dt_taken

    # write accumulated changes to db
    try:
        photo.save()
        log_and_store_message(request, messages.SUCCESS,
            f"Successfully updated photo [{photo_id}] to db") 
    except Exception as ex:
        log_and_store_message(request, messages.ERROR,
            f"[{ex.__class__.__name__}]: Failure to update photo [{photo_id}] to db. Details: {ex}")

    return redirect(f"/lockdownsf/manage/photo_view/{photo_id}/")


def tag_listing(request):
    template = 'tag_listing.html'
    page_title = 'Tag listing'

    # process messages
    response_messages = extract_messages_from_storage(request)

    # form backing data
    all_albums = Album.objects.filter(owner=DEFAULT_OWNER)
    all_tag_statuses = [ts.name for ts in TagStatus]
        
    all_tags = Tag.objects.all().order_by('name')
    for tag in all_tags:
        tag.photo_count = len(tag.photo_set.all())
        
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
        new_tag = Tag(name=new_tag_name, status=TagStatus.ACTIVE.name, owner=DEFAULT_OWNER)
        new_tag.save()
        log_and_store_message(request, messages.SUCCESS, f"Successfully created new tag [{new_tag.name}].")
        return redirect(f"/lockdownsf/manage/tag_listing/")

    except Exception as ex:
        log_and_store_message(request, messages.ERROR, 
            f"[{ex.__class__.__name__}]: Failed to create new tag [{new_tag_name}]. Details: {ex}")
        return redirect(f"/lockdownsf/manage/tag_listing/")


def tag_edit(request):

    # assign form data to vars and validate input
    tag_id = request.POST.get('tag-id', '')
    if not tag_id:
        log_and_store_message(request, messages.ERROR, f"Failed to edit tag, no tag id was specified.")
        return redirect(f"/lockdownsf/manage/tag_listing/")

    tag_status_field = f"tag-status-select-{tag_id}"
    tag_status = request.POST.get(tag_status_field, '')

    # for key, value in request.POST.items():
    #     print(f"key: {key} | value: {value}") 

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
        log_and_store_message(request, messages.ERROR, 
            f"[{ex.__class__.__name__}]: Failed to fetch and update tag with tag_id [{tag_id}]. Details: {ex}")
        return redirect(f"/lockdownsf/manage/tag_listing/")


def extract_ocr_text(request):

    # assign form data to vars and validate input
    request_scope = request.POST.get('request-scope', '')
    object_id = request.POST.get('object-id', '')

    if not (request_scope and object_id):
        log_and_store_message(request, messages.ERROR, 
            "Failure to extract OCR text, both request_scope and object_id are required")
        return redirect(f"/lockdownsf/manage/")  # TODO where should this go?

    if request_scope not in ['album', 'photo']:
        log_and_store_message(request, messages.ERROR, 
            "Failure to extract OCR text, request_scope must be 'album' or 'photo'")
        return redirect(f"/lockdownsf/manage/")  # TODO where should this go?

    # generate uuid for tmp s3 dir to store photos to if any are uploaded
    tmp_dir_uuid = str(uuid.uuid4())
    
    if request_scope == 'photo':
        # fetch photo from db
        try:
            photo = Photo.objects.get(pk=object_id)
        except Exception as ex:
            log_and_store_message(request, messages.ERROR, 
                f"[{ex.__class__.__name__}]: Failure to extract OCR text, no image found in db matching id [{object_id}]")
            return redirect(f"/lockdownsf/manage/")  # TODO where should this go?

        # # copy image from gphotos to s3 for OCR extraction
        # try:
        #     s3_file_name = copy_gphotos_image_to_s3(external_id, tmp_dir_uuid)
        # except Exception as ex:
        #     log_and_store_message(request, messages.ERROR, 
        #         f"[{ex.__class__.__name__}]: {ex}")
        #     return redirect(f"/lockdownsf/manage/photo_view/{external_id}/")

        s3_file_name = ''  # TODO how do we get this?

        # extract OCR text from image on s3
        extracted_text_search, extracted_text_display = s3manager.extract_text(s3_file_name, settings.S3_BUCKET)

        # add extracted text to photo and save 
        photo.extracted_text_search = extracted_text_search
        photo.extracted_text_display = extracted_text_display
        photo.save()

        # delete photo from s3
        s3manager.delete_dir(tmp_dir_uuid, [object_id])

        return redirect(f"/lockdownsf/manage/photo_view/{object_id}/")

    if request_scope == "album":
        # fetch photos mapped to album from db
        try:
            album = Album.objects.get(pk=object_id)
            album_photos = album.photo_set.all()
        except Exception as ex:
            log_and_store_message(request, messages.ERROR, 
                f"[{ex.__class__.__name__}]: Failure to extract OCR text, problem fetching images associated to album with id [{object_id}]")
            return redirect(f"/lockdownsf/manage/album_view/{object_id}/")  # should this redirect to another url?

        for photo in album_photos:
            # # copy image from gphotos to s3 for OCR extraction
            # try:
            #     s3_file_name = copy_gphotos_image_to_s3(photo.external_id, tmp_dir_uuid)
            # except Exception as ex:
            #     log_and_store_message(request, messages.ERROR, 
            #         f"[{ex.__class__.__name__}]: {ex}")
            #     continue

            s3_file_name = ''  # TODO how do we get this?

            # extract OCR text from image on s3
            extracted_text_search, extracted_text_display = s3manager.extract_text(s3_file_name, settings.S3_BUCKET)

            # add extracted text to photo and save 
            photo.extracted_text_search = extracted_text_search
            photo.extracted_text_display = extracted_text_display
            photo.save()

            # delete photos from s3
            s3manager.delete_dir(tmp_dir_uuid, [p.id for p in album_photos if p.id])

        return redirect(f"/lockdownsf/manage/album_view/{object_id}/")
