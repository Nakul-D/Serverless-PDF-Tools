import json
import os
import uuid

import boto3
from botocore.client import Config
from PyPDF2 import PdfMerger

# Read from Lambda environment variables
REGION = os.environ.get("REGION")
BUCKET_NAME = os.environ.get("BUCKET_NAME")
MERGED_FOLDER = "merged"

s3_client = boto3.client(
    "s3",
    region_name=REGION,
    config=Config(signature_version="s3v4", s3={"addressing_style": "path"}),
)


def lambda_handler(event, context):

    if not BUCKET_NAME or not REGION:
        raise Exception("missing required environment variables")

    try:
        body = json.loads(event["body"])
    except (TypeError, json.JSONDecodeError):
        return {"statusCode": 400, "body": json.dumps("invalid JSON body")}

    keys = body.get("keys")  # list of uploaded PDF keys

    if not keys or not isinstance(keys, list):
        return {
            "statusCode": 400,
            "body": json.dumps("keys must be provided as a list"),
        }

    merger = PdfMerger()
    temp_files = []

    try:
        # Download PDFs from S3
        for key in keys:
            tmp_path = f"/tmp/{uuid.uuid4()}_{os.path.basename(key)}"
            s3_client.download_file(BUCKET_NAME, key, tmp_path)
            temp_files.append(tmp_path)
            merger.append(tmp_path)

        # Save merged PDF
        merged_filename = f"{MERGED_FOLDER}/{uuid.uuid4()}.pdf"
        merged_path = f"/tmp/{os.path.basename(merged_filename)}"
        merger.write(merged_path)
        merger.close()
        temp_files.append(merged_path)

        # Upload merged PDF back to S3
        s3_client.upload_file(
            merged_path,
            BUCKET_NAME,
            merged_filename,
            ExtraArgs={"ContentType": "application/pdf"},
        )

        # Generate presigned URL
        url = s3_client.generate_presigned_url(
            "get_object",
            Params={"Bucket": BUCKET_NAME, "Key": merged_filename},
            ExpiresIn=3600,  # 1 hour
        )

        # Clean up temp files
        for f in temp_files:
            if os.path.exists(f):
                os.remove(f)

        return {
            "statusCode": 200,
            "body": json.dumps(
                {"merged_filename": merged_filename, "merged_pdf_url": url}
            ),
        }

    except Exception as e:
        return {"statusCode": 500, "body": json.dumps(f"error merging PDFs: {str(e)}")}
