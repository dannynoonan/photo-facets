import boto3
from datetime import datetime
import exifread
from inspect import getmembers
from io import BytesIO
import json
import os
from PIL import Image, ExifTags
import requests
from pprint import pprint
import uuid

from django.contrib import messages
from django.db.models import Q
from django.http import HttpResponse, Http404
from django.shortcuts import render, redirect
from django.template import loader

from lockdownsf import metadata
from lockdownsf.models import Album, MediaItem, Neighborhood, Photo, Tag, User
from lockdownsf.services import gphotosapi, image_utils, s3manager
from lockdownsf.services.controller_utils import extract_messages_from_storage, log_and_store_message, populate_thumb_urls_from_gphotosapi, update_mediaitems_with_gphotos_data

OWNER = User.objects.get(email='andyshirey@gmail.com')


def index(request):
    template = 'index.html'

    # fetch all albums from db
    all_albums = Album.objects.all()

    if all_albums:
        for album in all_albums:
            # fetch all media_items per album; ignore albums lacking media items
            album_media_items = album.mediaitem_set.all()
            if not album_media_items:
                continue
            # fetch media_items from gphotos api to populate thumb_urls
            populate_thumb_urls_from_gphotosapi(album_media_items)
            album.media_items = album_media_items

    # build photo_collection json that will be passed to page js
    photo_collection_json = []
    for album in all_albums:
        album_media_items_json = []
        if not hasattr(album, 'media_items'):
            continue
        for media_item in album.media_items:
            facets_json = []
            if media_item.facets:
                facets_json.extend(media_item.facets.split('|'))
            media_item_json = {
                'external_id': media_item.external_id,
                'longitude': str(media_item.longitude),
                'latitude': str(media_item.latitude),
                'thumb_url': media_item.thumb_url,
                'facets': facets_json
            }
            album_media_items_json.append(media_item_json)
        album_json = {
            'external_id': album.external_id,
            'media_items': album_media_items_json,
        }
        photo_collection_json.append(album_json)

    context = {
        'template': template,
        'all_albums': all_albums,
        'photo_collection_json': json.dumps(photo_collection_json, indent=4)
    }

    return render(request, template, context)


def neighborhood(request, neighborhood_slug):
    template = 'neighborhood.html'

    try:
        neighborhood = Neighborhood.objects.get(slug=neighborhood_slug)
        photos = neighborhood.photo_set.all() 
        context = {
            'neighborhood': neighborhood,
            'photos': photos,
        }
        return render(request, template, context)
    except Neighborhood.DoesNotExist:
        raise Http404("No neighborhood found for slug %s" % neighborhood_slug)


def sign_s3(request):
    # S3_BUCKET = os.environ.get('S3_BUCKET')
    # S3_BUCKET = settings.S3_BUCKET_NAME

    # file_name = request.args.get('file_name')
    # file_type = request.args.get('file_type')

    # object_name = urllib.parse.quote_plus(request.GET['file_name'])
    file_name = request.GET['file_name']
    file_type = request.GET['file_type']

    s3 = boto3.client('s3')

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
        'url': 'https://' + metadata.S3_BUCKET + '.s3.amazonaws.com/' +  file_name,
    })

    return HttpResponse(data, content_type='json')


def manage(request):
    template = 'manage.html'

    all_albums = Album.objects.all()

    context = {
        'template': template,
        'all_albums': all_albums,
        'all_facets': metadata.all_facets,
    }
    
    return render(request, template, context)


def file_uploader(request):
    template = 'file_uploader.html'

    all_albums = Album.objects.all()

    context = {
        'template': template,
        'all_albums': all_albums,
    }
    
    return render(request, template, context)


def album_listing(request):
    template = 'album_listing.html'

    # process messages
    success_messages, error_messages = extract_messages_from_storage(request)

    all_albums = Album.objects.all()
    if all_albums:
        for album in all_albums:
            album.mediaitem_count = len(album.mediaitem_set.all())

    context = {
        'template': template,
        'success_messages': success_messages,
        'error_messages': error_messages,
        'all_albums': all_albums,
    }
    
    return render(request, template, context)


def album_import(request):
    template = 'album_import.html'

    # form backing data
    all_albums = Album.objects.all()

    context = {
        'template': template,
        'all_albums': all_albums,
    }
    
    return render(request, template, context)


def album_delete(request):

    # bind vars to form data 
    album_external_id = request.POST.get('album-external-id', '')

    if not album_external_id:
        log_and_store_message(request, messages.ERROR, 'Unable to delete album, album_external_id was not set.')

    else:
        try:
            # fetch album from db, then delete it
            album = Album.objects.get(external_id=album_external_id)
            album.delete()
            log_and_store_message(request, messages.SUCCESS, f"Successfully deleted album [{album_external_id}]")

        except Exception as ex:
            log_and_store_message(request, messages.ERROR, 
                f"Failed to delete album with external_id [{album_external_id}]. Exception: {ex}")

    return redirect(f"/lockdownsf/manage/album_listing/")


