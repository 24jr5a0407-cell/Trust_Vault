import io
import boto3
from botocore.config import Config
from botocore.exceptions import ClientError
from config import B2_BUCKET_NAME, B2_KEY_ID, B2_APPLICATION_KEY, B2_ENDPOINT_URL
from logger import logger

# Backward compatibility alias
B2_BUCKET = B2_BUCKET_NAME

# Initialize B2 S3 Client conditionally if credentials are configured
s3_client = None
if B2_KEY_ID and B2_APPLICATION_KEY and B2_BUCKET_NAME:
    try:
        s3_client = boto3.client(
            "s3",
            endpoint_url=B2_ENDPOINT_URL,
            aws_access_key_id=B2_KEY_ID,
            aws_secret_access_key=B2_APPLICATION_KEY,
            config=Config(
                signature_version="s3v4", 
                connect_timeout=5, 
                read_timeout=15,
                max_pool_connections=100
            )
        )
        logger.info(f"Initialized Backblaze B2 client for bucket: {B2_BUCKET_NAME}")
    except Exception as e:
        logger.error(f"Failed to initialize Backblaze B2 S3 client: {e}")
else:
    logger.warning("Backblaze B2 credentials not fully configured; cloud object storage running in mock/disabled mode.")


def upload_file_to_b2(file_obj, filename: str, is_personal: bool = False, user_email: str = "") -> str:
    """
    Uploads a file stream directly to Backblaze B2 cloud storage.
    - Official documents: saved in 'official-documents/<unique_filename>'
    - Personal documents: saved in 'personal-documents/<clean_user>/<unique_filename>'
    """
    if is_personal:
        clean_user = (user_email or "unknown_user").replace("/", "_").strip()
        storage_key = f"personal-documents/{clean_user}/{filename}"
    else:
        storage_key = f"official-documents/{filename}"

    if not s3_client:
        logger.warning(f"B2 S3 client not configured. Skipping cloud upload for {storage_key}.")
        return storage_key

    try:
        file_obj.seek(0)
        s3_client.upload_fileobj(file_obj, B2_BUCKET_NAME, storage_key)
        logger.info(f"Successfully uploaded {filename} to Backblaze B2 at key: {storage_key}")
        return storage_key
    except Exception as e:
        logger.error(f"Failed to upload {filename} to Backblaze B2: {e}")
        raise


def get_file_from_b2(storage_key: str):
    """
    Downloads file stream from Backblaze B2 into an in-memory BytesIO stream.
    Returns (io.BytesIO, content_type)
    """
    if not s3_client:
        raise RuntimeError("B2 storage client is not configured.")

    try:
        logger.info(f"Fetching object from Backblaze B2: {storage_key}")
        response = s3_client.get_object(Bucket=B2_BUCKET_NAME, Key=storage_key)
        content_type = response.get("ContentType", "application/octet-stream")
        stream = io.BytesIO(response["Body"].read())
        stream.seek(0)
        return stream, content_type
    except ClientError as e:
        logger.error(f"Backblaze B2 client error retrieving {storage_key}: {e}")
        raise
    except Exception as e:
        logger.error(f"Unexpected error retrieving {storage_key} from B2: {e}")
        raise


def delete_file_from_b2(storage_key: str):
    """Deletes an object from Backblaze B2."""
    if not s3_client:
        logger.warning(f"B2 client not configured. Skipping cloud deletion for {storage_key}.")
        return

    try:
        logger.info(f"Deleting object from Backblaze B2: {storage_key}")
        s3_client.delete_object(Bucket=B2_BUCKET_NAME, Key=storage_key)
    except ClientError as e:
        logger.warning(f"ClientError while deleting {storage_key} from B2: {e}")
    except Exception as e:
        logger.warning(f"Unexpected error while deleting {storage_key} from B2: {e}")
