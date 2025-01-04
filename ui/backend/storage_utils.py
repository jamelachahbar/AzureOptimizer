import os
import logging
from azure.storage.blob import BlobServiceClient
from azure.identity import DefaultAzureCredential

# Initialize logging
logging.basicConfig(level=logging.DEBUG)  # DEBUG level for detailed logs
logger = logging.getLogger(__name__)

# Azure Blob Storage configuration
STORAGE_ACCOUNT_URL = os.getenv("STORAGE_ACCOUNT_URL")
CONTAINER_NAME = 'costopttool'
POLICIES_FILE = 'policies.yaml'
SCHEMA_FILE = 'schema.json'
LOCAL_POLICIES_PATH = os.path.join('policies', POLICIES_FILE)
LOCAL_SCHEMA_PATH = os.path.join('src', SCHEMA_FILE)

# Use DefaultAzureCredential for authentication
credential = DefaultAzureCredential()
blob_service_client = BlobServiceClient(account_url=STORAGE_ACCOUNT_URL, credential=credential)
container_client = blob_service_client.get_container_client(CONTAINER_NAME)

def ensure_container_and_files_exist():
    """Ensure the container and required files exist in Azure Blob Storage."""
    try:
        # Check or create container
        try:
            container_client.create_container()
            logger.info(f"Container {CONTAINER_NAME} created successfully.")
        except Exception as e:
            if "ContainerAlreadyExists" in str(e):
                logger.info(f"Container {CONTAINER_NAME} already exists.")
            else:
                logger.error(f"Error creating container: {e}")
                raise

        # Define file mappings (local path -> blob name)
        files_to_upload = {
            LOCAL_POLICIES_PATH: os.path.basename(POLICIES_FILE),  # Use only file name as blob name
            LOCAL_SCHEMA_PATH: os.path.basename(SCHEMA_FILE),     # Use only file name as blob name
        }

        # Upload blobs
        for local_path, blob_name in files_to_upload.items():
            try:
                if not os.path.exists(local_path):
                    logger.error(f"Local file {local_path} does not exist. Skipping upload.")
                    continue

                blob_client = container_client.get_blob_client(blob_name)
                with open(local_path, 'rb') as data:
                    blob_client.upload_blob(data, overwrite=True)
                logger.info(f"Uploaded {blob_name} successfully.")
            except Exception as e:
                logger.error(f"Error uploading blob {blob_name}: {e}")
                raise

    except Exception as e:
        logger.error(f"Overall error in ensure_container_and_files_exist: {e}")
        raise

def update_policies_file():
    """Update the policies.yaml file in Blob Storage when modified locally."""
    try:
        if not os.path.exists(LOCAL_POLICIES_PATH):
            logger.error(f"Local file {LOCAL_POLICIES_PATH} does not exist.")
            return

        blob_client = container_client.get_blob_client(POLICIES_FILE)
        with open(LOCAL_POLICIES_PATH, 'rb') as data:
            blob_client.upload_blob(data, overwrite=True)
        logger.info(f"Policies file {POLICIES_FILE} updated successfully in Blob Storage.")
    except Exception as e:
        logger.error(f"Error updating policies file: {e}")
        raise
