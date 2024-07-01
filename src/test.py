from azure.identity import DefaultAzureCredential
from azure.mgmt.consumption import ConsumptionManagementClient
from collections import defaultdict
from datetime import datetime, timedelta
import pandas as pd

# Ensure you have the correct subscription ID
subscription_id = "38c26c07-ccce-4839-b504-cddac8e5b09d"
credential = DefaultAzureCredential()

# Initialize the ConsumptionManagementClient with your credential and subscription ID
consumption_client = ConsumptionManagementClient(credential, subscription_id)

# Initialize dictionaries to hold costs
resource_costs = defaultdict(float)
usage_details_list = []

# Function to get cost details for all resources of the last 30 days
def get_cost_details():
    scope = f"/subscriptions/{subscription_id}"
    end_date = datetime.now()
    start_date = end_date - timedelta(days=15)
    
    try:
        usage_details_pager = consumption_client.usage_details.list(
            scope,
            expand="properties/additionalInfo",
            filter=f"properties/usageStart ge '{start_date.strftime('%Y-%m-%d')}' and properties/usageEnd le '{end_date.strftime('%Y-%m-%d')}'"
        )
        
        for usage_detail in usage_details_pager:
            # Access properties - adjust based on actual structure
            try:
                resource_name = usage_detail.instance_name   # Adjust based on actual structure
                cost = float(usage_detail.cost_in_usd)  # Adjust attribute name if necessary
                usage_start = usage_detail.service_period_start_date  # Adjust attribute name if necessary
                
                # Sum costs by resource
                resource_costs[resource_name] += cost
                
                # Collecting data for DataFrame
                usage_details_list.append({
                    'Resource': resource_name,
                    'Cost': cost,
                    'Date': usage_start
                })
            except Exception as e:
                print(f"Error processing usage detail: {e}")

    except Exception as e:
        print(f"An error occurred: {e}")

# Function to print total costs per resource
def display_resource_costs():
    get_cost_details()
    
    # Create DataFrame from collected data
    df = pd.DataFrame(usage_details_list)
    
    if df.empty:
        print("No data available for the specified period.")
        return
    
    # Aggregating the cost per resource over the period
    aggregated_df = df.groupby('Resource').agg({'Cost': 'sum'}).reset_index()
    
    # Display DataFrame
    print("Aggregated Cost per Resource:")
    print(aggregated_df)

    # Optionally, save the aggregated DataFrame to a CSV file
    aggregated_df.to_csv('aggregated_azure_usage_details.csv', index=False)
    print("The aggregated breakdown has been saved to 'aggregated_azure_usage_details.csv'.")

# Call the function to display costs
display_resource_costs()
