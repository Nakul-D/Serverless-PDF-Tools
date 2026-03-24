import json
import os
import uuid

import boto3
from botocore.client import Config
from PyPDF2 import PdfReader, PdfWriter

REGION = os.environ.get("REGION")
BUCKET_NAME = os.environ.get("BUCKET_NAME")
SPLIT_FOLDER = "split"

s3_client = boto3.client(
    "s3",
    region_name=REGION,
    config=Config(signature_version="s3v4", s3={"addressing_style": "path"}),
)


def write_and_upload(writer, folder, temp_files):
    filename = f"{folder}/{uuid.uuid4()}.pdf"
    tmp_path = f"/tmp/{os.path.basename(filename)}"
    temp_files.append(tmp_path)
    with open(tmp_path, "wb") as f:
        writer.write(f)
    s3_client.upload_file(
        tmp_path, BUCKET_NAME, filename, ExtraArgs={"ContentType": "application/pdf"}
    )
    url = s3_client.generate_presigned_url(
        "get_object",
        Params={"Bucket": BUCKET_NAME, "Key": filename},
        ExpiresIn=3600,
    )
    return {"filename": filename, "url": url}


def lambda_handler(event, context):
    if not BUCKET_NAME or not REGION:
        raise Exception("missing required environment variables")

    try:
        body = json.loads(event["body"])
    except (TypeError, json.JSONDecodeError):
        return {"statusCode": 400, "body": json.dumps("invalid JSON body")}

    key = body.get("key")
    split_after = body.get("split_after_page_number")

    if not key or not isinstance(key, str):
        return {
            "statusCode": 400,
            "body": json.dumps("key must be provided as a string"),
        }

    if not split_after or not isinstance(split_after, int) or split_after < 1:
        return {
            "statusCode": 400,
            "body": json.dumps("split_after_page_number must be an integer >= 1"),
        }

    tmp_input = f"/tmp/{uuid.uuid4()}_{os.path.basename(key)}"
    temp_files = [tmp_input]

    try:
        s3_client.download_file(BUCKET_NAME, key, tmp_input)
        reader = PdfReader(tmp_input)
        total_pages = len(reader.pages)

        if split_after >= total_pages:
            return {
                "statusCode": 400,
                "body": json.dumps(
                    f"split_after_page_number must be less than total pages ({total_pages})"
                ),
            }

        # Part 1: pages 1 to split_after
        writer1 = PdfWriter()
        for i in range(split_after):
            writer1.add_page(reader.pages[i])

        # Part 2: pages split_after+1 to end
        writer2 = PdfWriter()
        for i in range(split_after, total_pages):
            writer2.add_page(reader.pages[i])

        part1 = write_and_upload(writer1, SPLIT_FOLDER, temp_files)
        part2 = write_and_upload(writer2, SPLIT_FOLDER, temp_files)

        # Cleanup
        for f in temp_files:
            if os.path.exists(f):
                os.remove(f)

        return {
            "statusCode": 200,
            "body": json.dumps(
                {
                    "total_pages": total_pages,
                    "split_after_page_number": split_after,
                    "part1": part1,
                    "part2": part2,
                }
            ),
        }

    except Exception as e:
        for f in temp_files:
            if os.path.exists(f):
                os.remove(f)
        return {"statusCode": 500, "body": json.dumps(f"error splitting PDF: {str(e)}")}
