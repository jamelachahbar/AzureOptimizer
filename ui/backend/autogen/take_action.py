import logging
from auto_gen_assistant import AutoGenAssistant
from auto_gen_group import AutoGenGroup
from kusto_utils import run_kusto_query  # Import the function from the separate module


# // create a template for prompts text
prompt1 = """
Given the following Azure Cost Recommendation:
PROBLEM: {problem}
SOLUTION: {solution}
RESOURCE_ID: {resource_id}
Analyze and provide the best advice possible.
"""

prompt2 = """
Given the following Azure Cost Recommendation:
PROBLEM: {problem}
SOLUTION: {solution}
RESOURCE_ID: {resource_id}
Analyze and provide the best advice possible.
Analyze the environment first and output a summary of the environment (output of important resource information from Azure). Also provide the actual cost of the resources in the environment.
The final output should be a summary of the environment, the cost of the resources and the best advice possible. If you don't get the cost, make an estimate based on retail price, the resource properties from Azure and give the annual potential saving amount if the problem is fixed. Do not fix the issue.
"""

prompt3 = """
Given the following Azure Cost Recommendation:
PROBLEM: {problem}
SOLUTION: {solution}
RESOURCE_ID: {resource_id}
Analyze and provide the best advice possible.
Run kusto query using the Coder's function and output a summary of the environment (output of important resource information from Azure). 
The final output should be a summary of the environment, formatted as a table with the cost of the resources and the best advice possible. .
"""

# This is for now the best prompt to use
prompt4 = """
Given the following Azure Cost Recommendation:
PROBLEM: {problem}
SOLUTION: {solution}
RESOURCE_ID: {resource_id}
1.Analyze the issue and fix it, but don't delete anything in the environment.
2.Also provide the actual cost of the resources in the environment by using Azure cost management SDK -> from azure.mgmt.costmanagement import CostManagementClient and query the cost of the resource using the info from {resource_id}.
3.The final output should be a summary of the environment, the cost of the resources and the best advice possible. It should be clear what the end user needs to do. Save the output to a file called summary_output.csv, and data needs to be
written and saved in the file. Check if there is a file called summary_output.csv in the current directory. If it exists, read the file and display the content.
I also need to know the conclusion and best advice possible,so I can take action.
"""
INTRO_PROMPT = prompt1

# logging.basicConfig(level=logging.DEBUG)
def generate_code(problem, solution, resource_id):
    # Replace the placeholders in the prompt with the actual values
    formatted_prompt = INTRO_PROMPT.format(
        problem=problem,
        solution=solution,
        resource_id=resource_id
    )

    assistant = AutoGenGroup()
    assistant.initiate_chat(formatted_prompt)
    
    
    print("Done")
    

# Example usage:
# problem = "The Azure SQL Database 'MyDB' is not accessible due to a firewall rule misconfiguration"
# solution = "Add a new firewall rule to allow access from the application server's IP address"
# resource_id = "/subscriptions/12345678-1234-1234-1234-123456789012/resourceGroups/MyRG/providers/Microsoft.Sql/servers/myserver/databases/MyDB"
# 
problem = "You have disks that are not attached to a VM . Please evaluate if you still need the disk."
solution = "You have disks that are not attached to a VM . Please evaluate if you still need the disk."
resource_id = "/subscriptions/e9b4640d-1f1f-45fe-a543-c0ea45ac34c1/resourceGroups/rg-mgmt/providers/Microsoft.Compute/disks/unattacheddisk-1"  # "/subscriptions/e9b4640d-1f1f-45fe-a543-c0ea45ac34c1/resourcegroups/rg-tubdemos/providers/microsoft.compute/disks/premiumv2disk01"
generate_code(problem, solution, resource_id)
logging.info("Done")