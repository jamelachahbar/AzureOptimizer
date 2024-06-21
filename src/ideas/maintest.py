import argparse
import logging
import os
from datetime import datetime, timedelta
import json
import yaml
import jsonschema
from applicationinsights import TelemetryClient
from azure.identity import DefaultAzureCredential
from azure.mgmt.resource import ResourceManagementClient
from azure.mgmt.costmanagement import CostManagementClient
from azure.mgmt.compute import ComputeManagementClient
from azure.mgmt.storage import StorageManagementClient
from azure.mgmt.network import NetworkManagementClient
from azure.mgmt.sql import SqlManagementClient
import pandas as pd
import matplotlib.pyplot as plt
from dotenv import load_dotenv
from prettytable import PrettyTable
from termcolor import colored
from sklearn.ensemble import IsolationForest
import textwrap
from sql_scalingtest import scale_sql_database

# Load environment variables from .env file
load_dotenv()

# Load configuration from config.yaml
config_file = os.getenv('CONFIG_FILE', 'configs/config.yaml')
with open(config_file, 'r') as file:
    config = yaml.safe_load(file)

# Initialize Application Insights Telemetry Client
instrumentation_key = os.getenv('APPINSIGHTS_INSTRUMENTATIONKEY', config['app_insights']['instrumentation_key'])
tc = TelemetryClient(instrumentation_key)

# Authentication
credential = DefaultAzureCredential()
subscription_id = os.getenv('AZURE_SUBSCRIPTION_ID')

# Clients
resource_client = ResourceManagementClient(credential, subscription_id)
cost_management_client = CostManagementClient(credential)
compute_client = ComputeManagementClient(credential, subscription_id)
storage_client = StorageManagementClient(credential, subscription_id)
network_client = NetworkManagementClient(credential, subscription_id)
sql_client = SqlManagementClient(credential, subscription_id)

def load_policies(policy_file, schema_file):
    """Load and validate policies from the YAML file against the schema."""
    with open(policy_file, 'r') as file:
        policies = yaml.safe_load(file)
    
    with open(schema_file, 'r') as file:
        schema = json.load(file)
    
    jsonschema.validate(instance=policies, schema=schema)
    return policies['policies']

def get_cost_data(scope):
    """Retrieve cost data from Azure."""
    try:
        logging.info(f"Retrieving cost data for scope: {scope}")
        cost_data = cost_management_client.query.usage(
            scope,
            {
                "type": "Usage",
                "timeframe": "MonthToDate",
                "dataset": {
                    "granularity": "Daily",
                    "aggregation": {
                        "totalCost": {
                            "name": "PreTaxCost",
                            "function": "Sum"
                        }
                    }
                }
            }
        )
        return cost_data
    except Exception as e:
        logging.error(f"Failed to retrieve cost data for scope {scope}: {e}")
        return None

def filter_cost_data(cost_data, resource_id):
    """Filter the cost data to match the specific resource ID."""
    filtered_data = []
    for item in cost_data.rows:
        if resource_id in item:
            filtered_data.append(item)
    return filtered_data

def analyze_cost_data(cost_data):
    """Analyze cost data, detect trends, anomalies, and generate reports."""
    data = []
    for item in cost_data.rows:
        try:
            date_str = str(item[1])
            date = pd.to_datetime(date_str, format='%Y%m%d')
            data.append({'date': date, 'cost': item[0]})
        except Exception as e:
            logging.error(f"Error parsing date: {e}, Item: {item}")

    df = pd.DataFrame(data)
    df['date'] = pd.to_datetime(df['date'])
    df.set_index('date', inplace=True)
    df = df.asfreq('D')  # Set frequency to daily

    # Log daily costs
    for _, row in df.iterrows():
        logging.info(f"Date: {row.name.date()}, Cost: {row['cost']}")
        tc.track_metric("DailyCost", row['cost'], properties={"Date": row.name.date().isoformat()})
    
    # Generate trend analysis
    trend_analysis(df)
    
    # Detect anomalies using basic statistical methods
    detect_anomalies_statistical(df)
    
    # Detect anomalies using Isolation Forest
    detect_anomalies_isolation_forest(df)
    
    # Generate cost summary report
    generate_summary_report(df)

