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

from django.http import HttpResponse
from django.http import Http404
from django.db.models import Q
from django.shortcuts import render
from django.template import loader

from lockdownsf import metadata
from lockdownsf.models import Album, MediaItem, Neighborhood, Photo
from lockdownsf.services import controller_utils, gphotosapi, image_utils, s3manager

import ipdb


def index(request):
    template = 'index.html'

    all_neighborhoods = Neighborhood.objects.all()
    all_photos = Photo.objects.all()

    photo_collection_json = []
    for neighborhood in all_neighborhoods:
        neighborhood_photos_json = []
        for photo in neighborhood.photo_set.all():
            cats_json = []
            if metadata.scene_types_to_checkboxes[photo.scene_type]:
                print(f"photo.scene_type [{photo.scene_type}] -> scene_types_to_checkboxes[photo.scene_type] [{metadata.scene_types_to_checkboxes[photo.scene_type]}] for photo.uuid [{photo.uuid}]")
                cats_json.append(metadata.scene_types_to_checkboxes[photo.scene_type])
            if photo.business_type and photo.business_type != 'none': # TODO shouldn't need to be here
                cats_json.append(photo.business_type)
            if photo.other_labels:
                cats_json.extend(photo.other_labels.split('|'))
            photo_json = {
                'uuid': photo.uuid,
                'aspect_format': photo.aspect_format,
                'longitude': str(photo.longitude),
                'latitude': str(photo.latitude),
                'cats': cats_json
            }
            neighborhood_photos_json.append(photo_json)
        neighborhood_json = {
            'neighborhood': neighborhood.slug,
            'photos': neighborhood_photos_json,
        }
        photo_collection_json.append(neighborhood_json)

    context = {
        'template': template,
        'all_neighborhoods': all_neighborhoods,
        'all_photos': all_photos,
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


def admin(request):
    template = 'admin.html'

    all_neighborhoods = Neighborhood.objects.all()

    context = {
        'all_neighborhoods': all_neighborhoods,
        'all_scene_types': metadata.all_scene_types,
        'all_business_types': metadata.all_business_types,
        'all_other_labels': metadata.all_other_labels,
    }

    return render(request, template, context)


def album_listing(request):
    template = 'album_listing.html'

    albums = get_albums()

    context = {
        'albums': albums,
    }
    
    return render(request, template, context)


def album_import(request):
    template = 'album_import.html'

    context = {}
    
    return render(request, template, context)


def album_view(request, album_id):
    template = 'album_view.html'

    # TODO some way to identify where the photos uploaded to s3 temporarily are

    # TODO why is this page being called twice?

    if album_id and album_id != "_":
        """If we're loading a pre-existing album: fetch it from the db and the gphotos api"""
        album = Album.objects.get(external_id=album_id)
        mapped_media_items = album.mediaitem_set.all()

        context = {
            'album': album,
            'mapped_media_items': mapped_media_items,
        }
    else:
        """If we're uploading photos and creating a new album: 
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

        # insert Album into db with status PENDING and no external_id
        album = Album(name=album_title, external_resource=metadata.ExternalResource.GOOGLE_PHOTOS_V1.name, status=metadata.Status.NEWBORN.name)
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
            lat, lng = image_utils.get_lat_lng(exif_data['GPSInfo'])
            dt_taken = datetime.strptime(exif_data['DateTimeOriginal'], '%Y:%m:%d %H:%M:%S')

            # extract OCR text
            extracted_text_raw, extracted_text_formatted = s3manager.extract_text(image_file_name, metadata.S3_BUCKET)

            # init and save MediaItems to db, mapped to Album but with status PENDING and no external_id
            media_item = MediaItem(
                file_name=image_file_name, external_resource=metadata.ExternalResource.GOOGLE_PHOTOS_V1.name, 
                album=album, mime_type=pil_image.format, dt_taken=dt_taken, width=width, height=height, 
                latitude=lat, longitude=lng, extracted_text=extracted_text_raw, status=metadata.Status.NEWBORN.name)
            media_item.save()
            media_items.append(media_item)

        # create gphotos album
        album_response = gphotosapi.init_new_album_simple(album_title)

        if not album_response or not album_response['id']:
            print('@@@@@@ ERROR GRASSHOPPER DISASSEMBLE')

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
                mapped_media_items = controller_utils.update_mediaitems_with_gphotos_data(
                    mapped_images_response['mapped_gpids_to_img_data'], media_items, failed_media_items)
            # update images that failed to map to album
            if mapped_images_response.get('unmapped_gpids_to_img_data', ''):
                unmapped_media_items = controller_utils.update_mediaitems_with_gphotos_data(
                    mapped_images_response['unmapped_gpids_to_img_data'], media_items, failed_media_items, status=metadata.Status.LOADED)

        # update Album in db with status LOADED_AND_MAPPED
        album.status = metadata.Status.LOADED_AND_MAPPED.name
        album.save()

        # TODO: delete photos from s3
        
        # print(f"@@@@@ album: [{album}]")
        # print(f"@@@@@ mapped_media_items: [{mapped_media_items}]")
        # print(f"@@@@@ unmapped_media_items: [{unmapped_media_items}]")
        # print(f"@@@@@ failed_media_items: [{failed_media_items}]")

        context = {
            'album': album,
            'mapped_media_items': mapped_media_items,
            'unmapped_media_items': unmapped_media_items,
            'failed_media_items': failed_media_items,
        }
    
    return render(request, template, context)


# def update_mediaitems_with_gphotos_data(gpids_to_img_data, media_items, failed_media_items):
#     matched_media_items = []
#     for mapped_gpid, img_data in gpids_to_img_data.items():
#         for media_item in media_items:
#             if media_item.file_name == img_data.get('filename', ''):
#                 # update db
#                 media_item.external_id = mapped_gpid
#                 media_item.thumb_url = img_data.get('thumb_url', '')
#                 media_item.status = metadata.Status.LOADED_AND_MAPPED.name
#                 media_item.save()
#                 # add to matched_media_items
#                 matched_media_items.append(media_item)
#                 # remove from failed_media_items
#                 for f_item in failed_media_items:
#                     f_item_fn = f_item.split('/')[-1:][0]
#                     if f_item_fn == media_item.file_name:
#                         failed_media_items.remove(f_item)
#                         continue
#                 continue

#     return matched_media_items


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
