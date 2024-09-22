from typing import Literal
import logging
import autogen
from typing_extensions import Annotated
from azure.identity import DefaultAzureCredential
from azure.mgmt.resourcegraph import ResourceGraphClient
from azure.mgmt.resourcegraph.models import QueryRequest
from pydantic import BaseModel
from typing import List, Dict  # Add the correct import for List and Dict
from datetime import datetime, timedelta
import pytz
import csv
import azure.monitor.query
from azure.monitor.query import LogsQueryClient
print(azure.monitor.query.__version__)
from autogen import register_function
from azure.identity import AzureCliCredential
 
# Load configuration from JSON
config_list = autogen.config_list_from_json("./OAI_CONFIG_LIST.json")
llm_config = {
    "config_list": config_list, 
    "cache_seed": 30,
    "timeout": 30
}

subscription_id = "e9b4640d-1f1f-45fe-a543-c0ea45ac34c1"
threshold = 3
days = 7

# Define the prompt

# Define the prompt
# prompt =f"""
#     Please analyze my Azure environment and find all unattached disks and vm's that have a CPU threshold below {threshold}% for the last {days} days in my Azure subscription id:{subscription_id} and output 
#     the results in a table format and save the results to a csv file. Provide advice on what to do with this information and output it along with the results in the csv file.
#     """



# Define the prompt for different types of resources, this prompt gives us good results
resources = ["Microsoft.Compute/disks", "Microsoft.Compute/virtualMachines", "Microsoft.Network/publicIPAddresses", "Microsoft.Network/networkInterfaces"]
prompt= f"""
Please analyze my Azure environment and find opportunities to save money. Give me a shortlist. Look for these types of resources {resources}
"""
# Define the prompt for storage account -> working
# prompt =f"""
#     Please analyze my Azure environment and find all potential saving for these resources: {resources}, and check if possible if they haven't been used or not used much based on usage since last {days} days in my Azure subscription id:{subscription_id} and output 
#     the results in a table format and save the results to a csv file. Provide advice on what to do with this information and output it along with the results in the csv file.
#     1. First create a plan
#     2. The plan should first get a list of all impacted resources: {resources} in the subscription, then check the last usage data.
#     3. If the impacted resources: {resources} show low to no usage in the last {days} days, mark it as idle. You can leverage logs like activity logs in azure monitor to get this data.
#     4. Output the list of impacted resources: {resources} in a table format.
#     5. Save the results to a csv file.
#     6. Provide advice on what to do with this information and output it along with the results in the csv file.
#     7. Make sure you mention the impacted resources: {resources} name, resource group, last activity and type of activity depending on the resource, subscription id and the recommendation.
#     When we talk about activity, for disks it is the unattached state and VM's it's CPU usage below threshold of {threshold}, for public IP's it's the number of connections and for network interfaces it's the number of connections. For storage accounts it's the number of read and write operations and last access time.
#     """

# Define the prompt for storage account and unutilized resources like disks, public ip's and network interfaces
# prompt =f"""
#     Please analyze my Azure environment and find all storage accounts that haven't been accessed, unattached disks, unattached public ip's and unattached network interfaces since last {days} days in my Azure subscription id:{subscription_id} and output
#     the results in a table format and save the results to a csv file. 
#     Provide advise on what to do with this information, output it along with the results in the csv file.
#     """
# prompt =f"""
#     You are a FinOps Expert Team and Azure Guru with 10 years experience.
#     Please analyze my Azure environment based on status and usage using platform metrics from last {days} days and find top 5 savings opportunities and the resources related to this in my subscription id:{subscription_id} and output
#     the results in a table format and save the results to a csv file. 
#     Provide advise on what to do with this information, output it along with the results in the csv file.
#     Make sure you mention the resource type, resource name, resourcegroup, additional properties, subscriptionid and the recommendation."""

# prompt = f"""
#     You are a FinOps Expert Team and Azure Gurus with 10 years experience.
#     Please analyze my Azure environment based on status and usage using platform metrics and find top 5 savings opportunities and the resources related to this in my subscription id:{subscription_id} and output
#     the results in a table format and save the results to a csv file. 
#     Provide advice on what to do with this information, output it along with the results in the csv file.
# """