def trend_analysis(df):
    """Analyze cost trends over time and plot the trend."""
    df['cost'].plot(title='Cost Trend Over Time', figsize=(10, 5))
    plt.xlabel('Date')
    plt.ylabel('Cost')
    plt.savefig('cost_trend.png')
    plt.close()
    logging.info("Trend analysis plot saved as cost_trend.png.")
    tc.track_event("TrendAnalysisCompleted")

def detect_anomalies_statistical(df):
    """Detect anomalies in the cost data using statistical methods."""
    mean = df['cost'].mean()
    std = df['cost'].std()
    
    # Define anomalies as costs that are more than 2 standard deviations away from the mean
    anomalies = df[(df['cost'] > mean + 2 * std) | (df['cost'] < mean - 2 * std)]
    
    if not anomalies.empty:
        logging.warning("Anomalies detected in cost data.")
        for _, row in anomalies.iterrows():
            logging.warning(f"Anomaly detected on {row.name.date()}: Cost = {row['cost']}")
            tc.track_event("AnomalyDetectedStatistical", {"Date": row.name.date().isoformat(), "Cost": row['cost']})
    else:
        logging.info("No anomalies detected in cost data.")
        tc.track_event("NoAnomaliesDetectedStatistical")

def detect_anomalies_isolation_forest(df):
    """Detect anomalies in the cost data using Isolation Forest."""
    model = IsolationForest(contamination=0.05)
    df['anomaly'] = model.fit_predict(df[['cost']])
    anomalies = df[df['anomaly'] == -1]
    
    if not anomalies.empty:
        logging.warning("Anomalies detected in cost data using Isolation Forest.")
        for _, row in anomalies.iterrows():
            logging.warning(f"Anomaly detected on {row.name.date()}: Cost = {row['cost']}")
            tc.track_event("AnomalyDetectedIsolationForest", {"Date": row.name.date().isoformat(), "Cost": row['cost']})
    else:
        logging.info("No anomalies detected in cost data using Isolation Forest.")
        tc.track_event("NoAnomaliesDetectedIsolationForest")

def generate_summary_report(df):
    """Generate a summary report of the cost data."""
    total_cost = df['cost'].sum()
    avg_cost = df['cost'].mean()
    max_cost = df['cost'].max()
    min_cost = df['cost'].min()
    
    logging.info(f"Total Cost: {total_cost}")
    logging.info(f"Average Daily Cost: {avg_cost}")
    logging.info(f"Maximum Daily Cost: {max_cost}")
    logging.info(f"Minimum Daily Cost: {min_cost}")
    
    summary = {
        "TotalCost": total_cost,
        "AverageDailyCost": avg_cost,
        "MaximumDailyCost": max_cost,
        "MinimumDailyCost": min_cost
    }
    tc.track_event("SummaryReportGenerated", summary)
    tc.track_metric("TotalCost", total_cost)
    tc.track_metric("AverageDailyCost", avg_cost)
    tc.track_metric("MaximumDailyCost", max_cost)
    tc.track_metric("MinimumDailyCost", min_cost)

def evaluate_filters(resource, filters):
    """Evaluate if a resource meets the defined filters."""
    for filter in filters:
        filter_type = filter['type']
        if filter_type == 'last_used':
            if not last_used_filter(resource, filter['days']):
                return False
        elif filter_type == 'unattached':
            if not unattached_filter(resource):
                return False
        elif filter_type == 'tag':
            if not tag_filter(resource, filter['key'], filter['value']):
                return False
        elif filter_type == 'sku':
            if not sku_filter(resource, filter['values']):
                return False
    return True

def evaluate_exclusions(resource, exclusions):
    """Evaluate if a resource meets any of the exclusion criteria."""
    for exclusion in exclusions:
        exclusion_type = exclusion['type']
        if exclusion_type == 'tag':
            if tag_filter(resource, exclusion['key'], exclusion['value']):
                return True
    return False

def last_used_filter(resource, days):
    """Check if a resource was last used within a specified number of days."""
    last_used_date = get_last_used_date(resource)
    return (datetime.now() - last_used_date).days <= days

def unattached_filter(resource):
    """Check if a resource is unattached."""
    logging.info(f"Checking if resource {resource.name} is unattached.")
    if isinstance(resource, network_client.public_ip_addresses.models.PublicIPAddress):
        return resource.ip_configuration is None
    return resource.managed_by is None

def tag_filter(resource, key, value):
    """Check if a resource has a specific tag."""
    tags = resource.tags
    return tags and tags.get(key) == value

def sku_filter(resource, values):
    """Check if a resource's SKU is in the specified values."""
    return resource.sku.name in values

