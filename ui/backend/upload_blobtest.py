from azure.storage.blob import BlobServiceClient
from azure.identity import DefaultAzureCredential

STORAGE_ACCOUNT_URL = "https://stgarchivecostdata.blob.core.windows.net"
CONTAINER_NAME = "costopttool"
POLICIES_FILE = "policies.yaml"
LOCAL_POLICIES_PATH = "policies/policies.yaml"

# Initialize BlobServiceClient
credential = DefaultAzureCredential()
blob_service_client = BlobServiceClient(account_url=STORAGE_ACCOUNT_URL, credential=credential)

# Upload test
try:
    container_client = blob_service_client.get_container_client(CONTAINER_NAME)
    blob_client = container_client.get_blob_client(POLICIES_FILE)
    with open(LOCAL_POLICIES_PATH, "rb") as data:
        blob_client.upload_blob(data, overwrite=True)
    print(f"Uploaded {POLICIES_FILE} successfully.")
except Exception as e:
    print(f"Error: {e}")
