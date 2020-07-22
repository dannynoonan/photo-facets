from django.urls import path

from . import views

urlpatterns = [
    path('', views.index, name='index'),
    path('neighborhood/<str:neighborhood_slug>/', views.neighborhood, name='neighborhood'),
    path('sign_s3/', views.sign_s3, name='sign_s3'),
    path('admin/', views.admin, name='admin',),
    path('admin/neighborhood_listing/', views.neighborhood_listing, name='neighborhood_listing'),
    path('admin/add_neighborhood/', views.add_neighborhood, name='add_neighborhood'),
    path('admin/save_neighborhood/', views.save_neighborhood, name='save_neighborhood'),
    path('admin/edit_neighborhood/<str:neighborhood_slug>/', views.edit_neighborhood, name='edit_neighborhood'),
    path('admin/select_photo/', views.select_photo, name='select_photo'),
    path('admin/save_photo/', views.save_photo, name='save_photo'),
    path('admin/search_photos/', views.search_photos, name='search_photos'),
    path('admin/edit_photo/<str:photo_uuid>/', views.edit_photo, name='edit_photo'),
]