import boto3
from datetime import datetime
from inspect import getmembers
import json
import os
from pprint import pprint
import uuid

from django.shortcuts import render
from django.template import loader
from django.http import HttpResponse
from django.http import Http404

from .models import Neighborhood, Photo
from .metadata import all_aspect_formats, all_scene_types, all_business_types, all_other_labels, image_file_formats


def index(request):
    template = 'index.html'
    neighborhoods = Neighborhood.objects.all()
    context = {
        'neighborhoods': neighborhoods
    }
    return render(request, template, context)


def neighborhood(request, neighborhood_slug):
    template = 'neighborhood.html'
    try:
        neighborhood = Neighborhood.objects.get(pk=neighborhood_slug)
        photos = neighborhood.photo_set.all() 
        context = {
            'neighborhood': neighborhood,
            'photos': photos,
        }
        return render(request, template, context)
    except Neighborhood.DoesNotExist:
        raise Http404("No neighborhood found for slug %s" % neighborhood_slug)


# def upload_photo_flask():
#     port = int(os.environ.get('PORT', 5000))
#     app.run(host='0.0.0.0', port = port)
#     return render(request, 'upload_photo.html', context)


def sign_s3(request):
    # S3_BUCKET = os.environ.get('S3_BUCKET')
    # S3_BUCKET = settings.S3_BUCKET_NAME
    S3_BUCKET = 'lockdownsf'

    # file_name = request.args.get('file_name')
    # file_type = request.args.get('file_type')

    # object_name = urllib.parse.quote_plus(request.GET['file_name'])
    file_name = request.GET['file_name']
    file_type = request.GET['file_type']

    s3 = boto3.client('s3')

    presigned_post = s3.generate_presigned_post(
        Bucket = S3_BUCKET,
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
        # 'url': 'https://%s.s3.amazonaws.com/%s' % (S3_BUCKET, file_name),
        'url': 'https://' + S3_BUCKET + '.s3.amazonaws.com/' +  file_name,
    })

    return HttpResponse(data, content_type='json')


def select_photo(request):
    template = 'select_photo.html'
    
    photo_uuid = uuid.uuid4()
    all_neighborhoods = Neighborhood.objects.all()
    
    context = {
        'photo_uuid': str(photo_uuid),
        'all_neighborhoods': all_neighborhoods,
        'all_aspect_formats': all_aspect_formats,
        'all_scene_types': all_scene_types,
        'all_business_types': all_business_types,
        'all_other_labels': all_other_labels,
    }

    return render(request, template, context)
        

def save_photo(request):
    template = 'save_photo.html'

    try:
        # bind vars to form data 
        neighborhood_slug = request.POST.get('photo-neighborhood-slug', '')
        source_file_name = request.POST.get('photo-file-name', '')
        uuid = request.POST.get('photo-uuid', '')
        file_path = request.POST.get('photo-file-path', '')
        date_taken = request.POST.get('photo-date-taken', '')
        file_format = request.POST.get('photo-file-format', '')
        latitude = request.POST.get('photo-latitude', '')
        longitude = request.POST.get('photo-longitude', '')
        width = request.POST.get('photo-width', '')
        height = request.POST.get('photo-height', '')
        aspect_format = request.POST.get('photo-aspect-format', '')
        scene_type = request.POST.get('photo-scene-type', '')
        business_type = request.POST.get('photo-business-type', '')
        other_labels = request.POST.get('photo-other-labels', '')

        # process raw vars for Photo obj 
        neighborhood = Neighborhood.objects.get(pk=neighborhood_slug)
        # 2020:06:05 15:07:50
        print('@@@@@@@ date_taken: ' + date_taken)
        dt_taken = datetime.strptime(date_taken, '%Y:%m:%d %H:%M:%S')
        print('@@@@@@@ dt_taken: ' + str(dt_taken))
        file_format = image_file_formats.get(file_format, 'xxx')

        photo = Photo(uuid=uuid, source_file_name=source_file_name, neighborhood=neighborhood, 
            dt_taken=dt_taken, file_format=file_format, latitude=latitude, longitude=longitude, 
            width_pixels=width, height_pixels=height, aspect_format=aspect_format,
            scene_type=scene_type, business_type=business_type, other_labels=other_labels)
        photo.save()

        context = {
            'photo': photo,
            'source_file_name': source_file_name,
            'file_path': file_path,
        }

        return render(request, template, context)

    except Exception as ex:
        dump = getmembers(request)
        context = {
            'dump': dump,
            'exception': ex
        }
        return render(request, template, context)
