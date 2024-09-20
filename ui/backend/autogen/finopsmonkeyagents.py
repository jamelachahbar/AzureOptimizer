from typing import Literal
import logging
import autogen
from typing_extensions import Annotated
from auto_gen_assistant import AutoGenAssistant
from azure.identity import DefaultAzureCredential
from azure.mgmt.resourcegraph import ResourceGraphClient
from azure.mgmt.resourcegraph.models import QueryRequest
from pydantic import BaseModel
from typing import List, Dict  # Add the correct import for List and Dict
from azure.monitor.query import MetricsQueryClient
from datetime import timedelta
from typing import List, Dict
import csv

# Load configuration from JSON
config_list = autogen.config_list_from_json("./OAI_CONFIG_LIST.json")
llm_config = {
    "config_list": config_list, 
    "cache_seed": 0,
    "timeout": 120
                }

subscription_id = "e9b4640d-1f1f-45fe-a543-c0ea45ac34c1"

# Define the prompt
prompt = """
    Please analyze my Azure environment and find all unattached disks and vm's that have a CPU threshold below 5% for the last 7 days in my Azure subscription id:e9b4640d-1f1f-45fe-a543-c0ea45ac34c1 and output 
    the results in a table format and save the results to a csv file. Provide advice on what to do with this information and output it along with the results in the csv file.
    """

# Initialize the Planner
planner = autogen.AssistantAgent(
            name="Planner",
            system_message="""You are the planner of this team of assistants. You plan the tasks and make sure everything is on track.
            Suggest a plan. Revise the plan based on feedback from user_proxy and get his approval.""",
            llm_config=llm_config
        )
def ask_planner(self, message):
        """A placeholder ask_planner method for testing."""
        logging.info(f"Planner received the following message: {message}")
        return f"Planner response to: {message}"




            # code_execution_config={
            #     "work_dir": "coding",
            #     "use_docker": "python:3.11"
            # },

# Create UserProxyAgent
user_proxy = autogen.UserProxyAgent(
    name="user_proxy",
    human_input_mode="TERMINATE",
    max_consecutive_auto_reply=10,
    code_execution_config=False,
    function_map={"ask_planner": ask_planner}
)

# Create an AssistantAgent for coding with external KQL handling
coder = autogen.AssistantAgent(
    name="Code_Guru",
    system_message="""You are a highly experienced programmer specialized in Azure. 
    Follow the approved plan and save the code to disk.
    If you see a request to get data from the environment, only use the functions you
    have been provided with. You can even combinne them. Reply TERMINATE when the task is done.""", 
    llm_config={
        "cache_seed": 42,  # Seed for caching and reproducibility
        "config_list": config_list,  # List of OpenAI API configurations
        "temperature": 0  # Temperature for sampling
    },
    human_input_mode="NEVER"
    # function_map={"run_kusto_query": run_kusto_query}
)


        # Create an AssistantAgent for FinOps
finops_expert = autogen.AssistantAgent(
            name="Finops_Expert",
            system_message="You are an Azure Expert specialized in FinOps and Azure Cost Optimization. You provide the highest level of expertise in FinOps and Azure Cost Optimization. Don't give any programming advice or code advice.",
            llm_config=llm_config,
            human_input_mode="NEVER"
        )

        # Create the GroupChat and GroupChatManager




# Custom Pydantic model to handle query results
class KustoQueryResult(BaseModel):
    data: List[dict]  # You can customize this to fit the exact structure of your query response

