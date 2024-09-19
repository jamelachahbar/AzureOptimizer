import logging
from auto_gen_assistant import AutoGenAssistant
from auto_gen_group import AutoGenGroup


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
The final output should be a summary of the environment, the cost of the resources and the best advice possible. If you don't get the cost, make an estimate based on retail price, the resource properties from Azure and give the annual potential saving amount if the problem is fixed.
"""
prompt3 = """
Given the following Azure Cost Recommendation:
PROBLEM: {problem}
SOLUTION: {solution}
RESOURCE_ID: {resource_id}
Analyze the issue and fix it, but don't delete anything in the environment. Check if fix is implemented.
Also provide the actual cost of the resources in the environment.
The final output should be a summary of the environment, the cost of the resources and the best advice possible.
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
resource_id = "/subscriptions/e9b4640d-1f1f-45fe-a543-c0ea45ac34c1/resourceGroups/AOETESTRESOURCES/providers/Microsoft.Compute/disks/myVM0_OsDisk_1_3b125947f0494013b4f6ed1897127f3f"  # "/subscriptions/e9b4640d-1f1f-45fe-a543-c0ea45ac34c1/resourcegroups/rg-tubdemos/providers/microsoft.compute/disks/premiumv2disk01"
generate_code(problem, solution, resource_id)
logging.info("Done")