import exifread
from PIL import ExifTags, Image

from lockdownsf.metadata import img_max_dimensions

import ipdb


def calculate_resized_images(aspect_ratio, width, height):
    img_dimensions = {}
    # landscape, square, or pano
    if aspect_ratio >= 1:
        # small
        small_width = img_max_dimensions['small_width']
        small_height = round(img_max_dimensions['small_width'] / aspect_ratio)
        img_dimensions['small'] = (small_width, small_height)
        # medium
        if img_max_dimensions['medium_width'] > width:
            img_dimensions['medium'] = (width, height)
        else:
            medium_width = img_max_dimensions['medium_width']
            medium_height = round(img_max_dimensions['medium_width'] / aspect_ratio)
            img_dimensions['medium'] = (medium_width, medium_height)
        # large
        if img_max_dimensions['large_width'] > width:
            img_dimensions['large'] = (width, height)
        else:
            large_width = img_max_dimensions['large_width']
            large_height = round(img_max_dimensions['large_width'] / aspect_ratio)
            img_dimensions['large'] = (large_width, large_height)
    # portrait or vertical pano
    else:
        # small
        small_height = img_max_dimensions['small_height']
        small_width = round(img_max_dimensions['small_height'] * aspect_ratio)
        img_dimensions['small'] = (small_width, small_height)
        # medium
        if img_max_dimensions['medium_height'] > height:
            img_dimensions['medium'] = (width, height)
        else:
            medium_height = img_max_dimensions['medium_height']
            medium_width = round(img_max_dimensions['medium_height'] * aspect_ratio)
            img_dimensions['medium'] = (medium_width, medium_height)
        # large
        if img_max_dimensions['large_height'] > height:
            img_dimensions['large'] = (width, height)
        else:
            large_height = img_max_dimensions['large_height']
            large_width = round(img_max_dimensions['large_height'] * aspect_ratio)
            img_dimensions['large'] = (large_width, large_height)
            
    return img_dimensions
    

def get_exif_data(img):
    """Returns a dictionary from the exif data of an PIL Image item. Also
    converts the GPS Tags"""
    exif_data = {}
    info = img._getexif()
    if info:
        for tag, value in info.items():
            decoded = ExifTags.TAGS.get(tag, tag)
            if decoded == "GPSInfo":
                gps_data = {}
                for t in value:
                    sub_decoded = ExifTags.GPSTAGS.get(t, t)
                    gps_data[sub_decoded] = value[t]

                exif_data[decoded] = gps_data
            else:
                exif_data[decoded] = value
    return exif_data


def get_lat_lng(exif_gps_data):
    lat = None
    lng = None
    # latitude
    gps_latitude = exif_gps_data.get('GPSLatitude', '')
    gps_latitude_ref = exif_gps_data.get('GPSLatitudeRef', '')
    if gps_latitude and gps_latitude_ref:
        lat = convert_to_degress(gps_latitude)
        if gps_latitude_ref != 'N':
            lat = 0 - lat
        lat = str(f"{lat:.{5}f}")
    # longitude
    gps_longitude = exif_gps_data.get('GPSLongitude', '')
    gps_longitude_ref = exif_gps_data.get('GPSLongitudeRef', '')
    if gps_longitude and gps_longitude_ref:
        lng = convert_to_degress(gps_longitude)
        if gps_longitude_ref != 'E':
            lng = 0 - lng
        lng = str(f"{lng:.{5}f}")
    return lat, lng


def convert_to_degress(value):
    """Helper function to convert the GPS coordinates
    stored in the EXIF to degress in float format"""
    d0 = value[0][0]
    d1 = value[0][1]
    d = float(d0) / float(d1)
    m0 = value[1][0]
    m1 = value[1][1]
    m = float(m0) / float(m1)

    s0 = value[2][0]
    s1 = value[2][1]
    s = float(s0) / float(s1)

    return d + (m / 60.0) + (s / 3600.0)










# def get_exif_data_old(image_file):
#     with open(image_file, 'rb') as f:
#         exif_tags = exifread.process_file(f)
#     return exif_tags


# # https://gist.github.com/snakeye/fdc372dbf11370fe29eb
# def _get_if_exist(data, key):
#     if key in data:
#         return data[key]

#     return None


# def _convert_to_degress(value):
#     """
#     Helper function to convert the GPS coordinates stored in the EXIF to degress in float format
#     :param value:
#     :type value: exifread.utils.Ratio
#     :rtype: float
#     """
#     d = float(value.values[0].num) / float(value.values[0].den)
#     m = float(value.values[1].num) / float(value.values[1].den)
#     s = float(value.values[2].num) / float(value.values[2].den)

#     return d + (m / 60.0) + (s / 3600.0)


# def get_exif_data(image_data):
#     # print(f"^^^^^^ in get_exif_data file size / in_mem_image.tell(): {str(in_mem_image.tell())}")
#     ipdb.set_trace()
#     exif_tags = exifread.process_file(image_data)
#     return exif_tags


# def get_exif_location(exif_data):
#     """
#     Returns the latitude and longitude, if available, from the provided exif_data (obtained through get_exif_data above)
#     """
#     lat = None
#     lon = None

#     ipdb.set_trace()

#     gps_latitude = _get_if_exist(exif_data, 'GPS GPSLatitude')
#     gps_latitude_ref = _get_if_exist(exif_data, 'GPS GPSLatitudeRef')
#     gps_longitude = _get_if_exist(exif_data, 'GPS GPSLongitude')
#     gps_longitude_ref = _get_if_exist(exif_data, 'GPS GPSLongitudeRef')

#     if gps_latitude and gps_latitude_ref and gps_longitude and gps_longitude_ref:
#         lat = _convert_to_degress(gps_latitude)
#         if gps_latitude_ref.values[0] != 'N':
#             lat = 0 - lat

#         lon = _convert_to_degress(gps_longitude)
#         if gps_longitude_ref.values[0] != 'E':
#             lon = 0 - lon

#     return lat, lon