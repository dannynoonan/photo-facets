from django.urls import path

from . import views

urlpatterns = [
    path('', views.index, name='index'),
    path('neighborhood/<str:neighborhood_slug>/', views.neighborhood, name='neighborhood'),
    path('sign_s3/', views.sign_s3, name='sign_s3'),
    path('select_photo/', views.select_photo, name='select_photo'),
    path('save_photo/', views.save_photo, name='save_photo'),
]