def get_last_used_date(resource):
    """Get the last used date of a VM. Placeholder logic."""
    # Implement actual logic to get the last used date
    return datetime.now() - timedelta(days=10)

def apply_actions(resource, actions, status_log, dry_run):
    """Apply actions to a resource."""
    for action in actions:
        action_type = action['type']
        if dry_run:
            status_log.append({'Resource': resource.name, 'Action': action_type, 'Status': 'Dry Run', 'Message': 'Dry run mode, no action taken'})
        else:
            if action_type == 'stop':
                status, message = stop_vm(resource)
                status_log.append({'Resource': resource.name, 'Action': 'stop', 'Status': status, 'Message': message})
            elif action_type == 'delete':
                if isinstance(resource, compute_client.disks.models.Disk):
                    status, message = delete_disk(resource)
                    status_log.append({'Resource': resource.name, 'Action': 'delete', 'Status': status, 'Message': message})
                elif isinstance(resource, resource_client.resource_groups.models.ResourceGroup):
                    status, message = delete_resource_group(resource)
                    status_log.append({'Resource': resource.name, 'Action': 'delete', 'Status': status, 'Message': message})
                elif isinstance(resource, network_client.public_ip_addresses.models.PublicIPAddress):
                    status, message = delete_public_ip(resource)
                    status_log.append({'Resource': resource.name, 'Action': 'delete', 'Status': status, 'Message': message})
            elif action_type == 'update_sku':
                if isinstance(resource, storage_client.storage_accounts.models.StorageAccount):
                    status, message = update_storage_account_sku(resource, action['sku'])
                    status_log.append({'Resource': resource.name, 'Action': 'update_sku', 'Status': status, 'Message': message})
            elif action_type == 'scale_sql_database':
                status, message = scale_sql_database(sql_client, resource, action['tiers'], dry_run, tc)
                status_log.append({'Resource': resource.name, 'Action': 'scale_sql_database', 'Status': status, 'Message': message})

def stop_vm(vm):
    """Stop a VM."""
    try:
        logging.info(f"Stopping VM: {vm.name}")
        compute_client.virtual_machines.begin_deallocate(vm.resource_group_name, vm.name)
        tc.track_event("VMStopped", {"VMName": vm.name})
        return 'Success', 'VM stopped successfully.'
    except Exception as e:
        logging.error(f"Failed to stop VM {vm.name}: {e}")
        tc.track_event("VMStopFailed", {"VMName": vm.name, "Error": str(e)})
        return 'Failed', f"Failed to stop VM: {e}"

def delete_disk(disk):
    """Delete a disk."""
    try:
        logging.info(f"Attempting to delete disk: {disk.name}")
        resource_group_name = disk.id.split('/')[4]  # Extract the resource group name from the disk ID
        logging.info(f"Disk resource group: {resource_group_name}")
        logging.info(f"Disk details: {disk}")
        compute_client.disks.begin_delete(resource_group_name, disk.name)
        tc.track_event("DiskDeleted", {"DiskName": disk.name})
        return 'Success', 'Disk deleted successfully.'
    except Exception as e:
        logging.error(f"Failed to delete Disk {disk.name}: {e}")
        tc.track_event("DiskDeletionFailed", {"DiskName": disk.name, "Error": str(e)})
        return 'Failed', f"Failed to delete disk: {e}"

def delete_resource_group(resource_group):
    """Delete all resources in a resource group."""
    try:
        logging.info(f"Deleting Resource Group: {resource_group.name}")
        resource_client.resource_groups.begin_delete(resource_group.name)
        tc.track_event("ResourceGroupDeleted", {"ResourceGroupName": resource_group.name})
        return 'Success', 'Resource group deleted successfully.'
    except Exception as e:
        logging.error(f"Failed to delete Resource Group {resource_group.name}: {e}")
        tc.track_event("ResourceGroupDeletionFailed", {"ResourceGroupName": resource_group.name, "Error": str(e)})
        return 'Failed', f"Failed to delete resource group: {e}"

