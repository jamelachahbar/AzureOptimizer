from azure.monitor.query import LogsQueryClient
from azure.identity import DefaultAzureCredential, ClientSecretCredential
import os
import logging
from datetime import timedelta

# Set up logging for the module
logger = logging.getLogger(__name__)

def get_log_analytics_data(query, client_id_key, timespan):
    """
    Fetch data from the Azure Log Analytics workspace using the provided KQL query and credentials.
    
    Args:
        query (str): The Kusto Query Language (KQL) query to execute.
        client_id_key (str): The client ID key for authentication.
        timespan (timedelta): The time span for the query.
    
    Returns:
        list: A list of dictionary objects representing the rows from the Log Analytics query result.
    """
    # Determine the credentials based on client_id_key
    if client_id_key == 'OTHER':
        # Assume OTHER uses ClientSecretCredential for specific tenant/app/client ID
        tenant_id = os.getenv(f'{client_id_key}_AZURE_TENANT_ID')
        client_id = os.getenv(f'{client_id_key}_CLIENT_ID')
        client_secret = os.getenv(f'{client_id_key}_CLIENT_SECRET')
        
        if not tenant_id or not client_id or not client_secret:
            logger.error(f"Missing credentials for client_id_key: {client_id_key}")
            return []

        # Use ClientSecretCredential with custom credentials
        credential = ClientSecretCredential(tenant_id=tenant_id, client_id=client_id, client_secret=client_secret)
    else:
        # Default to managed identity or environment credentials
        credential = DefaultAzureCredential(exclude_managed_identity_credential=False)

    client = LogsQueryClient(credential)
    
    # Get the workspace ID from environment variables
    workspace_id = os.getenv('LOG_ANALYTICS_WORKSPACE_ID')
    
    if not workspace_id:
        logger.error("LOG_ANALYTICS_WORKSPACE_ID environment variable not set")
        return []

    try:
        # Execute the query with timespan
        logger.info(f"Executing Log Analytics query on workspace {workspace_id} for {client_id_key}: {query}")
        response = client.query_workspace(workspace_id=workspace_id, query=query, timespan=timespan)
        
        # Extract and format the data from the response
        if not response.tables:
            logger.error("No tables found in Log Analytics response.")
            return []

        # Get the first table in the response
        table = response.tables[0]

        # Print columns for debugging
        logger.info(f"Table columns: {table.columns}")

        # Extract columns and rows
        # Use col if it's a string or col.name otherwise
        columns = [col if isinstance(col, str) else col.name for col in table.columns]
        rows = table.rows

        # Convert rows to a list of dictionaries (column name as key)
        data = [dict(zip(columns, row)) for row in rows]
        
        return data
    
    except Exception as e:
        logger.error(f"Error querying Log Analytics: {e}")
        return []
