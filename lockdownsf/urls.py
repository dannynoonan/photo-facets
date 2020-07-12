from django.urls import path

from . import views

urlpatterns = [
    path('', views.index, name='index'),
    path('neighborhood/<str:neighborhood_slug>/', views.neighborhood, name='neighborhood'),
    path('sign_s3/', views.sign_s3, name='sign_s3'),
    path('upload_photo/', views.upload_photo, name='upload_photo'),
    path('submit_form/', views.submit_form, name='submit_form'),
]