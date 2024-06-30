from azure.identity import DefaultAzureCredential
from azure.mgmt.consumption import ConsumptionManagementClient

# Ensure you have the correct subscription ID
subscription_id = "38c26c07-ccce-4839-b504-cddac8e5b09d"
credential = DefaultAzureCredential()

# Initialize the ConsumptionManagementClient with your credential and subscription ID
consumption_client = ConsumptionManagementClient(credential, subscription_id)
from collections import defaultdict

# Initialize dictionaries to hold costs
resource_group_costs = defaultdict(float)
resource_costs = defaultdict(float)

def print_resource_costs():
    scope = f"/subscriptions/{subscription_id}"
    try:
        usage_details = consumption_client.usage_details.list(scope)
        
        for detail in usage_details:
            # Assuming 'instance_name' or 'id' contains the resource group and resource name
            # You might need to adjust the parsing logic based on your actual data structure
            resource_group_name = detail.instance_name.split('/')[4]  # Adjust based on actual structure
            resource_name = detail.instance_name.split('/')[-1]  # Adjust based on actual structure
            cost = detail.cost_in_usd  # Adjust attribute name if necessary
            
            # Sum costs by resource group and resource
            resource_group_costs[resource_group_name] += cost
            resource_costs[resource_name] += cost

    except Exception as e:
        print(f"An error occurred: {e}")

    # Print total cost per resource group
    for rg, cost in resource_group_costs.items():
        print(f"Resource Group: {rg}, Total Cost: {cost}")

    # Print total cost per resource
    for resource, cost in resource_costs.items():
        print(f"Resource: {resource}, Total Cost: {cost}")

# Call the function to print costs
print_resource_costs()