import json
import os
import uuid

import boto3
from botocore.client import Config
from PyPDF2 import PdfReader, PdfWriter

REGION = os.environ.get("REGION")
BUCKET_NAME = os.environ.get("BUCKET_NAME")
COMPRESSED_FOLDER = "compressed"

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

    key = body.get("key")  # single PDF key
    if not key or not isinstance(key, str):
        return {
            "statusCode": 400,
            "body": json.dumps("key must be provided as a string"),
        }

    tmp_input = f"/tmp/{uuid.uuid4()}_{os.path.basename(key)}"
    compressed_filename = f"{COMPRESSED_FOLDER}/{uuid.uuid4()}.pdf"
    tmp_output = f"/tmp/{os.path.basename(compressed_filename)}"
    temp_files = [tmp_input, tmp_output]

    try:
        # Download PDF from S3
        s3_client.download_file(BUCKET_NAME, key, tmp_input)

        # Compress
        reader = PdfReader(tmp_input)
        writer = PdfWriter()

        for page in reader.pages:
            page.compress_content_streams()  # CPU-intensive but reduces size
            writer.add_page(page)

        # Carry over metadata
        if reader.metadata:
            writer.add_metadata(reader.metadata)

        with open(tmp_output, "wb") as f:
            writer.write(f)

        # Upload compressed PDF to S3
        s3_client.upload_file(
            tmp_output,
            BUCKET_NAME,
            compressed_filename,
            ExtraArgs={"ContentType": "application/pdf"},
        )

        # Generate presigned URL
        url = s3_client.generate_presigned_url(
            "get_object",
            Params={"Bucket": BUCKET_NAME, "Key": compressed_filename},
            ExpiresIn=3600,
        )

        # Report size reduction
        original_size = (
            os.path.getsize(tmp_input) if os.path.exists(tmp_input) else None
        )
        compressed_size = (
            os.path.getsize(tmp_output) if os.path.exists(tmp_output) else None
        )

        # Cleanup
        for f in temp_files:
            if os.path.exists(f):
                os.remove(f)

        return {
            "statusCode": 200,
            "body": json.dumps(
                {
                    "compressed_filename": compressed_filename,
                    "compressed_pdf_url": url,
                    "original_size_bytes": original_size,
                    "compressed_size_bytes": compressed_size,
                }
            ),
        }

    except Exception as e:
        for f in temp_files:
            if os.path.exists(f):
                os.remove(f)
        return {
            "statusCode": 500,
            "body": json.dumps(f"error compressing PDF: {str(e)}"),
        }
