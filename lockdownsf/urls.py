from django.urls import path

from . import views

urlpatterns = [
    path(r'', views.index, name='index'),
    path(r'album_map/<str:album_id>/', views.album_map, name='album_map'),
    path(r'sign_s3/', views.sign_s3, name='sign_s3'),
    path(r'manage/', views.manage, name='manage'),
    path(r'manage/album_listing/', views.album_listing, name='album_listing'),
    path(r'manage/album_view/<str:album_id>/', views.album_view, name='album_view'),
    path(r'manage/album_view/<str:album_id>/<str:page_number>/', views.album_view, name='album_view_for_page'),
    path(r'manage/album_edit/', views.album_edit, name='album_edit'),
    path(r'manage/album_select_new_photos/', views.album_select_new_photos, name='album_select_new_photos'),
    path(r'manage/album_import_new_photos/', views.album_import_new_photos, name='album_import_new_photos'),
    path(r'manage/album_delete/', views.album_delete, name='album_delete'),
    path(r'manage/album_photos_delete/', views.album_photos_delete, name='album_photos_delete'),
    path(r'manage/photo_search/', views.photo_search, name='photo_search'),
    path(r'manage/photo_view/<str:photo_id>/', views.photo_view, name='photo_view'),
    path(r'manage/photo_edit/', views.photo_edit, name='photo_edit'),
    path(r'manage/tag_listing/', views.tag_listing, name='tag_listing'),
    path(r'manage/tag_create/', views.tag_create, name='tag_create'),
    path(r'manage/tag_edit/', views.tag_edit, name='tag_edit'),
    path(r'manage/extract_ocr_text/', views.extract_ocr_text, name='extract_ocr_text'),
]