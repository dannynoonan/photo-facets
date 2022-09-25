import os

from lockdownsf.metadata import Status, TagStatus
from lockdownsf.models import Album, Photo, Tag, User
 
DEFAULT_OWNER = User.objects.get(email=os.environ['DEFAULT_OWNER_EMAIL'])

    
def create_album(album_name: str, album_s3_dir_uuid: str, user:str = DEFAULT_OWNER) -> Album:
    album = Album(name=album_name, owner=user, status=Status.NEWBORN.name)
    album.s3_dir = album_s3_dir_uuid 
    album.save()
    return album


def fetch_album_by_id(album_id: int) -> Album:
    return Album.objects.get(pk=album_id)


def fetch_all_albums(gps_required=False, user: str = DEFAULT_OWNER) -> list[Album]:
    if not gps_required:
        return Album.objects.filter(owner=user)
    else:
        return Album.objects.filter(owner=user, center_latitude__isnull=False, center_longitude__isnull=False)


def update_album_name(album_id: int, album_name: str) -> Album:
    album = Album.objects.get(pk=album_id)
    album.name = album_name
    album.save()
    return album


def fetch_photo_by_id(photo_id: int) -> Photo:
    return Photo.objects.get(pk=photo_id)


def create_tag(tag_name: str, user: str = DEFAULT_OWNER) -> Tag:
    new_tag = Tag(name=tag_name, status=TagStatus.ACTIVE.name, owner=user)
    new_tag.save()
    return new_tag


def fetch_tag_by_id(tag_id: int) -> Tag:
    return Tag.objects.get(pk=tag_id)


def fetch_all_tags(order_by=None, user: str = DEFAULT_OWNER) -> list[Tag]:
    if order_by:
        return Tag.objects.filter(owner=user).order_by(order_by)
    else:
        return Tag.objects.filter(owner=user)