@user_proxy.register_for_execution()
@coder.register_for_llm(description="Kusto Query code creator")
def run_kusto_query(query: str, subscriptions: List[str]) -> List[Dict]:
    """
    Executes a Kusto Query Language (KQL) query using Azure Resource Graph.

    Args:
        query (str): The KQL query to run.
        subscriptions (list): List of subscription IDs to query.

    Returns:
        List[Dict]: The response from Azure Resource Graph as a list of dictionaries.
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

    # Return the query result as a list of dictionaries
    return query_response.data  # Already a list of dictionaries



# Custom Pydantic model to handle CPU query results
class MetricsQueryResult(BaseModel):
    metric_data: List[Dict]



# Custom Pydantic model to handle CPU query results
class MetricsQueryResult(BaseModel):
    metric_data: List[Dict]

@user_proxy.register_for_execution()
@coder.register_for_llm(description="Monitor metrics query creator")
def query_metrics(resource_id: str, metric_name: str, timespan: str = "P7D", aggregation: List[str] = ['Average']) -> List[Dict]:
    """
    Generalizes the Azure Monitor metrics query to work with any resource and metric.
    Args:
        resource_id (str): The resource ID of the Azure resource.
        metric_name (str): The name of the metric to query (e.g., "Percentage CPU").
        timespan (str): The time span for which to query metrics, in ISO8601 duration format (e.g., "P7D" for 7 days).
        aggregation (List[str]): The type of aggregation (e.g., ["Average", "Total"]).
    Returns:
        List[Dict]: The metrics data as a list of dictionaries.
    """
    credential = DefaultAzureCredential()
    client = MetricsQueryClient(credential)

    # Query Azure Monitor for the specified metric
    response = client.query(
        resource_id,
        metric_names=[metric_name],
        timespan=timespan,
        interval="PT1H",  # 1 hour interval in ISO 8601 duration format
        aggregation=aggregation
    )

    # Process the result
    metric_data = []
    for metric in response.metrics:
        for time_series in metric.timeseries:
            for data in time_series.data:
                metric_data.append({
                    "timestamp": data.timestamp,
                    "value": data.average if "Average" in aggregation else data.total
                })

    return metric_data  # List of dictionaries


class FullAnalysisResult(BaseModel):
    analysis_data: List[Dict]

@user_proxy.register_for_execution()
@coder.register_for_llm(description="orchestrate full analysis")
def run_full_analysis(subscription_id: str, resource_type: str, fields: List[str], metric_name: str) -> List[Dict]:
    """
    Orchestrates the full analysis by:
    1. Querying Azure Resource Graph for the specified resource type.
    2. Querying Azure Monitor for the specified metric for each resource.
    
    Args:
        subscription_id (str): Azure subscription ID.
        resource_type (str): The resource type to query (e.g., "microsoft.compute/virtualmachines").
        fields (List[str]): The fields to return for the resource (e.g., ["name", "id", "location"]).
        metric_name (str): The metric to query (e.g., "Percentage CPU").

    Returns:
        List[Dict]: Combined results of unattached disks and VMs with CPU usage below 5%.
    """
    # Collect results for returning in a structured format
    results = []
    
    # Step 1: Query Resource Graph for the specified resource type
    resource_results = run_kusto_query(resource_type, subscription_id, fields)

    # Iterate over each resource and fetch its metrics
    for resource in resource_results:
        resource_id = resource['id']
        print(f"Fetching {metric_name} metrics for Resource: {resource['name']} (Resource ID: {resource_id})")

        # Step 2: Query Azure Monitor for the specified metric
        metrics_result = query_metrics(resource_id, metric_name)

        # Collect the results in the structured format
        for metric_data in metrics_result:
            result = {
                "Resource Name": resource['name'],
                "Resource ID": resource_id,
                "Location": resource.get('location', ''),
                "Timestamp": metric_data['timestamp'],
                f"{metric_name}": metric_data['value']
            }
            results.append(result)

    # Return the combined results
    return results


@user_proxy.register_for_execution()
@coder.register_for_llm(description="save results to csv")
def save_results_to_csv(results: List[Dict], filename: str = "azure_analysis_results.csv") -> str:
    """
    Saves the results to a CSV file and returns a confirmation message.
    
    Args:
        results (List[Dict]): The list of results to save.
        filename (str): The name of the CSV file.

    Returns:
        str: A confirmation message with the path to the saved file.
    """
    keys = results[0].keys() if results else []
    
    with open(filename, mode='w', newline='') as file:
        writer = csv.DictWriter(file, fieldnames=keys)
        writer.writeheader()
        writer.writerows(results)
    
    # Return a confirmation message
    return f"Results successfully saved to {filename}"


groupchat = autogen.GroupChat(
            agents=[planner, coder, finops_expert, user_proxy, ], 
            messages=[],  # Start with no messages
            max_round=100,
            speaker_selection_method="round_robin"
        )
manager = autogen.GroupChatManager(groupchat=groupchat, llm_config=llm_config)

# Initiate a chat between the user_proxy and the assistant
user_proxy.initiate_chat(
            manager,
            message=prompt,
            summary_method="reflection_with_llm"

        )