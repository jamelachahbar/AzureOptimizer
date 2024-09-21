from azure.identity import DefaultAzureCredential
from azure.mgmt.resourcegraph import ResourceGraphClient
from azure.mgmt.resourcegraph.models import QueryRequest

@user_proxy.register_for_execution()
@coder.register_for_llm()
def run_kusto_query(query, subscriptions):
    """
    Executes a Kusto Query Language (KQL) query using Azure Resource Graph.

    Args:
        query (str): The KQL query to run.
        subscriptions (list): List of subscription IDs to query.

    Returns:
        dict: The response from Azure Resource Graph.
    """
    credential = DefaultAzureCredential()
    resourcegraph_client = ResourceGraphClient(credential)

    # Create the query request object
    query_request = QueryRequest(
        query=query,
        subscriptions=subscriptions
    )

    # Execute the query
    query_response = resourcegraph_client.resources(query_request)

    # Return the query result data
    return query_response.data
