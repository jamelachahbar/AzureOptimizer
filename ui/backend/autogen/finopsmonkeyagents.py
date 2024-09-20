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
    the resuls in a table format and save the results to a csv file. 
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
    have been provided with. Reply TERMINATE when the task is done.""", 
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
def run_kusto_query(query: str, subscriptions: List[str]) -> KustoQueryResult:
    """
    Executes a Kusto Query Language (KQL) query using Azure Resource Graph.

    Args:
        query (str): The KQL query to run.
        subscriptions (list): List of subscription IDs to query.

    Returns:
        KustoQueryResult: The response from Azure Resource Graph.
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

    # Return the query result data wrapped in a Pydantic model
    return KustoQueryResult(data=query_response.data)






groupchat = autogen.GroupChat(
            agents=[planner, coder, user_proxy], 
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