def album_media_items_delete(request):

    # bind vars to form data 
    album_external_id = request.POST.get('album-external-id', '')
    media_item_external_ids = request.POST.getlist('media-item-external-ids', '')

    if not (album_external_id and media_item_external_ids):
        log_and_store_message(request, messages.ERROR, 
            f"Invalid request to delete media items [{media_item_external_ids}] from album [{album_external_id}]")

    else:
        successful_media_item_ids = []
        failed_media_item_ids = []

        # fetch media_items from db, then delete them
        for media_item_id in media_item_external_ids:
            try:
                media_item = MediaItem.objects.get(external_id=media_item_id)
                media_item.delete()
                successful_media_item_ids.append(media_item_id)

            except Exception as ex:
                failed_media_item_ids.append(media_item_id)

        if successful_media_item_ids:
            log_and_store_message(request, messages.SUCCESS, 
                f"Successfully deleted [{len(successful_media_item_ids)}] media items from album [{album_external_id}]")
            log_and_store_message(request, messages.SUCCESS, f"Successful media items: [{successful_media_item_ids}]")
        if failed_media_item_ids:
            log_and_store_message(request, messages.ERROR, 
                f"Failed to delete [{len(failed_media_item_ids)}] media items from album [{album_external_id}]")
            log_and_store_message(request, messages.ERROR, f"Failed media items: [{failed_media_item_ids}]")

    return redirect(f"/lockdownsf/manage/album_view/{album_external_id}/")

    
def album_view(request, album_external_id):
    template = 'album_view.html'

    # process messages
    success_messages, error_messages = extract_messages_from_storage(request)

    # form backing data
    all_albums = Album.objects.all()

    # TODO some way to identify where the photos uploaded to s3 temporarily are

    if album_external_id and album_external_id != "_":
        """If we're loading a pre-existing album: fetch it from the db and the gphotos api"""
        # fetch album and mapped media_items from db
        album = Album.objects.get(external_id=album_external_id)
        mapped_media_items = album.mediaitem_set.all()

        # fetch media_items from gphotos api to populate thumb_urls
        populate_thumb_urls_from_gphotosapi(mapped_media_items)
        
        # TODO diff media_items returned by gphotos api call to those mapped to db album
        # gphotos_media_items = gphotosapi.get_photos_for_album(album.external_id)

        context = {
            'template': template,
            'success_messages': success_messages,
            'error_messages': error_messages,
            'all_albums': all_albums,
            'album': album,
            'mapped_media_items': mapped_media_items,
        }
    else:
        log_and_store_message(request, messages.ERROR, 'Failure to fetch album, no external_id was specified')
        context = {
            'template': template,
            'error_messages': error_messages,
            'all_albums': all_albums,
        }

    return render(request, template, context)


