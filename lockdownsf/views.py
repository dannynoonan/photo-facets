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
from lockdownsf.models import Neighborhood, Photo
from lockdownsf.services import image_utils 
from lockdownsf.services import s3manager 
from lockdownsf.services import gphotosapi 

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

    if album_id and album_id != "_":
        # if we're loading a pre-existing album: fetch it from the db and the gphotos api
        album = gphotosapi.get_album(album_id)
        album_photos = gphotosapi.get_photos_for_album(album_id)
    else:
        # if we're uploading photos and creating a new album: 
        # - upload the photos to s3
        # - extract location and OCR text info from photos
        # - initialize a google photos album
        # - insert album and photo data into db
         
        # bind vars to form data 
        album_title = request.POST.get('album-title', '')
        images_to_upload = request.POST.getlist('images-to-upload', [])

        media_objects = []
        for image_path in images_to_upload:
            image_file_name = image_path.split('/')[-1:][0]   

            response = requests.get(image_path, stream=True)
            pil_image = Image.open(BytesIO(response.content))

            # extract location info
            exif_data = image_utils.get_exif_data(pil_image)
            print(f"^^^^^^ exif_data['GPSInfo']: {exif_data['GPSInfo']}")
            lat, lng = image_utils.get_lat_lng(exif_data['GPSInfo'])
            print(f"@@@@@@ lat: [{lat}] lng: [{lng}]")

            # extract OCR text
            extracted_text_raw, extracted_text_formatted = s3manager.extract_text(image_file_name, metadata.S3_BUCKET)
            print(f"text extracted for image [{image_file_name}]: [{extracted_text_raw}]")

        album = gphotosapi.init_new_album(album_title, image_list=images_to_upload, from_cloud=True)
        album_photos = gphotosapi.get_photos_for_album(album['id'])

    context = {
        'album': album,
        'album_photos': album_photos,
    }
    
    return render(request, template, context)


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
