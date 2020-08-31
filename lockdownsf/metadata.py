from enum import Enum


class Status(Enum):
    NEWBORN = 'NEWBORN'
    LOADED = 'LOADED'
    LOADED_AND_MAPPED = 'LOADED_AND_MAPPED'


class TagStatus(Enum):
    ACTIVE = 'ACTIVE'
    DISABLED = 'DISABLED'


# https://gis.stackexchange.com/questions/225794/converting-miles-above-ground-to-zoom-level
# simple degree distances to google maps zoom levels
# doesn't factor in difference in longitude distance at equator vs poles, or any trig whatsoever
distances_to_zooms = [
    (0.0005, 19),
    (0.001, 18),
    (0.003, 17),
    (0.005, 16),
    (0.011, 15),
    (0.022, 14),
    (0.044, 13),
    (0.088, 12),
    (0.176, 11),
    (0.352, 10),
    (0.703, 9),
    (1.406, 8),
    (2.813, 7),
    (5.625, 6),
    (11.25, 5),
    (22.5, 4),
    (45, 3),
    (90, 2),
    (180, 1),
]


# img_max_dimensions = {
#     'small_width': 120,
#     'small_height': 120,
#     'medium_width': 600,
#     'medium_height': 500,
#     'large_width': 1200,
#     'large_height': 1000,
# }


# all_facets = [
#     # scene types
#     'boarded',
#     'boarded_tagged',
#     'boarded_mural',
#     'sign_generic',
#     'sign_distinctive',
#     'sign_personal',
#     'park',
#     'slow_streets',
#     'empty_street',
#     'none',
#     # business types
#     'dining',
#     'bar',
#     'food_market',
#     'non_food_shop',
#     'laundry',
#     'salon',
#     'exercise',
#     'medical',
#     'financial',
#     'performance_venue',
#     'municipal',
#     'religious', 
#     # other
#     'open',
#     'clever',
#     'neighborly',
#     'black_lives_matter',
# ]


# image_file_types = ['jpg', 'jpeg', 'png', 'gif', 'bmp', 'heic', 'ico', 'tiff', 'webp']