def album_create(request):
    """Upload photos and create new album: 
    - init and save Album to db with status PENDING and no external_id
    - download the photos from s3
    - extract location and OCR text info from photos
    - init and save MediaItems to db, mapped to Album but with status PENDING and no external_id
    - create gphotos album
    - update Album in db with status ACTIVE, lat/lng, and external_id set
    - upload and map gphotos mediaItems to gphotos album
    - update MediaItems in db with statuses ACTIVE and external_ids set
    - delete photos from s3
    """
    
    # TODO workflow is entirely dependent on filename uniqueness!!!

    # bind vars to form data 
    album_title = request.POST.get('album-title', '')
    images_to_upload = request.POST.getlist('images-to-upload', [])

    if not (album_title and images_to_upload):
        if not album_title:
            log_and_store_message(request, messages.ERROR,
                "Failed to create album, no album title was specified.")
        if not images_to_upload:
            log_and_store_message(request, messages.ERROR,
                "Failed to create album, no images were queued for upload. At least one image is required.")

        return redirect(f"/lockdownsf/manage/album_import/")

    # insert Album into db with status PENDING and no external_id
    album = Album(name=album_title, owner=OWNER, external_resource=metadata.ExternalResource.GOOGLE_PHOTOS_V1.name, 
        status=metadata.Status.NEWBORN.name)
    album.save()

    media_items = []
    for image_path in images_to_upload:
        image_file_name = image_path.split('/')[-1:][0]   

        # download the photos from s3
        response = requests.get(image_path, stream=True)
        pil_image = Image.open(BytesIO(response.content))

        # bind vars to image metadata
        width, height = pil_image.size

        # extract location and timestamp info
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
        extracted_text_raw, extracted_text_formatted = s3manager.extract_text(image_file_name, metadata.S3_BUCKET)

        # init and save MediaItems to db, mapped to Album but with status PENDING and no external_id
        media_item = MediaItem(
            file_name=image_file_name, owner=OWNER, external_resource=metadata.ExternalResource.GOOGLE_PHOTOS_V1.name, 
            album=album, mime_type=pil_image.format, dt_taken=dt_taken, width=width, height=height, 
            latitude=lat, longitude=lng, extracted_text=extracted_text_raw, status=metadata.Status.NEWBORN.name)
        media_item.save()
        media_items.append(media_item)

    # create gphotos album
    album_response = gphotosapi.init_new_album_simple(album_title)

    if not album_response or not album_response['id']:
        log_and_store_message(request, messages.ERROR, "@@@@@@ ERROR GRASSHOPPER DISASSEMBLE")

        return redirect(f"/lockdownsf/manage/album_import/")

    # TODO calculate album lat/lng and zoom

    # update Album in db with status LOADED, lat/lng, and external_id set
    album.external_id = album_response['id']
    album.status = metadata.Status.LOADED.name
    album.save()

    # upload and map gphotos mediaItems to gphotos album
    mapped_images_response = gphotosapi.upload_and_map_images_to_album(album_response, image_list=images_to_upload, from_cloud=True)

    # update MediaItems in db with statuses LOADED_AND_MAPPED or LOADED and external_ids set
    mapped_media_items = []
    unmapped_media_items = []
    failed_media_items = images_to_upload
    if mapped_images_response:
        # update images mapped to an album
        if mapped_images_response.get('mapped_gpids_to_img_data', ''):
            mapped_media_items = update_mediaitems_with_gphotos_data(
                mapped_images_response['mapped_gpids_to_img_data'], media_items, failed_media_items)
        # update images that failed to map to album
        if mapped_images_response.get('unmapped_gpids_to_img_data', ''):
            unmapped_media_items = update_mediaitems_with_gphotos_data(
                mapped_images_response['unmapped_gpids_to_img_data'], media_items, failed_media_items, status=metadata.Status.LOADED)

    # update Album in db with status LOADED_AND_MAPPED
    album.status = metadata.Status.LOADED_AND_MAPPED.name
    album.save()

    log_and_store_message(request, messages.SUCCESS,
        f"Successfully created album [{album.external_id}] and mapped [{len(mapped_media_items)}] media items to it")
    if unmapped_media_items:
        log_and_store_message(request, messages.ERROR,
            f"Successfully loaded [{len(unmapped_media_items)}] media items, but failed to map these to newly created album [{album.external_id}]")
        log_and_store_message(request, messages.ERROR, f"Unmapped media items: [{unmapped_media_items}]")
    if failed_media_items:
        log_and_store_message(request, messages.ERROR,
            f"Failed to load [{len(failed_media_items)}] media items into google photos library.")
        log_and_store_message(request, messages.ERROR, f"Failed media items: [{failed_media_items}]")

    # TODO: delete photos from s3
    
    return redirect(f"/lockdownsf/manage/album_view/{album.external_id}/")


def mediaitem_search(request):
    template = 'mediaitem_search.html'

    # form backing data
    all_albums = Album.objects.all()

    # bind vars to form data and assemble query filters
    search_criteria = {}
    and_filters = {}
    or_filters = ''
    if request.GET.get('search-facets'):
        search_criteria['facets'] = request.GET.get('search-facets')
        and_filters['facets__contains'] = search_criteria['facets']
    if request.GET.get('search-text'):
        search_criteria['search_text'] = request.GET.get('search-text')
        or_filters = Q(extracted_text__contains = search_criteria['search_text']) | Q(external_id__contains = search_criteria['search_text']) | Q(file_name__contains = search_criteria['search_text'])

    # fetch media_items from db
    matching_mediaitems = MediaItem.objects.filter(**and_filters)
    if or_filters:
        matching_mediaitems = matching_mediaitems.filter(or_filters)

    # fetch media_items from gphotos api to populate thumb_urls 
    populate_thumb_urls_from_gphotosapi(matching_mediaitems)

    context = {
        'template': template,
        'all_albums': all_albums,
        'all_facets': metadata.all_facets,
        'search_criteria': search_criteria,
        'matching_mediaitems': matching_mediaitems,
    }

    return render(request, template, context)