def delete_public_ip(public_ip):
    """Delete a public IP address."""
    try:
        logging.info(f"Deleting Public IP: {public_ip.name}")
        resource_group_name = public_ip.id.split('/')[4]  # Extract the resource group name from the public IP ID
        logging.info(f"Public IP resource group: {resource_group_name}")
        logging.info(f"Public IP details: {public_ip}")
        network_client.public_ip_addresses.begin_delete(resource_group_name, public_ip.name)
        tc.track_event("PublicIPDeleted", {"PublicIPName": public_ip.name})
        return 'Success', 'Public IP deleted successfully.'
    except Exception as e:
        logging.error(f"Failed to delete Public IP {public_ip.name}: {e}")
        tc.track_event("PublicIPDeletionFailed", {"PublicIPName": public_ip.name, "Error": str(e)})
        return 'Failed', f"Failed to delete Public IP: {e}"

def update_storage_account_sku(storage_account, new_sku):
    """Update the SKU of a storage account."""
    try:
        logging.info(f"Updating storage account SKU: {storage_account.name}")
        storage_client.storage_accounts.update(
            resource_group_name=storage_account.id.split('/')[4],  # Extract resource group from the ID
            account_name=storage_account.name,
            parameters={
                'sku': {'name': new_sku}
            }
        )
        tc.track_event("StorageAccountSkuUpdated", {"StorageAccountName": storage_account.name, "NewSku": new_sku})
        return 'Success', f'Storage account SKU updated to {new_sku}.'
    except Exception as e:
        logging.error(f"Failed to update storage account SKU {storage_account.name}: {e}")
        tc.track_event("StorageAccountSkuUpdateFailed", {"StorageAccountName": storage_account.name, "Error": str(e)})
        return 'Failed', f'Failed to update storage account SKU: {e}'

def wrap_text(text, width=30):
    """Wrap text to a given width."""
    return "\n".join(textwrap.wrap(text, width))

