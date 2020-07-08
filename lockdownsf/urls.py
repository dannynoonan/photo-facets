from django.urls import path

from . import views

urlpatterns = [
    path('', views.index, name='index'),
    path('<str:neighborhood_slug>/', views.neighborhood, name='neighborhood'),
]