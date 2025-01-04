from azure.identity import DefaultAzureCredential
from azure.storage.blob import BlobServiceClient

credential = DefaultAzureCredential()
token = credential.get_token("https://storage.azure.com/.default")
print(f"Token Scope: {token.token}")
