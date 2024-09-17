import logging
from auto_gen_assistant import AutoGenAssistant
import os
import json

INTRO_PROMPT = """
You are an Azure expert.  You have received the following information:
PROBLEM: {problem}
SOLUTION: {solution}
RESOURCE_ID: {resource_id}
Your task is to generate to fix the issue. At the end check if the issue has been resolved and do a quality check if the resource is still in the environment.

"""

def generate_code(problem, solution, resource_id):
    # Replace the placeholders in the prompt with the actual values
    formatted_prompt = INTRO_PROMPT.format(
        problem=problem,
        solution=solution,
        resource_id=resource_id
    )

    assistant = AutoGenAssistant()
    assistant.initiate_chat(formatted_prompt)
    print("Done")
    

# Example usage:
# problem = "The Azure SQL Database 'MyDB' is not accessible due to a firewall rule misconfiguration"
# solution = "Add a new firewall rule to allow access from the application server's IP address"
# resource_id = "/subscriptions/12345678-1234-1234-1234-123456789012/resourceGroups/MyRG/providers/Microsoft.Sql/servers/myserver/databases/MyDB"
# 
problem = "You have disks that are not attached to a VM . Please evaluate if you still need the disk."
solution = "You have disks that are not attached to a VM . Please evaluate if you still need the disk."
resource_id = "/subscriptions/e9b4640d-1f1f-45fe-a543-c0ea45ac34c1/resourcegroups/rg-tubdemos/providers/microsoft.compute/disks/premiumv2disk01"
generate_code(problem, solution, resource_id)