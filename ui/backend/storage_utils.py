import os
import json
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

# Result files that need to be persisted to blob storage
RESULT_FILES = [
    'impacted_resources.json',
    'execution_data.json',
    'summary_reports.json',
    'anomalies_all.json',
]

# Use DefaultAzureCredential for authentication
credential = DefaultAzureCredential()

# Initialize blob storage clients only if storage account URL is configured
if STORAGE_ACCOUNT_URL and STORAGE_ACCOUNT_URL != "https://azureoptimizer726653.blob.core.windows.net/":
    blob_service_client = BlobServiceClient(account_url=STORAGE_ACCOUNT_URL, credential=credential)
    container_client = blob_service_client.get_container_client(CONTAINER_NAME)
else:
    blob_service_client = None
    container_client = None
    logger.warning("Azure Storage Account not configured. Storage features will be disabled.")

def ensure_container_and_files_exist():
    """Ensure the container and required files exist in Azure Blob Storage."""
    if not container_client:
        logger.info("Storage account not configured. Skipping container setup.")
        return
    
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
    if not container_client:
        logger.info("Storage account not configured. Skipping policies file update.")
        return
    
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


def upload_result_file(filename: str, data: dict) -> bool:
    """Upload a result file (JSON) to blob storage for persistence across container restarts."""
    if not container_client:
        logger.debug(f"Storage not configured. Skipping upload of {filename}")
        return False
    
    try:
        blob_client = container_client.get_blob_client(filename)
        json_data = json.dumps(data, indent=4, default=str)
        blob_client.upload_blob(json_data, overwrite=True)
        logger.info(f"Uploaded {filename} to blob storage ({len(data)} items)")
        return True
    except Exception as e:
        logger.error(f"Error uploading {filename} to blob storage: {e}")
        return False


def download_result_file(filename: str) -> dict | list | None:
    """Download a result file (JSON) from blob storage."""
    if not container_client:
        logger.debug(f"Storage not configured. Cannot download {filename}")
        return None
    
    try:
        blob_client = container_client.get_blob_client(filename)
        download_stream = blob_client.download_blob()
        content = download_stream.readall().decode('utf-8')
        data = json.loads(content)
        logger.info(f"Downloaded {filename} from blob storage ({len(data) if isinstance(data, list) else 'dict'} items)")
        return data
    except Exception as e:
        if "BlobNotFound" in str(e):
            logger.debug(f"Blob {filename} not found in storage")
        else:
            logger.warning(f"Error downloading {filename} from blob storage: {e}")
        return None


def upload_all_result_files(base_dir: str = ".") -> dict:
    """Upload all result files to blob storage."""
    results = {}
    for filename in RESULT_FILES:
        filepath = os.path.join(base_dir, filename)
        if os.path.exists(filepath):
            try:
                with open(filepath, 'r') as f:
                    data = json.load(f)
                results[filename] = upload_result_file(filename, data)
            except Exception as e:
                logger.error(f"Error reading {filepath}: {e}")
                results[filename] = False
        else:
            logger.debug(f"Result file {filepath} does not exist, skipping")
            results[filename] = False
    return results


def download_all_result_files(base_dir: str = ".") -> dict:
    """Download all result files from blob storage to local disk."""
    results = {}
    for filename in RESULT_FILES:
        data = download_result_file(filename)
        if data is not None:
            filepath = os.path.join(base_dir, filename)
            try:
                with open(filepath, 'w') as f:
                    json.dump(data, f, indent=4, default=str)
                results[filename] = True
                logger.info(f"Saved {filename} to {filepath}")
            except Exception as e:
                logger.error(f"Error saving {filepath}: {e}")
                results[filename] = False
        else:
            results[filename] = False
    return results