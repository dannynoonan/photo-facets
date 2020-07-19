import boto3

from .metadata import img_max_dimensions, AWS_REGION_NAME


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


def detect_text(photo, bucket):

    # https://docs.aws.amazon.com/rekognition/latest/dg/text-detecting-text-procedure.html
    # https://boto3.amazonaws.com/v1/documentation/api/latest/reference/services/rekognition.html#Rekognition.Client.detect_text

    # TODO could this extract more than 50 words?
    # https://boto3.amazonaws.com/v1/documentation/api/latest/reference/services/textract.html

    client = boto3.client('rekognition', region_name=AWS_REGION_NAME)
    response = client.detect_text(Image={'S3Object':{'Bucket':bucket,'Name':photo}})
                        
    text_detections = response['TextDetections']
    extracted_text_raw = ''
    extracted_text_formatted = ''
    for text in text_detections:
        if text['Type'] == 'LINE':
            extracted_text_raw = f"{extracted_text_raw} {text['DetectedText']}"
            extracted_text_formatted = f"{extracted_text_formatted}<br/>{text['DetectedText']}"
    
    print ('extracted_text_raw')
    print (extracted_text_raw)
    print ('text_format')
    print (extracted_text_formatted)

    return extracted_text_raw, extracted_text_formatted