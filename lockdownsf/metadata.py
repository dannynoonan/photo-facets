from enum import Enum


AWS_REGION_NAME = 'us-west-1'
S3_BUCKET = 'lockdownsf'


class Status(Enum):
    NEWBORN = 'NEWBORN'
    LOADED = 'LOADED'
    LOADED_AND_MAPPED = 'LOADED_AND_MAPPED'


class ExternalResource(Enum):
    GOOGLE_PHOTOS_V1 = 'GOOGLE_PHOTOS_V1'


img_max_dimensions = {
    'small_width': 120,
    'small_height': 120,
    'medium_width': 600,
    'medium_height': 500,
    'large_width': 1200,
    'large_height': 1000,
}

all_aspect_formats = [
    'landscape',
    'portrait',
    'square',
    'pano',
    'pano_vertical',
]

all_scene_types = [
    'boarded',
    'boarded_tagged',
    'boarded_mural',
    'sign_generic',
    'sign_distinctive',
    'sign_personal',
    'park',
    'slow_streets',
    'empty_street',
    'none',
]

all_business_types = [
    'dining',
    'bar',
    'food_market',
    'non_food_shop',
    'laundry',
    'salon',
    'exercise',
    'medical',
    'financial',
    'performance_venue',
    'municipal',
    'religious', 
]

all_other_labels = [
    'open',
    'clever',
    'neighborly',
    'black_lives_matter',
]


image_file_types = ['jpg', 'jpeg', 'png', 'gif', 'bmp', 'heic', 'ico', 'tiff', 'webp']


image_file_formats = {
    'image/jpeg': 'jpg'
}


scene_types_to_checkboxes = {
    'boarded': 'boarded',
    'boarded_tagged': 'boarded',
    'boarded_mural': 'mural',
    'sign_generic': '',
    'sign_distinctive': 'sign',
    'sign_personal': 'sign',
    'park': 'park',
    'slow_streets': '',
    'empty_street': '',
    'none': '',
}


# business_types_to_checkboxes = {
#     'food_market': 'food_market',
#     'non_food_shop': 'non_food_shop',
#     'dining': 'dining',
#     'bar': 'bar',
#     'laundry': 'laundry',
#     'salon': 'salon',
#     'exercise': 'exercise',
#     'medical': 'medical',
#     'financial': 'financial',
#     'performance_venue': 'performance_venue',
#     'municipal': 'municipal',
#     'religious': 'religious', 
# }