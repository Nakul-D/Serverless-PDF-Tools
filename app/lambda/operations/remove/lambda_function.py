import json
import os
import uuid

import boto3
from botocore.client import Config
from PyPDF2 import PdfReader, PdfWriter

REGION = os.environ.get("REGION")
BUCKET_NAME = os.environ.get("BUCKET_NAME")
REMOVED_FOLDER = "removed"

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
    from_page = body.get("from_page")
    to_page = body.get("to_page")

    if not key:
        return {"statusCode": 400, "body": json.dumps("key is required")}
    if from_page is None or to_page is None:
        return {
            "statusCode": 400,
            "body": json.dumps("from_page and to_page are required"),
        }
    if not isinstance(from_page, int) or not isinstance(to_page, int):
        return {
            "statusCode": 400,
            "body": json.dumps("from_page and to_page must be integers"),
        }
    if from_page < 1 or to_page < from_page:
        return {
            "statusCode": 400,
            "body": json.dumps(
                "invalid page range: from_page must be >= 1 and <= to_page"
            ),
        }

    tmp_input = f"/tmp/{uuid.uuid4()}_{os.path.basename(key)}"
    tmp_output = f"/tmp/{uuid.uuid4()}_removed.pdf"

    try:
        s3_client.download_file(BUCKET_NAME, key, tmp_input)

        reader = PdfReader(tmp_input)
        total_pages = len(reader.pages)

        to_page = min(to_page, total_pages)

        if from_page > total_pages:
            return {
                "statusCode": 400,
                "body": json.dumps(f"from_page exceeds total pages ({total_pages})"),
            }

        remove_range = set(range(from_page - 1, to_page))

        writer = PdfWriter()
        for i, page in enumerate(reader.pages):
            if i not in remove_range:
                writer.add_page(page)

        if len(writer.pages) == 0:
            return {
                "statusCode": 400,
                "body": json.dumps("cannot remove all pages from the PDF"),
            }

        with open(tmp_output, "wb") as f:
            writer.write(f)

        output_key = f"{REMOVED_FOLDER}/{uuid.uuid4()}.pdf"
        s3_client.upload_file(
            tmp_output,
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
            "body": json.dumps(f"error removing pages: {str(e)}"),
        }

    finally:
        for f in [tmp_input, tmp_output]:
            if os.path.exists(f):
                os.remove(f)
