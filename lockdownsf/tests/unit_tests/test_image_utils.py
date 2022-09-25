from lockdownsf.services.photo_utils import get_lat_lng, avg_gps_info

def test_get_lat_lng():
    # TODO incorporate global S & E 
    gps_exif_data = {
        'GPSLatitudeRef': 'N', 
        'GPSLatitude': (33.0, 59.0, 16.59), 
        'GPSLongitudeRef': 'W', 
        'GPSLongitude': (118.0, 25.0, 30.53)
    }
    assert(get_lat_lng(gps_exif_data) == 33.987870, -118.425180)

def test_avg_gps_info():
    pass
    