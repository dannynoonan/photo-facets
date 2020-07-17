from .metadata import img_max_dimensions


def calculate_resized_images(aspect_ratio, width, height):
    img_dimensions = {}
    # landscape, square, or pano
    if aspect_ratio >= 1:
        # thumb
        img_dimensions['thumb_width'] = img_max_dimensions['thumb_width']
        img_dimensions['thumb_height'] = round(img_dimensions['thumb_width'] / aspect_ratio)
        # medium
        if img_max_dimensions['medium_width'] > width:
            img_dimensions['medium_width'] = width
            img_dimensions['medium_height'] = height
        else:
            img_dimensions['medium_width'] = img_max_dimensions['medium_width']
            img_dimensions['medium_height'] = round(img_dimensions['medium_width'] / aspect_ratio)
        # large
        if img_max_dimensions['large_width'] > width:
            img_dimensions['large_width'] = width
            img_dimensions['large_height'] = height
        else:
            img_dimensions['large_width'] = img_max_dimensions['large_width']
            img_dimensions['large_height'] = round(img_dimensions['large_width'] / aspect_ratio)
    # portrait or vertical pano
    else:
        # thumb
        img_dimensions['thumb_height'] = img_max_dimensions['thumb_height']
        img_dimensions['thumb_width'] = round(img_dimensions['thumb_height'] * aspect_ratio)
        # medium
        if img_max_dimensions['medium_height'] > height:
            img_dimensions['medium_height'] = height
            img_dimensions['medium_width'] = width
        else:
            img_dimensions['medium_height'] = img_max_dimensions['medium_height']
            img_dimensions['medium_width'] = round(img_dimensions['medium_height'] * aspect_ratio)
        # large
        if img_max_dimensions['large_height'] > height:
            img_dimensions['large_height'] = height
            img_dimensions['large_width'] = width
        else:
            img_dimensions['large_height'] = img_max_dimensions['large_height']
            img_dimensions['large_width'] = round(img_dimensions['large_height'] * aspect_ratio)
    return img_dimensions