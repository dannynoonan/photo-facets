from django.shortcuts import render
from django.template import loader
from django.http import HttpResponse
from django.http import Http404

from .models import Neighborhood


def index(request):
    neighborhoods = Neighborhood.objects.all()
    context = {'neighborhoods': neighborhoods}
    return render(request, 'index.html', context)

def neighborhood(request, neighborhood_slug):
    try:
        neighborhood = Neighborhood.objects.get(pk=neighborhood_slug)
        photos = neighborhood.photo_set.all() 
        context = {
            'neighborhood': neighborhood,
            'photos': photos,
        }
        return render(request, 'neighborhood.html', context)
    except Neighborhood.DoesNotExist:
        raise Http404("No neighborhood found for slug %s" % neighborhood_slug)
    
