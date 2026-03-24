import json
import os
import uuid

import boto3
from botocore.client import Config
from PyPDF2 import PdfReader, PdfWriter

REGION = os.environ.get("REGION")
BUCKET_NAME = os.environ.get("BUCKET_NAME")
PROTECTED_FOLDER = "protected"

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

    key = body.get("key")
    password = body.get("password")

    if not key:
        return {"statusCode": 400, "body": json.dumps("key is required")}
    if not password or not isinstance(password, str):
        return {"statusCode": 400, "body": json.dumps("password is required")}

    temp_files = []

    try:
        tmp_path = f"/tmp/{uuid.uuid4()}_{os.path.basename(key)}"
        s3_client.download_file(BUCKET_NAME, key, tmp_path)
        temp_files.append(tmp_path)

        reader = PdfReader(tmp_path)

        if reader.is_encrypted:
            return {
                "statusCode": 400,
                "body": json.dumps("PDF is already encrypted — decrypt it first"),
            }

        writer = PdfWriter()
        for page in reader.pages:
            writer.add_page(page)

        if reader.metadata:
            writer.add_metadata(reader.metadata)

        writer.encrypt(
            user_password=password,
            owner_password=password,
            use_128bit=True,
        )

        output_key = f"{PROTECTED_FOLDER}/{uuid.uuid4()}.pdf"
        output_tmp_path = f"/tmp/{os.path.basename(output_key)}"
        temp_files.append(output_tmp_path)

        with open(output_tmp_path, "wb") as f:
            writer.write(f)

        s3_client.upload_file(
            output_tmp_path,
            BUCKET_NAME,
            output_key,
            ExtraArgs={"ContentType": "application/pdf"},
        )

        url = s3_client.generate_presigned_url(
            "get_object",
            Params={"Bucket": BUCKET_NAME, "Key": output_key},
            ExpiresIn=3600,
        )

        return {
            "statusCode": 200,
            "body": json.dumps({"filename": output_key, "url": url}),
        }

    except Exception as e:
        return {
            "statusCode": 500,
            "body": json.dumps(f"error encrypting PDF: {str(e)}"),
        }

    finally:
        for f in temp_files:
            if os.path.exists(f):
                os.remove(f)