# Initialize the Planner
planner = autogen.AssistantAgent(
    name="Planner",
    system_message="""You are a helpful AI Assistant. You are the planner of this team of assistants. You plan the tasks and make sure everything is on track.
    Suggest a plan. Revise the plan if needed.""",
    llm_config=llm_config
)

def ask_planner(message):
    """A placeholder ask_planner method for testing."""
    logging.info(f"Planner received the following message: {message}")
    return f"Planner response to: {message}"

# Create UserProxyAgent
user_proxy = autogen.UserProxyAgent(
    name="user_proxy",
    human_input_mode="NEVER",
    system_message="You are a helpful AI Assistant. You are the user proxy. You can execute the code and interact with the system.",
    description="""User Proxy is a user who can execute the code and interact with the system. I also check if the plan was applied and the output we have is according to the instructions.
    If not, I will ask the planner to revise the plan.""",
    max_consecutive_auto_reply=10,
    code_execution_config=
    {
        "work_dir": "coding",
        "use_docker": "python:3.10"
    }
)

# Create an AssistantAgent for coding with external KQL handling
coder = autogen.AssistantAgent(
    name="Code_Guru",
    system_message="""You are a helpful AI Assistant. You are a highly experienced programmer specialized in Azure. 
    Follow the approved plan and save the code to disk. Always use functions you have access to and start with run_kusto_query
    When using code, you must indicate the script type in the code block. 
    The user cannot provide any other feedback or perform any other action beyond executing the code you suggest. 
    The user can't change your code. 
    So do not suggest incomplete code which requires users to modify. 
    Don't use a code block if it's not intended to be executed by the user.
    If the result indicates there is an error, fix the error and output the code again. Suggest the 
    full code instead of partial code or code changes. If the error can't be fixed or if the task is 
    not solved even after the code is executed successfully, analyze the problem, revisit your 
    assumption, collect additional info you need, and think of a different approach to try.
    When you find an answer, verify the answer carefully. Include verifiable evidence in your response 
    if possible.
    Reply "TERMINATE" in the end when everything is done""", 
    description="I'm a highly experienced programmer specialized in Python, bash. I am **ONLY** allowed to speak **immediately** after `Planner`.",
    llm_config={
        "cache_seed": 0,  # Seed for caching and reproducibility was 42
        "config_list": config_list,  # List of OpenAI API configurations
        "temperature": 0  # Temperature for sampling
    },
    human_input_mode="NEVER"
)

critic = autogen.AssistantAgent(
    name="Critic",
    system_message="""Critic. You are a helpful assistant highly skilled in evaluating the quality of a given code by providing a score from 1 (bad) - 10 (good) while providing clear rationale. YOU MUST CONSIDER VISUALIZATION BEST PRACTICES for each evaluation. Specifically, you can carefully evaluate the code across the following dimensions:
- bugs (bugs):  are there bugs, logic errors, syntax error or typos? Are there any reasons why the code may fail to compile? How should it be fixed? If ANY bug exists, the bug score MUST be less than 5.
- Data transformation (transformation): Is the data transformed appropriately for the type? E.g., is the dataset appropriated filtered, aggregated, or grouped if needed? If a date field is used, is the date field first converted to a date object etc?
- Goal compliance (compliance): how well the code meets the specified goals?
- Visualization type (type): CONSIDERING BEST PRACTICES, is the type appropriate for the data and intent? Is there a type that would be more effective in conveying insights? If a different type is more appropriate, the score MUST BE LESS THAN 5.
- Data encoding (encoding): Is the data encoded appropriately for the type?
- Aesthetics (aesthetics): Are the aesthetics of the appropriate for the type and the data?

YOU MUST PROVIDE A SCORE for each of the above dimensions.
{bugs: 0, transformation: 0, compliance: 0, type: 0, encoding: 0, aesthetics: 0}
Do not suggest code.
Finally, based on the critique above, suggest a concrete list of actions that the coder should take to improve the code.""",
    llm_config=llm_config,
)

# Custom Pydantic model to handle query results
class KustoQueryResult(BaseModel):
    data: List[dict]  # You can customize this to fit the exact structure of your query response

# Define Kusto Query Function
def run_kusto_query(query: Annotated[str, "The KQL query"], subscriptions: Annotated[List[str], "List of subscription IDs"]) -> List[Dict]:
    credential = DefaultAzureCredential()
    resourcegraph_client = ResourceGraphClient(credential)
    
    query_request = QueryRequest(query=query, subscriptions=subscriptions)
    query_response = resourcegraph_client.resources(query_request)
    
    return query_response.data