def mediaitem_view(request, mediaitem_external_id):
    template = 'mediaitem_view.html'

    # form backing data
    all_albums = Album.objects.all()
    all_tags = Tag.objects.all()

    # fetch media_item from db
    try:
        mediaitem = MediaItem.objects.get(external_id=mediaitem_external_id)
    except Exception as ex:
        log_and_store_message(request, messages.SUCCESS,
            f"Failure to fetch media item, no match for external_id [{mediaitem_external_id}]")
        
        return redirect(f"/lockdownsf/manage/mediaitem_search/")

    # fetch media_item from gphotos api to populate thumb_url 
    gphotos_mediaitem = gphotosapi.get_photo_by_id(mediaitem_external_id)
    mediaitem.thumb_url = gphotos_mediaitem.get('baseUrl', '')

    # mediaitem_location = { 
    #     'lat': str(mediaitem.latitude), 
    #     'lng': str(mediaitem.longitude) 
    # }

    display_tags = []
    for tag in mediaitem.tags.all():
        display_tags.append(tag)

    context = {
        'template': template,
        'all_albums': all_albums,
        'all_tags': all_tags,
        'mediaitem_external_id': mediaitem_external_id,
        'mediaitem': mediaitem,
        # 'mediaitem_location_json': json.dumps(mediaitem_location, indent=4),
        'display_tags': display_tags,
    }

    return render(request, template, context)


def mediaitem_edit(request):

    # bind vars to form data 
    media_item_external_id = request.POST.get('media-item-external-id', '')
    new_tag_ids = request.POST.getlist('tag_ids', [])

    # TODO incorporate other editable fields

    # process form data
    new_tag_ids = [int(tag_id) for tag_id in new_tag_ids]

    # handle missing data
    if not media_item_external_id:
        log_and_store_message(request, messages.ERROR, f"Failure to update media item, external_id was not set")
        
        return redirect(f"/lockdownsf/manage/mediaitem_search/")

    # fetch media_item from db
    try:
        media_item = MediaItem.objects.get(external_id=media_item_external_id)
    except Exception as ex:
        log_and_store_message(request, messages.ERROR,
            f"Failure to update media item, no match for external_id [{media_item_external_id}]")
        
        return redirect(f"/lockdownsf/manage/mediaitem_search/")

    # update media item with form data
    old_tag_ids = [old_tag.id for old_tag in media_item.tags.all()]
    tag_ids_to_remove = list(set(old_tag_ids) - set(new_tag_ids))
    tag_ids_to_add = list(set(new_tag_ids) - set(old_tag_ids))

    # delete old tags that aren't in new list
    for tag_id_to_remove in tag_ids_to_remove:
        tag_to_remove = Tag.objects.get(pk=tag_id_to_remove)
        media_item.tags.remove(tag_to_remove)
        media_item.save()

    # add new tags that aren't in old list
    for tag_id_to_add in tag_ids_to_add:
        tag_to_add = Tag.objects.get(pk=tag_id_to_add)
        media_item.tags.add(tag_to_add)
        media_item.save()

    return redirect(f"/lockdownsf/manage/mediaitem_view/{media_item_external_id}/")


def tag_listing(request):
    template = 'tag_listing.html'

    # process messages
    success_messages, error_messages = extract_messages_from_storage(request)

    # form backing data
    all_albums = Album.objects.all()
    all_tag_statuses = [ts.name for ts in metadata.TagStatus]
        
    all_tags = Tag.objects.all()

    context = {
        'template': template,
        'success_messages': success_messages,
        'error_messages': error_messages,
        'all_albums': all_albums,
        'all_tag_statuses': all_tag_statuses,
        'all_tags': all_tags,
    }
    
    return render(request, template, context)


def tag_create(request):

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
        extracted_text_formatted = request.POST.get('photo-extracted-text', '')
        extracted_text_raw = extracted_text_formatted.replace('<br/>', ' ')
        try:
            photo = Photo.objects.get(uuid=uuid)
            # update properties
            photo.neighborhood_slug = neighborhood_slug
            photo.scene_type = scene_type
            photo.business_type = business_type
            photo.other_labels = other_labels
            photo.extracted_text_formatted = extracted_text_formatted
            photo.extracted_text_raw = extracted_text_raw
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
        extracted_text_raw, extracted_text_formatted = s3manager.extract_text(uuid, metadata.S3_BUCKET)

        # init and save photo
        photo = Photo(uuid=uuid, source_file_name=source_file_name, neighborhood=neighborhood, 
            dt_taken=dt_taken, file_format=file_format, latitude=latitude, longitude=longitude, 
            width_pixels=width, height_pixels=height, aspect_format=aspect_format,
            scene_type=scene_type, business_type=business_type, other_labels=other_labels,
            extracted_text_raw=extracted_text_raw, extracted_text_formatted=extracted_text_formatted)
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
