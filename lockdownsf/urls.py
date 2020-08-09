from django.urls import path

from . import views

urlpatterns = [
    path(r'', views.index, name='index'),
    path(r'neighborhood/<str:neighborhood_slug>/', views.neighborhood, name='neighborhood'),
    path(r'sign_s3/', views.sign_s3, name='sign_s3'),
    path(r'manage/', views.manage, name='manage'),
    path(r'file_uploader/', views.file_uploader, name='file_uploader'),
    path(r'manage/album_listing/', views.album_listing, name='album_listing'),
    path(r'manage/album_import/', views.album_import, name='album_import'),
    path(r'manage/album_create/', views.album_create, name='album_create'),
    path(r'manage/album_view/<str:album_external_id>/', views.album_view, name='album_view'),
    path(r'manage/album_delete/', views.album_delete, name='album_delete'),
    path(r'manage/album_media_items_delete/', views.album_media_items_delete, name='album_media_items_delete'),
    path(r'manage/mediaitem_search/', views.mediaitem_search, name='mediaitem_search'),
    path(r'manage/mediaitem_view/<str:mediaitem_external_id>/', views.mediaitem_view, name='mediaitem_view'),

    path('admin/neighborhood_listing/', views.neighborhood_listing, name='neighborhood_listing'),
    path('admin/add_neighborhood/', views.add_neighborhood, name='add_neighborhood'),
    path('admin/save_neighborhood/', views.save_neighborhood, name='save_neighborhood'),
    path('admin/edit_neighborhood/<str:neighborhood_slug>/', views.edit_neighborhood, name='edit_neighborhood'),
    path('admin/select_photo/', views.select_photo, name='select_photo'),
    path('admin/save_photo/', views.save_photo, name='save_photo'),
    path('admin/edit_photo/', views.edit_photo, name='edit_photo'),
    path('admin/search_photos/', views.search_photos, name='search_photos'),
    path('admin/edit_photo/<str:photo_uuid>/', views.edit_photo, name='edit_photo'),
]