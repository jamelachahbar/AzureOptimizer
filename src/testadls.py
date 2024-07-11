import os
import logging
import argparse
import pandas as pd
from azure.identity import DefaultAzureCredential
from azure.storage.filedatalake import DataLakeServiceClient
import io
import sys
from dotenv import load_dotenv

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Set FORCE_COLOR to 1 to ensure color output
os.environ["FORCE_COLOR"] = "1"

# Check if environment variables are already set, if not, load from .env file
if not os.getenv("AZURE_CLIENT_ID"):
    load_dotenv()

# Authentication
credential = DefaultAzureCredential()

# Verify that the necessary environment variables are set and log their values
required_env_vars = [
    "AZURE_CLIENT_ID",
    "AZURE_TENANT_ID",
    "AZURE_CLIENT_SECRET",
    "AZURE_SUBSCRIPTION_ID",
    "AZURE_STORAGE_ACCOUNT_NAME",
    "AZURE_STORAGE_FILE_SYSTEM_NAME",
    "ADLS_DIRECTORY_PATH"
]
for var in required_env_vars:
    value = os.getenv(var)
    if not value:
        logging.error(f"Environment variable {var} is not set.")
        sys.exit(1)
    logging.info(f"{var}: {value}")

# Read environment variables for storage account and file system
account_name = os.getenv('AZURE_STORAGE_ACCOUNT_NAME')
file_system_name = os.getenv('AZURE_STORAGE_FILE_SYSTEM_NAME')

# Check if environment variables are set correctly
if not account_name or not file_system_name:
    logger.error("Environment variables AZURE_STORAGE_ACCOUNT_NAME or AZURE_STORAGE_FILE_SYSTEM_NAME are not set.")
else:
    logger.info(f"Using storage account: {account_name}")
    logger.info(f"Using file system: {file_system_name}")

# Authentication and client setup
service_client = DataLakeServiceClient(
    account_url=f"https://{account_name}.dfs.core.windows.net",
    credential=credential
)

# Function to list files in a directory
def list_files_in_directory(directory_path):
    try:
        file_system_client = service_client.get_file_system_client(file_system_name)
        paths = file_system_client.get_paths(path=directory_path)

        files = []
        folders = []
        for path in paths:
            if path.is_directory:
                folders.append(path.name)
            else:
                files.append(path.name)

        logger.info(f"Folders in directory {directory_path}: {folders}")
        logger.info(f"Files in directory {directory_path}: {files}")

        return files
    except Exception as e:
        logger.error(f"Error listing files in directory {directory_path}: {e}")
        return []

def read_parquet_file_from_adls(file_path):
    try:
        file_system_client = service_client.get_file_system_client(file_system_name)
        file_client = file_system_client.get_file_client(file_path)

        download = file_client.download_file()
        downloaded_bytes = download.readall()

        df = pd.read_parquet(io.BytesIO(downloaded_bytes))
        return df
    except Exception as e:
        logger.error(f"Error reading Parquet file {file_path}: {e}")
        return pd.DataFrame()

def main(directory_path):
    # List files in the directory
    files = list_files_in_directory(directory_path)
    if not files:
        logger.error(f"No files found in directory {directory_path}")
        sys.exit(1)

    # Read the first file
    file_path = files[0]
    logger.info(f"Reading file: {file_path}")
    try:
        df = read_parquet_file_from_adls(file_path)
        logger.info(f"Dataframe shape: {df.shape}")
        logger.info(f"Dataframe columns: {df.columns}")
        logger.info(f"Dataframe head: {df.head()}")
    except Exception as e:
        logger.error(f"Error reading file {file_path}: {e}")
        sys.exit(1)

    # Analyze the data
    logger.info("Analyzing data...")
    try:
        # Group by the "Resource Group" column and sum the "PreTaxCost" column
        cost_data = df.groupby("x_ResourceGroupName")["BilledCost"].sum()
        logger.info(f"Cost data: {cost_data}")
    except Exception as e:
        logger.error(f"Error analyzing data: {e}")
        sys.exit(1)

    logger.info("Done")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Fetch and analyze cost data from ADLS")
    parser.add_argument("--directory-path", required=True, help="Directory path in ADLS to fetch Parquet files")
    args = parser.parse_args()

    main(args.directory_path)