def apply_policies(policies, dry_run):
    """Apply policies to resources."""
    impacted_resources = []  # List to store impacted resources for logging
    status_log = []  # List to store status of each operation

    for policy in policies:
        resource_type = policy['resource']
        filters = policy['filters']
        actions = policy['actions']
        exclusions = policy.get('exclusions', [])

        resources_impacted = False  # Flag to check if any resources are impacted by the policy

        if resource_type == 'azure.vm':
            vms = compute_client.virtual_machines.list_all()
            for vm in vms:
                if not evaluate_exclusions(vm, exclusions) and evaluate_filters(vm, filters):
                    apply_actions(vm, actions, status_log, dry_run)
                    impacted_resources.append({'Policy': policy['name'], 'Resource': vm.name, 'Actions': ', '.join([action['type'] for action in actions])})
                    resources_impacted = True
            if not resources_impacted:
                logging.info(f"No VMs impacted by policy: {policy['name']}")
                print(colored(f"No VMs impacted by policy: {policy['name']}", "yellow"))

        elif resource_type == 'azure.disk':
            disks = compute_client.disks.list()
            for disk in disks:
                logging.info(f"Evaluating disk {disk.name} for deletion.")
                if not evaluate_exclusions(disk, exclusions) and evaluate_filters(disk, filters):
                    apply_actions(disk, actions, status_log, dry_run)
                    impacted_resources.append({'Policy': policy['name'], 'Resource': disk.name, 'Actions': ', '.join([action['type'] for action in actions])})
                    resources_impacted = True
            if not resources_impacted:
                logging.info(f"No disks impacted by policy: {policy['name']}")
                print(colored(f"No disks impacted by policy: {policy['name']}", "yellow"))

        elif resource_type == 'azure.resourcegroup':
            resource_groups = resource_client.resource_groups.list()
            for resource_group in resource_groups:
                if not evaluate_exclusions(resource_group, exclusions) and evaluate_filters(resource_group, filters):
                    apply_actions(resource_group, actions, status_log, dry_run)
                    impacted_resources.append({'Policy': policy['name'], 'Resource': resource_group.name, 'Actions': ', '.join([action['type'] for action in actions])})
                    resources_impacted = True
            if not resources_impacted:
                logging.info(f"No resource groups impacted by policy: {policy['name']}")
                print(colored(f"No resource groups impacted by policy: {policy['name']}", "yellow"))

        elif resource_type == 'azure.storage':
            storage_accounts = storage_client.storage_accounts.list()
            for storage_account in storage_accounts:
                if not evaluate_exclusions(storage_account, exclusions) and evaluate_filters(storage_account, filters):
                    apply_actions(storage_account, actions, status_log, dry_run)
                    impacted_resources.append({'Policy': policy['name'], 'Resource': storage_account.name, 'Actions': ', '.join([action['type'] for action in actions])})
                    resources_impacted = True
            if not resources_impacted:
                logging.info(f"No storage accounts impacted by policy: {policy['name']}")
                print(colored(f"No storage accounts impacted by policy: {policy['name']}", "yellow"))

        elif resource_type == 'azure.publicip':
            public_ips = network_client.public_ip_addresses.list_all()
            for public_ip in public_ips:
                if not evaluate_exclusions(public_ip, exclusions) and evaluate_filters(public_ip, filters):
                    apply_actions(public_ip, actions, status_log, dry_run)
                    impacted_resources.append({'Policy': policy['name'], 'Resource': public_ip.name, 'Actions': ', '.join([action['type'] for action in actions])})
                    resources_impacted = True
            if not resources_impacted:
                logging.info(f"No public IPs impacted by policy: {policy['name']}")
                print(colored(f"No public IPs impacted by policy: {policy['name']}", "yellow"))

        elif resource_type == 'azure.sql':
            # Get all SQL servers and databases
            servers = sql_client.servers.list()
            for server in servers:
                databases = sql_client.databases.list_by_server(server.id.split('/')[4], server.name)

                for database in databases:
                    if not evaluate_exclusions(database, exclusions) and evaluate_filters(database, filters):
                        apply_actions(database, actions, status_log, dry_run)
                        impacted_resources.append({'Policy': policy['name'], 'Resource': database.name, 'Actions': ', '.join([action['type'] for action in actions])})
                        resources_impacted = True
                # Check if the server itself needs to be scaled
                # if not evaluate_exclusions(server, exclusions) and evaluate_filters(server, filters):
                #     apply_actions(server, actions, status_log, dry_run)
                #     impacted_resources.append({'Policy': policy['name'], 'Resource': server.name, 'Actions': ', '.join([action['type'] for action in actions])})
                #     resources_impacted = True
                if not resources_impacted:
                    logging.info(f"No SQL databases impacted by policy: {policy['name']}")
                    print(colored(f"No SQL databases impacted by policy: {policy['name']}", "yellow"))

    # Log impacted resources
    if impacted_resources:
        table = PrettyTable()
        table.field_names = ["Policy", "Resource", "Actions"]
        for resource in impacted_resources:
            wrapped_policy = wrap_text(resource['Policy'])
            wrapped_resource = wrap_text(resource['Resource'])
            wrapped_actions = wrap_text(resource['Actions'])
            table.add_row([wrapped_policy, wrapped_resource, wrapped_actions])
        print(colored("Impacted Resources:", "cyan", attrs=["bold"]))
        print(colored(table.get_string(), "cyan"))
        tc.track_event("ImpactedResources", {"Resources": impacted_resources})
    else:
        logging.info("No resources impacted by policies.")
        print(colored("No resources impacted by policies.", "green"))
    
    # Log status of operations
    if status_log:
        table_status = PrettyTable()
        table_status.field_names = ["Resource", "Action", "Status", "Message"]
        for log in status_log:
            wrapped_resource = wrap_text(log['Resource'])
            wrapped_action = wrap_text(log['Action'])
            wrapped_message = wrap_text(log['Message'])
            color = "green" if log['Status'] == "Success" else "red"
            table_status.add_row([wrapped_resource, wrapped_action, colored(log['Status'], color), wrapped_message])
        print(colored("Operation Status:", "cyan", attrs=["bold"]))
        print(colored(table_status.get_string(), "cyan"))
        tc.track_event("OperationStatus", {"Status": status_log})
    else:
        logging.info("No operations performed.")
        print(colored("No operations performed.", "yellow"))

def main(mode):
    """Main function to execute cost optimization."""
    logging.info('Cost Optimizer Function triggered.')
    tc.track_event("FunctionTriggered")

    try:
        policy_file = config['policies']['policy_file']
        schema_file = config['policies']['schema_file']
        policies = load_policies(policy_file, schema_file)
        cost_data = get_cost_data(f'/subscriptions/{subscription_id}')
        if cost_data:
            analyze_cost_data(cost_data)
        apply_policies(policies, mode == 'dry-run' if mode == 'dry-run' else False)
        tc.flush()
    except Exception as e:
        logging.error(f"Error: {e}")
        tc.track_exception()
        tc.flush()

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Azure Cost Optimization Tool")
    parser.add_argument('--mode', choices=['dry-run', 'apply'], required=True, help="Mode to run the function (dry-run or apply)")
    args = parser.parse_args()
    main(args.mode)
