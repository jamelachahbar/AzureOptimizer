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
from datetime import timedelta
import csv
import azure.monitor.query
print(azure.monitor.query.__version__)
from autogen import register_function

# Load configuration from JSON
config_list = autogen.config_list_from_json("./OAI_CONFIG_LIST.json")
llm_config = {
    "config_list": config_list, 
    "cache_seed": 42,
    "timeout": 30
                }

subscription_id = "e9b4640d-1f1f-45fe-a543-c0ea45ac34c1"
threshold = 5
days = 30
# Define the prompt
# prompt =f"""
#     Please analyze my Azure environment and find all unattached disks and vm's that have a CPU threshold below {threshold}% for the last {days} days in my Azure subscription id:{subscription_id} and output 
#     the results in a table format and save the results to a csv file. Provide advice on what to do with this information and output it along with the results in the csv file.
#     """


# Define the prompt for storage account -> working
# prompt =f"""
#     Please analyze my Azure environment and find all idle storage accounts since last {days} days in my Azure subscription id:{subscription_id} and output 
#     the results in a table format and save the results to a csv file. Provide advice on what to do with this information and output it along with the results in the csv file.
#     """

# Define the prompt for storage account and unutilized resources like disks, public ip's and network interfaces
# prompt =f"""
#     Please analyze my Azure environment and find all storage accounts that haven't been accessed, unattached disks, unattached public ip's and unattached network interfaces since last {days} days in my Azure subscription id:{subscription_id} and output
#     the results in a table format and save the results to a csv file. 
#     Provide advise on what to do with this information, output it along with the results in the csv file.
#     """
prompt =f"""
    You are a FinOps Expert Team and Azure Guru with 10 years experience.
    Please analyze my Azure environment based on status and usage using platform metrics and find top 5 savings opportunities and the resources related to this in my subscription id:{subscription_id} and output
    the results in a table format and save the results to a csv file. 
    Provide advise on what to do with this information, output it along with the results in the csv file."""
# Initialize the Planner
planner = autogen.AssistantAgent(
            name="Planner",
            system_message="""You are a helpful AI Assistant. You are the planner of this team of assistants. You plan the tasks and make sure everything is on track.
            Suggest a plan. Revise the plan if needed.""",
            llm_config=llm_config
        )
def ask_planner( message):
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
    Follow the approved plan and save the code to disk. 
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
    description="I'm a highly exmperienced programmer specialized in Azure, bash, linux and azure cli. I am **ONLY** allowed to speak **immediately** after `Planner`.",
    llm_config={
        "cache_seed": 0,  # Seed for caching and reproducibility was 42
        "config_list": config_list,  # List of OpenAI API configurations
        "temperature": 0  # Temperature for sampling
    },
    human_input_mode="NEVER"
    # function_map={"run_kusto_query": run_kusto_query}
)

critic = autogen.AssistantAgent(
    name="Critic",
    system_message="""Critic. You are a helpful assistant highly skilled in evaluating the quality of a given code by providing a score from 1 (bad) - 10 (good) while providing clear rationale. YOU MUST CONSIDER VISUALIZATION BEST PRACTICES for each evaluation. Specifically, you can carefully evaluate the code across the following dimensions
- bugs (bugs):  are there bugs, logic errors, syntax error or typos? Are there any reasons why the code may fail to compile? How should it be fixed? If ANY bug exists, the bug score MUST be less than 5.
- Data transformation (transformation): Is the data transformed appropriately for the  type? E.g., is the dataset appropriated filtered, aggregated, or grouped  if needed? If a date field is used, is the date field first converted to a date object etc?
- Goal compliance (compliance): how well the code meets the specified  goals?
- Visualization type (type): CONSIDERING BEST PRACTICES, is the  type appropriate for the data and intent? Is there a type that would be more effective in conveying insights? If a different type is more appropriate, the score MUST BE LESS THAN 5.
- Data encoding (encoding): Is the data encoded appropriately for the  type?
- aesthetics (aesthetics): Are the aesthetics of the appropriate for the type and the data?

YOU MUST PROVIDE A SCORE for each of the above dimensions.
{bugs: 0, transformation: 0, compliance: 0, type: 0, encoding: 0, aesthetics: 0}
Do not suggest code.
Finally, based on the critique above, suggest a concrete list of actions that the coder should take to improve the code.
""",
    llm_config=llm_config,
)



# Custom Pydantic model to handle query results
class KustoQueryResult(BaseModel):
    data: List[dict]  # You can customize this to fit the exact structure of your query response

# @user_proxy.register_for_execution()
# @coder.register_for_llm(description="Kusto Query code creator")

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

# user_proxy.register_for_execution()(run_kusto_query)
# coder.register_for_llm(
#     name="run_kusto_query",
#     description="This function generates the code to run a Kusto Query Language (KQL) query using Azure Resource Graph.",
# )(run_kusto_query)

# Register the function to the two agents.
register_function(
    run_kusto_query,
    caller=coder,  # The assistant agent can suggest calls to the kusto_query.
    executor=user_proxy,  # The user proxy agent can execute the kusto_query calls.
    name="run_kusto_query",  # By default, the function name is used as the tool name.
    description="This function generates the code to run a Kusto Query Language (KQL) query using Azure Resource Graph.",
)



# @user_proxy.register_for_execution()
# @coder.register_for_llm(description="save results to csv")
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

speaker_list = ["Planner", "Code_Guru", "Critic", "User_Proxy"]

groupchat = autogen.GroupChat(
            agents=[planner, coder, critic, user_proxy ], 
            messages=[],  # Start with no messages
            max_round=40,
            speaker_selection_method="round_robin",
            select_speaker_prompt_template="Please select the next speaker from the list: {speaker_list}",
        )

# Register the function to the two agents.,

register_function(
    save_results_to_csv,
    caller=coder,  # The assistant agent can suggest calls to the kusto_query.
    executor=user_proxy,  # The user proxy agent can execute the kusto_query calls.
    name="save_results_to_csv",  # By default, the function name is used as the tool name.
    description="A tool to save results to csv",  # A description of the tool.
)


manager = autogen.GroupChatManager(groupchat=groupchat, llm_config=llm_config)

# Initiate a chat between the user_proxy and the assistant
user_proxy.initiate_chat(
            manager,
            message=prompt,
            summary_method="reflection_with_llm"

        )