# Register Kusto Query Function
register_function(
    run_kusto_query,
    caller=coder,
    executor=user_proxy,
    name="run_kusto_query",
    description="This function generates the code to run a Kusto Query Language (KQL) query using Azure Resource Graph.",
)

# Define Log Query Function with Annotations
def run_log_query(
    workspace_id: Annotated[str, "The Log Analytics Workspace GUID"],
    query: Annotated[str, "The KQL query to run on the log data"],
    days: Annotated[int, "The number of days to query logs for"] = 1,
    use_cli_credential: bool = False
) -> List[Dict]:
    """
    Executes a log query on Azure Monitor Logs for a specified Log Analytics Workspace.

    Args:
        workspace_id (str): The Log Analytics Workspace GUID.
        query (str): The KQL query to run on the log data.
        days (int): The number of days to query logs for.
        use_cli_credential (bool): Whether to use Azure CLI Credential for authentication (default is False).

    Returns:
        List[Dict]: The logs data as a list of dictionaries or an empty list in case of an error.
    """
    # Choose the credential type based on the input parameter
    if use_cli_credential:
        logging.info("Using Azure CLI Credential for authentication.")
        credential = AzureCliCredential()  # CLI context
    else:
        logging.info("Using Default Azure Credential for authentication.")
        credential = DefaultAzureCredential()  # Default context for broader use cases

    logs_client = LogsQueryClient(credential)
    # workspace_id = "608cd3e5-cf6b-4fa0-ac79-b5db5136c18f"  # This should be the Workspace GUID, not the full ARM path

    # Calculate the time range for the query
    utc = pytz.UTC
    end_time = utc.localize(datetime.utcnow())
    start_time = end_time - timedelta(days=days)

    log_data = []

    # Debug: log start and end time
    logging.info(f"Querying logs from {start_time} to {end_time} in workspace {workspace_id}")

    try:
        # Execute the log query
        response = logs_client.query_workspace(
            workspace_id="608cd3e5-cf6b-4fa0-ac79-b5db5136c18f",
            query=query,
            timespan=(start_time, end_time)
        )

        # Check for empty response
        if not response.tables:
            logging.warning("No tables found in the response.")
            return []

        # Process the response
        for table in response.tables:
            for row in table.rows:
                log_data.append({col.name: val for col, val in zip(table.columns, row)})

        logging.info(f"Successfully retrieved {len(log_data)} rows of data.")
        return log_data

    except Exception as e:
        # Improved error handling with logging
        logging.error(f"Error querying logs: {str(e)}", exc_info=True)
        return []
# Register Log Query Function
register_function(
    run_log_query,
    caller=coder,
    executor=user_proxy,
    name="run_log_query",
    description="This function executes a log query using Azure Monitor Logs.",
)

# Define the function to save results to CSV
# Define the function to save results to CSV
def save_results_to_csv(results: List[Dict], filename: str = "azure_analysis_results.csv") -> str:
    if not results:
        return "No results to save."

    # Extract keys from the first result to use as column headers
    keys = results[0].keys() if results else []
    
    # Save results to a CSV file
    with open(filename, mode='w', newline='') as file:
        writer = csv.DictWriter(file, fieldnames=keys)
        writer.writeheader()
        writer.writerows(results)
    
    return f"Results successfully saved to {filename}"

# Register Save to CSV Function
register_function(
    save_results_to_csv,
    caller=coder,
    executor=user_proxy,
    name="save_results_to_csv",
    description="A tool to save results to CSV.",
)

# Initialize GroupChat
groupchat = autogen.GroupChat(
    agents=[planner, coder, critic, user_proxy], 
    messages=[],  # Start with no messages
    max_round=50,
    speaker_selection_method="round_robin",
    select_speaker_prompt_template="Please select the next speaker from the list: {speaker_list}",
)

# Initiate chat between the user_proxy and assistant
manager = autogen.GroupChatManager(groupchat=groupchat, llm_config=llm_config)

# Initiate chat
user_proxy.initiate_chat(
    manager,
    message=prompt,
    summary_method="reflection_with_llm"
)
