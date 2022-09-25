from lockdownsf.models import Album
from lockdownsf.services import photo_utils


def update_album_gps_info(album: Album) -> None:
    """
    update Album with center lat/lng, zoom level, and tally of photos having gps data
    """
    ctr_lat, ctr_lng, zoom_level, photos_having_gps = photo_utils.avg_gps_info(album.photo_set.all())
    album.center_latitude = ctr_lat
    album.center_longitude = ctr_lng
    album.map_zoom_level = zoom_level
    album.photos_having_gps = photos_having_gps
