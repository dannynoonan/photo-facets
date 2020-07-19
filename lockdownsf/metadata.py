AWS_REGION_NAME = 'us-west-1'
S3_BUCKET = 'lockdownsf'


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
    'food_market',
    'non_food_shop',
    'dining',
    'bar',
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

image_file_formats = {
    'image/jpeg': 'jpg'
}