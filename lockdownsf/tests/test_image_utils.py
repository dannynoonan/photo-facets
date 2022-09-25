from lockdownsf.services.image_utils import get_lat_lng

def test_get_lat_lng():
    exif_data = {
        'GPSLatitude': (33.0, 59.0, 16.59), 
        'GPSLongitude': (118.0, 25.0, 30.53), 
    }
    assert(get_lat_lng(exif_data) == 33.987870, -118.425180)
    