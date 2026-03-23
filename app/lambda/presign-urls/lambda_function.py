import json
import os
import uuid

import boto3
from botocore.client import Config

REGION = os.environ.get("REGION")
BUCKET_NAME = os.environ.get("BUCKET_NAME")
UPLOAD_FOLDER = "uploads"

s3_client = boto3.client(
    "s3",
    region_name=REGION,
    config=Config(signature_version="s3v4", s3={"addressing_style": "path"}),
)


def lambda_handler(event, context):

    # Parse JSON body
    try:
        body = json.loads(event["body"])
    except (TypeError, json.JSONDecodeError):
        return {"statusCode": 400, "body": json.dumps({"error": "invalid JSON body"})}

    filenames = body.get("filenames")

    if not filenames or not isinstance(filenames, list):
        return {
            "statusCode": 400,
            "body": json.dumps({"error": "filenames must be provided as a list"}),
        }

    urls = {}

    try:
        for filename in filenames:
            key = f"{UPLOAD_FOLDER}/{uuid.uuid4()}.pdf"

            # Generate presigned URL
            url = s3_client.generate_presigned_url(
                "put_object",
                Params={
                    "Bucket": BUCKET_NAME,
                    "Key": key,
                    "ContentType": "application/pdf",
                },
                ExpiresIn=3600,  # 1 hour
            )

            urls[filename] = {"key": key, "upload_url": url}

    except Exception as e:
        return {
            "statusCode": 500,
            "body": json.dumps({"error": "error generating presigned URL"}),
        }

    return {"statusCode": 200, "body": json.dumps(urls)}
