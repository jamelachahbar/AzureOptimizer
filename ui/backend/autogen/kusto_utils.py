# kusto_utils.py
from azure.identity import DefaultAzureCredential
from azure.mgmt.resourcegraph import ResourceGraphClient
from azure.mgmt.resourcegraph.models import QueryRequest

def run_kusto_query(query):
    """
    Executes a Kusto query against the Azure Resource Graph for a given subscription.
    
    Parameters:
    - query (str): The Kusto query to execute.

    Returns:
    - The result of the Kusto query as a list of resources.
    """
    # Authenticate using the DefaultAzureCredential
    credential = DefaultAzureCredential()

    # Initialize the Azure Resource Graph client
    client = ResourceGraphClient(credential)

    # Define the query request
    request = QueryRequest(
        query=query
    )

    # Execute the query and return the result
    response = client.resources(request)

    return response.data
