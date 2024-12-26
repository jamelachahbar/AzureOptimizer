# storage_utils.py
import os
import logging
from azure.storage.blob import BlobServiceClient

# Initialize logging
logger = logging.getLogger(__name__)

# Azure Blob Storage configuration
AZURE_CONNECTION_STRING = os.getenv("AZURE_STORAGE_CONNECTION_STRING")
CONTAINER_NAME = 'costopttool'
POLICIES_FILE = 'policies.yaml'
SCHEMA_FILE = 'schema.json'
LOCAL_POLICIES_PATH = os.path.join('policies', POLICIES_FILE)  # Update with your actual local path
LOCAL_SCHEMA_PATH = os.path.join('src', SCHEMA_FILE)      # Update with your actual local path

# Initialize BlobServiceClient
blob_service_client = BlobServiceClient.from_connection_string(AZURE_CONNECTION_STRING)

container_client = blob_service_client.get_container_client(CONTAINER_NAME)

def ensure_container_and_files_exist():
    """Ensure the container and required files exist in Azure Blob Storage."""
    try:
        # Check if the container exists, create if not
        if not container_client.exists():
            container_client.create_container()
            logger.info(f"Created container: {CONTAINER_NAME}")

        # Check if policies.yaml exists, upload if not
        blob_client = container_client.get_blob_client(POLICIES_FILE)
        if not blob_client.exists():
            with open(LOCAL_POLICIES_PATH, 'rb') as data:
                blob_client.upload_blob(data)
            logger.info(f"Uploaded {POLICIES_FILE} to container: {CONTAINER_NAME}")

        # Check if schema.json exists, upload if not
        blob_client = container_client.get_blob_client(SCHEMA_FILE)
        if not blob_client.exists():
            with open(LOCAL_SCHEMA_PATH, 'rb') as data:
                blob_client.upload_blob(data)
            logger.info(f"Uploaded {SCHEMA_FILE} to container: {CONTAINER_NAME}")

    except Exception as e:
        logger.error(f"Error ensuring container and files exist: {e}")
        raise
