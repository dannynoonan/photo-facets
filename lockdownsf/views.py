import boto3
from inspect import getmembers
import json
import os
from pprint import pprint

from django.shortcuts import render
from django.template import loader
from django.http import HttpResponse
from django.http import Http404

from .models import Neighborhood


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
    print('###### pprint(getmembers(request)):')
    pprint(getmembers(request))
    
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

    # print('################### pprint(getmembers(presigned_post)):')
    # pprint(getmembers(presigned_post))

    data = json.dumps({
        'data': presigned_post,
        # 'url': 'https://%s.s3.amazonaws.com/%s' % (S3_BUCKET, file_name),
        'url': 'https://' + S3_BUCKET + '.s3.amazonaws.com/' +  file_name,
    })

    print('@@@@@@@@@@@@@@@@@@@@ data:')
    pprint(data)

    return HttpResponse(data, content_type='json')


def upload_photo(request):
    template = 'upload_photo.html'

    context = {
    }

    return render(request, template, context)


def submit_form(request):
    template = 'upload_photo_success.html'

    try:
        neighborhood_slug = request.POST["neighborhood-slug"]
        img_url = request.POST["img-url"]

        # TODO
        # import_photo(image_url, neighborhood_slug)

        context = {
            'neighborhood_slug': neighborhood_slug,
            'img_url': img_url,
        }

        return render(request, template, context)

    except Exception as e:
        print('pprint(getmembers(request)): ')
        a = getmembers(request)
        print('pprint(vars(request)): ')
        b = vars(request)
        context = {
            'a': a,
            'b': b,
            'e': e
        }
        return render(request, template, context)
