import boto3
from datetime import datetime, timedelta
from io import BytesIO
from PIL import Image

from lockdownsf import metadata


def extract_text(img_file_name, bucket):
    extracted_text_raw = ''
    extracted_text_formatted = ''

    # TODO automatically process personalized signs with textract? 
    # TODO compare output of both and keep whatever is distinctive?  Thep example

    # use AWS rekognition's detect_text for first pass at extracting text from image
    # https://docs.aws.amazon.com/rekognition/latest/dg/text-detecting-text-procedure.html
    # https://boto3.amazonaws.com/v1/documentation/api/latest/reference/services/rekognition.html#Rekognition.Client.detect_text
    rekognition_client = boto3.client('rekognition', region_name=metadata.AWS_REGION_NAME)
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
                if extracted_text_raw:
                    extracted_text_raw = f"{extracted_text_raw} {text['DetectedText']}"
                    extracted_text_formatted = f"{extracted_text_formatted}<br/>{text['DetectedText']}"
                else:
                    extracted_text_raw = text['DetectedText']
                    extracted_text_formatted = text['DetectedText']

    # otherwise use AWS textract's detect_document_text (more costly, only use if 50 word threshold met)
    else:
        # https://docs.aws.amazon.com/textract/latest/dg/detecting-document-text.html
        # https://docs.aws.amazon.com/textract/latest/dg/API_DetectDocumentText.html
        # https://boto3.amazonaws.com/v1/documentation/api/latest/reference/services/textract.html
        print(f"parsing textract detect_document_text response for image [{img_file_name}]")
        textract_client = boto3.client('textract', region_name=metadata.AWS_REGION_NAME)
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


def resize_and_upload(orig_img, thumb_type, img_dimensions, uuid):
    print('****** in resize_and_upload')

    print(f"@@@@@@ [{thumb_type} before resizing] orig_img.format: {str(orig_img.format)}")
    print(f"@@@@@@ [{thumb_type} before resizing] orig_img.size: {str(orig_img.size)}")

    # im = Image.open(orig_img)
    orig_img.thumbnail(img_dimensions, Image.ANTIALIAS)
    
    print(f"****** [{thumb_type} after resizing] orig_img.format: {str(orig_img.format)}")
    print(f"****** [{thumb_type} after resizing] orig_img.size: {str(orig_img.size)}")
    
    in_mem_file = BytesIO()
    orig_img.save(in_mem_file, format=orig_img.format)

    print(f"^^^^^^ [{thumb_type}] orig_img saved to in_mem_file")
    print(f"^^^^^^ [{thumb_type}] file size / in_mem_file.tell(): {str(in_mem_file.tell())}")

    in_mem_file.seek(0)

    resized_img_file_name = f"{thumb_type}/{uuid}"

    # Upload image to s3
    client_s3 = boto3.client('s3') 

    response = client_s3.put_object( 
        ACL="public-read",
        Bucket=metadata.S3_BUCKET,
        Body=in_mem_file,
        ContentType='image/jpeg',
        Key=resized_img_file_name,
        Expires = datetime.now() + timedelta(minutes = 6),
    )

    resized_img_file_path = f"https://{metadata.S3_BUCKET}.s3.amazonaws.com/{resized_img_file_name}"

    print(f"====== [{thumb_type}] resized_img_file_path: {resized_img_file_path}")
    print(f"====== [{thumb_type}] str(response): {str(response)}")

    return resized_img_file_path