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


def extract_text(img_file_name, bucket):
    extracted_text_raw = ''
    extracted_text_formatted = ''

    # TODO automatically process personalized signs with textract? 
    # TODO compare output of both and keep whatever is distinctive?  Thep example

    # use AWS rekognition's detect_text for first pass at extracting text from image
    # https://docs.aws.amazon.com/rekognition/latest/dg/text-detecting-text-procedure.html
    # https://boto3.amazonaws.com/v1/documentation/api/latest/reference/services/rekognition.html#Rekognition.Client.detect_text
    rekognition_client = boto3.client('rekognition', region_name=AWS_REGION_NAME)
    response = rekognition_client.detect_text(
        Image = {'S3Object': {'Bucket': bucket, 'Name': img_file_name}})
    text_detections = response['TextDetections']
    word_count = len([t for t in text_detections if t['Type'] == 'WORD'])
    print(f"rekognition detect_text word count [{word_count}] for image_file_name [{img_file_name}]")

    # rekognition detect_text maxes out at 50 words. if fewer than 50 words, parse detect_text response  
    if word_count < 50:
        print(f"parsing rekognition detect_text response for image [{img_file_name}]")
        for text in text_detections:
            if text['Type'] == 'LINE':
                extracted_text_raw = f"{extracted_text_raw} {text['DetectedText']}"
                extracted_text_formatted = f"{extracted_text_formatted}<br/>{text['DetectedText']}"
 
    # otherwise use AWS textract's detect_document_text (more costly, only use if 50 word threshold met)
    else:
        # https://docs.aws.amazon.com/textract/latest/dg/detecting-document-text.html
        # https://docs.aws.amazon.com/textract/latest/dg/API_DetectDocumentText.html
        # https://boto3.amazonaws.com/v1/documentation/api/latest/reference/services/textract.html
        print(f"parsing textract detect_document_text response for image [{img_file_name}]")
        textract_client = boto3.client('textract', region_name=AWS_REGION_NAME)
        response = textract_client.detect_document_text(
            Document = {'S3Object': {'Bucket': bucket, 'Name': img_file_name}})
        blocks = response['Blocks']
        for block in blocks:
            if 'Text' in block and block['BlockType'] == 'LINE':
                extracted_text_raw = f"{extracted_text_raw} {block['Text']}"
                extracted_text_formatted = f"{extracted_text_formatted}<br/>{block['Text']}"

    print('extracted_text_raw')
    print(extracted_text_raw)
    print('extracted_text_formatted')
    print(extracted_text_formatted)

    return extracted_text_raw, extracted_text_formatted