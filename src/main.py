import argparse
import logging
import os
import sys
import time
from datetime import datetime, timedelta, timezone
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
from azure.mgmt.sql.models import Sku, Database
from azure.mgmt.subscription import SubscriptionClient
from azure.mgmt.consumption import ConsumptionManagementClient
import pandas as pd
import matplotlib.pyplot as plt
from dotenv import load_dotenv
from prettytable import PrettyTable
from termcolor import colored
from sklearn.ensemble import IsolationForest
import textwrap
from collections import defaultdict
import pytz

# Set FORCE_COLOR to 1 to ensure color output
os.environ['FORCE_COLOR'] = '1'
# Check if environment variables are already set, if not, load from .env file
if not os.getenv('AZURE_CLIENT_ID'):
    load_dotenv()

# Load configuration from config.yaml
config_file = os.getenv('CONFIG_FILE', 'configs/config.yaml')
if not config_file:
    raise Exception("CONFIG_FILE environment variable not set.")
with open(config_file, 'r') as file:
    config = yaml.safe_load(file)

# Initialize Application Insights Telemetry Client
instrumentation_key = os.getenv('APPINSIGHTS_INSTRUMENTATIONKEY')
if not instrumentation_key:
    raise Exception("Instrumentation key was required but not provided")
tc = TelemetryClient(instrumentation_key)

# Authentication
credential = DefaultAzureCredential()

# Verify that the necessary environment variables are set
required_env_vars = ['AZURE_CLIENT_ID', 'AZURE_TENANT_ID', 'AZURE_CLIENT_SECRET', 'AZURE_SUBSCRIPTION_ID']
for var in required_env_vars:
    if not os.getenv(var):
        logging.error(f"Environment variable {var} is not set.")
        sys.exit(1)

# Clients
subscription_client = SubscriptionClient(credential)  # Added SubscriptionClient

def simple_scale_sql_database(sql_client, database, new_dtu, min_dtu, max_dtu, dry_run=True):
    """Simple function to scale a SQL database DTU without any conditions."""
    try:
        current_sku = database.sku
        logging.info(f"Database: {database.name}, Current DTU: {current_sku.capacity}")
        print(f"Database: {database.name}, Current DTU: {current_sku.capacity}")

        if new_dtu == current_sku.capacity:
            logging.info("Current DTU is already optimal.")
            return 'No Change', 'Current DTU is already optimal.'
        
        if new_dtu < min_dtu:
            new_dtu = min_dtu
        elif new_dtu > max_dtu:
            new_dtu = max_dtu

        resource_group_name = database.id.split('/')[4]
        server_name = database.id.split('/')[8]
        database_name = database.name
        logging.info(f"Scaling SQL database {database.name} to {new_dtu} DTU.")

        valid_dtus = {
            'Basic': [5],
            'Standard': [10, 20, 50, 100, 200, 400, 800, 1600, 3000],
            'Premium': [125, 250, 500, 1000, 1750, 4000]
        }
        if new_dtu not in valid_dtus[current_sku.tier]:
            logging.error(f"DTU {new_dtu} is not valid for tier {current_sku.tier}.")
            return 'Error', f'DTU {new_dtu} is not valid for tier {current_sku.tier}.'

        new_sku = Sku(name=current_sku.name, tier=current_sku.tier, capacity=new_dtu)
        update_parameters = Database(location=database.location, sku=new_sku, min_capacity=new_dtu)
        logging.info(f"Update parameters: {update_parameters}")

        if dry_run:
            logging.info("This is a dry run. No changes will be made.")
            return 'Dry Run', f'Would scale DTU to {new_dtu}.'
        else:
            sql_client.databases.begin_create_or_update(resource_group_name, server_name, database_name, update_parameters).result()
            while True:
                database = sql_client.databases.get(resource_group_name, server_name, database_name)
                if database.sku.capacity == new_dtu:
                    break
                else:
                    logging.info("Operation in progress...")
                    time.sleep(10)
            logging.info(f"Database {database.name} scaled to {new_dtu} DTU.")
            return 'Success', f'Scaled DTU to {new_dtu}.'
    except Exception as e:
        logging.error(f"Error scaling SQL database {database.name}: {str(e)}")
        return 'Error', str(e)

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
        time.sleep(15)  # Delay to avoid rate limiting
        # last 30 days of cost CET timezone using timedelta
        cet = pytz.timezone('CET')
        # Get the current date and time in CET
        now_cet = datetime.now(cet)

        # Define the start and end dates in CET
        start_date = (now_cet - timedelta(days=30)).isoformat()
        end_date = now_cet.isoformat()
        # start_date = (datetime.now() - timedelta(days=30)).isoformat()
        # end_date = datetime.now().isoformat()

        cost_data = cost_management_client.query.usage(

            scope,
            {
                "type": "Usage",
                "timeframe": "Custom",
                "timePeriod": {
                    "from": start_date,
                    "to": end_date
                },
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

def analyze_cost_data(cost_data, subscription_id, summary_reports):
    """Analyze cost data until yesterday, detect trends, anomalies, and generate reports."""
    data = []
    cet = pytz.timezone('CET')
    now_cet = datetime.now(cet)

    for item in cost_data.rows:
        try:
            date_str = str(item[1])  # Assuming the date is in the second position (adjust if necessary)
            # Convert the date string to a datetime object
            date = pd.to_datetime(date_str, format='%Y%m%d')
            date = date.tz_localize('UTC').tz_convert(cet)  # Convert to CET timezone

            if date.date() < now_cet.date():
                data.append({'date': date, 'cost': item[0]})
        except Exception as e:
            logging.error(f"Error parsing date: {e}, Item: {item}")

    df = pd.DataFrame(data)
    df['date'] = pd.to_datetime(df['date'])
    df.set_index('date', inplace=True)
    df = df.asfreq('D')

    for _, row in df.iterrows():
        logging.info(f"Date: {row.name.date()}, Cost: {row['cost']}")
        tc.track_metric("DailyCost", row['cost'], properties={"Date": row.name.date().isoformat()})
    
    trend_analysis(df, subscription_id)
    detect_anomalies_isolation_forest(df, subscription_id)
    generate_summary_report(df, subscription_id, summary_reports)

def trend_analysis(df, subscription_id):
    """Analyze cost trends over time and plot the trend."""
    df['cost'].plot(title=f'Cost Trend Over Time for Subscription {subscription_id}', figsize=(10, 5))
    plt.xlabel('Date')
    plt.ylabel('Cost')
    plt.savefig(f'cost_trend_{subscription_id}.png')
    plt.close()
    logging.info(f"Trend analysis plot saved as cost_trend_{subscription_id}.png.")
    tc.track_event("TrendAnalysisCompleted", {"SubscriptionId": subscription_id})

def detect_anomalies_isolation_forest(df, subscription_id):
    """Detect anomalies in the cost data using Isolation Forest."""
    model = IsolationForest(contamination=0.025)
    df['anomaly'] = model.fit_predict(df[['cost']])
    anomalies = df[df['anomaly'] == -1]
    
    if not anomalies.empty:
        for _, row in anomalies.iterrows():
            tc.track_event("AnomalyDetectedIsolationForest", {"SubscriptionId": subscription_id, "Date": row.name.date().isoformat(), "Cost": row['cost']})
            table = PrettyTable()
            table.field_names = ["Subscription ID", "Anomaly Detected", "Date", "Cost"]
            table.add_row([subscription_id, "Isolation Forest Algorithm", row.name.date().isoformat(), f"{row['cost']:.2f}"])
            print(colored(table, "red"))
    else:
        logging.info(f"No anomalies detected in cost data for subscription {subscription_id} using Isolation Forest.")
        tc.track_event("NoAnomaliesDetectedIsolationForest", {"SubscriptionId": subscription_id})

def generate_summary_report(df, subscription_id, summary_reports):
    """Generate a summary report of the cost data."""
    total_cost = df['cost'].sum()
    avg_cost = df['cost'].mean()
    max_cost = df['cost'].max()
    min_cost = df['cost'].min()
    
    logging.info(f"Total Cost for subscription {subscription_id}: {total_cost}")
    logging.info(f"Average Daily Cost for subscription {subscription_id}: {avg_cost}")
    logging.info(f"Maximum Daily Cost for subscription {subscription_id}: {max_cost}")
    logging.info(f"Minimum Daily Cost for subscription {subscription_id}: {min_cost}")
    
    summary_reports.append({
        "SubscriptionId": subscription_id,
        "TotalCost": total_cost,
        "AverageDailyCost": avg_cost,
        "MaximumDailyCost": max_cost,
        "MinimumDailyCost": min_cost
    })

    tc.track_event("SummaryReportGenerated", {"SubscriptionId": subscription_id, "TotalCost": total_cost, "AverageDailyCost": avg_cost, "MaximumDailyCost": max_cost, "MinimumDailyCost": min_cost})
    tc.track_metric("TotalCost", total_cost, properties={"SubscriptionId": subscription_id})
    tc.track_metric("AverageDailyCost", avg_cost, properties={"SubscriptionId": subscription_id})
    tc.track_metric("MaximumDailyCost", max_cost, properties={"SubscriptionId": subscription_id})
    tc.track_metric("MinimumDailyCost", min_cost, properties={"SubscriptionId": subscription_id})

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
        if resource.ip_configuration is None:
            # Check for associations with Load Balancers and NAT Gateways
            associated_lb = network_client.load_balancers.list_all()
            for lb in associated_lb:
                for frontend_ip in lb.frontend_ip_configurations:
                    if frontend_ip.public_ip_address and frontend_ip.public_ip_address.id == resource.id:
                        return False
            associated_nat_gateways = network_client.nat_gateways.list_all()
            for nat_gateway in associated_nat_gateways:
                for public_ip in nat_gateway.public_ip_addresses:
                    if public_ip.id == resource.id:
                        return False
            return True
        else:
            return False
    return resource.managed_by is None

def tag_filter(resource, key, value):
    """Check if a resource has a specific tag."""
    if not hasattr(resource, 'tags'):
        logging.error(f"Resource {resource} does not have tags attribute.")
        return False
    tags = resource.tags
    return tags and tags.get(key) == value

def sku_filter(resource, values):
    """Check if a resource's SKU is in the specified values."""
    return resource.sku.name in values

def get_last_used_date(resource):
    """Get the last used date of a VM. Placeholder logic."""
    return datetime.now() - timedelta(days=10)

def apply_actions(resource, actions, status_log, dry_run, subscription_id):
    """Apply actions to a resource."""
    for action in actions:
        action_type = action['type']
        if dry_run:
            status_log.append({'SubscriptionId': subscription_id, 'Resource': resource.name, 'Action': action_type, 'Status': 'Dry Run', 'Message': 'Dry run mode, no action taken'})
        else:
            if action_type == 'stop':
                status, message = stop_vm(resource)
                status_log.append({'SubscriptionId': subscription_id, 'Resource': resource.name, 'Action': 'stop', 'Status': status, 'Message': message})
            elif action_type == 'delete':
                if isinstance(resource, compute_client.disks.models.Disk):
                    status, message = delete_disk(resource)
                    status_log.append({'SubscriptionId': subscription_id, 'Resource': resource.name, 'Action': 'delete', 'Status': status, 'Message': message})
                elif isinstance(resource, resource_client.resource_groups.models.ResourceGroup):
                    status, message = delete_resource_group(resource)
                    status_log.append({'SubscriptionId': subscription_id, 'Resource': resource.name, 'Action': 'delete', 'Status': status, 'Message': message})
                elif isinstance(resource, network_client.public_ip_addresses.models.PublicIPAddress):
                    status, message = delete_public_ip(resource)
                    status_log.append({'SubscriptionId': subscription_id, 'Resource': resource.name, 'Action': 'delete', 'Status': status, 'Message': message})
                elif isinstance(resource, network_client.application_gateways.models.ApplicationGateway):
                    status, message = delete_application_gateway(network_client, resource, status_log, dry_run)
            elif action_type == 'update_sku':
                if isinstance(resource, storage_client.storage_accounts.models.StorageAccount):
                    status, message = update_storage_account_sku(resource, action['sku'])
                    status_log.append({'SubscriptionId': subscription_id, 'Resource': resource.name, 'Action': 'update_sku', 'Status': status, 'Message': message})
            elif action_type == 'scale_sql_database':
                status, message = scale_sql_database(resource, action['tiers'], status_log, dry_run, subscription_id)

def stop_vm(vm):
    """Stop a VM."""
    try:
        logging.info(f"Stopping VM: {vm.name}")
        async_stop = compute_client.virtual_machines.begin_deallocate(vm.resource_group_name, vm.name)
        async_stop.result()  # Wait for the operation to complete
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
        resource_group_name = disk.id.split('/')[4]
        logging.info(f"Disk resource group: {resource_group_name}")
        logging.info(f"Disk details: {disk}")
        async_delete = compute_client.disks.begin_delete(resource_group_name, disk.name)
        async_delete.result()  # Wait for the operation to complete
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
        delete_operation = resource_client.resource_groups.begin_delete(resource_group.name)
        while not delete_operation.done():
            print("Deleting resource group, please wait...")
            time.sleep(10)
        operation_status = delete_operation.status()
        if operation_status == "Succeeded":
            tc.track_event("ResourceGroupDeleted", {"ResourceGroupName": resource_group.name})
            logging.info(f"Resource Group {resource_group.name} deleted successfully.")
            return 'Success', 'Resource group deleted successfully.'
        else:
            tc.track_event("ResourceGroupDeletionFailed", {"ResourceGroupName": resource_group.name, "Error": "Deletion operation did not succeed"})
            logging.error(f"Failed to delete Resource Group {resource_group.name}: Deletion operation did not succeed")
            return 'Failed', "Failed to delete resource group: Deletion operation did not succeed"
    except Exception as e:
        logging.error(f"Failed to delete Resource Group {resource_group.name}: {e}")
        tc.track_event("ResourceGroupDeletionFailed", {"ResourceGroupName": resource_group.name, "Error": str(e)})
        return 'Failed', f"Failed to delete resource group: {e}"
    
def delete_public_ip(public_ip):
    """Delete a public IP address."""
    try:
        logging.info(f"Deleting Public IP: {public_ip.name}")
        resource_group_name = public_ip.id.split('/')[4]
        logging.info(f"Public IP resource group: {resource_group_name}")
        logging.info(f"Public IP details: {public_ip}")
        async_delete = network_client.public_ip_addresses.begin_delete(resource_group_name, public_ip.name)
        async_delete.result()  # Wait for the operation to complete
        tc.track_event("PublicIPDeleted", {"PublicIPName": public_ip.name})
        return 'Success', 'Public IP deleted successfully.'
    except Exception as e:
        logging.error(f"Failed to delete Public IP {public_ip.name}: {e}")
        tc.track_event("PublicIPDeletionFailed", {"PublicIPName": public_ip.name, "Error": str(e)})
        return 'Failed', f"Failed to delete Public IP: {e}"

def delete_application_gateway(network_client, application_gateway, status_log, dry_run=True):
    """Delete an application gateway."""
    logging.info(f"Deleting Application Gateway: {application_gateway.name}")
    resource_group_name = application_gateway.id.split('/')[4]
    if dry_run:
        status_log.append({'Resource': application_gateway.name, 'Action': 'delete', 'Status': 'Dry Run', 'Message': 'Dry run mode, no action taken'})
        return 'Dry Run', f'Would delete Application Gateway: {application_gateway.name} due to empty backend pools'
    else:
        try:
            async_delete = network_client.application_gateways.begin_delete(resource_group_name, application_gateway.name)
            async_delete.result()
            tc.track_event("ApplicationGatewayDeleted", {"ApplicationGatewayName": application_gateway.name})
            status_log.append({'Resource': application_gateway.name, 'Action': 'delete', 'Status': 'Success', 'Message': 'Application Gateway deleted successfully'})
            return 'Success', 'Application Gateway deleted successfully.'
        except Exception as e:
            logging.error(f"Failed to delete Application Gateway {application_gateway.name}: {e}")
            tc.track_event("ApplicationGatewayDeletionFailed", {"ApplicationGatewayName": application_gateway.name, "Error": str(e)})
            status_log.append({'Resource': application_gateway.name, 'Action': 'delete', 'Status': 'Failed', 'Message': f'Failed to delete Application Gateway: {e}'})
            return 'Failed', f"Failed to delete Application Gateway: {e}"

def update_storage_account_sku(storage_account, new_sku):
    """Update the SKU of a storage account"""
    try:
        logging.info(f"Updating storage account SKU: {storage_account.name}")
        storage_client.storage_accounts.update(
            resource_group_name=storage_account.id.split('/')[4],
            account_name=storage_account.name,
            parameters={'sku': {'name': new_sku}}
        )
        tc.track_event("StorageAccountSkuUpdated", {"StorageAccountName": storage_account.name, "NewSku": new_sku})
        return 'Success', f'Storage account SKU updated to {new_sku}.'
    except Exception as e:
        logging.error(f"Failed to update storage account SKU {storage_account.name}: {e}")
        tc.track_event("StorageAccountSkuUpdateFailed", {"StorageAccountName": storage_account.name, "Error": str(e)})
        return 'Failed', f'Failed to update storage account SKU: {e}'

def scale_sql_database(database, tiers, status_log, dry_run=True, subscription_id=None):
    current_time = datetime.now().time()
    for tier in tiers:
        if tier['name'] in database.sku.name:
            off_peak_start = datetime.strptime(tier['off_peak_start'], "%H:%M").time()
            off_peak_end = datetime.strptime(tier['off_peak_end'], "%H:%M").time()

            if off_peak_start < off_peak_end:
                is_off_peak = off_peak_start <= current_time < off_peak_end
            else:  # Over midnight
                is_off_peak = not (off_peak_end <= current_time < off_peak_start)

            new_dtu = tier['off_peak_dtu'] if is_off_peak else tier['peak_dtu']

            if new_dtu == database.sku.capacity:
                message = 'Current DTU is already optimal. No scaling required.'
                logging.info(f"Database: {database.name}, {message}")
                status_log.append({'SubscriptionId': subscription_id, 'Resource': database.name, 'Action': 'scale', 'Status': 'No Change', 'Message': message})
                return 'No Change', message

            logging.info(f"Database: {database.name}, Current DTU: {database.sku.capacity}, New DTU: {new_dtu}")
            message = (f'Dry run mode, no action taken. Would scale DTU to {new_dtu}' 
                       if dry_run else f'Scaled DTU to {new_dtu}')
            logging.info(f"Scale status for {database.name}: {message}")
            status_log.append({'SubscriptionId': subscription_id, 'Resource': database.name, 'Action': 'scale', 'Status': 'Dry Run' if dry_run else 'Success', 'Message': message})
            if not dry_run:
                simple_scale_sql_database(sql_client, database, new_dtu, tier['min_dtu'], tier['max_dtu'], dry_run)
            return 'Success', message
    return 'No Change', 'Current DTU is already optimal.'

def wrap_text(text, width=30):
    """Wrap text to a given width."""
    return "\n".join(textwrap.wrap(text, width))

def review_application_gateways(policies, status_log, dry_run=True):
    impacted_resources = []
    for policy in policies:
        if policy['resource'] == 'azure.applicationgateway':
            logging.info("Reviewing application gateways for policy: {}".format(policy['name']))
            gateways = network_client.application_gateways.list_all()
            for gateway in gateways:
                if not gateway.backend_address_pools or any(not pool.backend_addresses for pool in gateway.backend_address_pools):
                    if evaluate_filters(gateway, policy['filters']):
                        try:
                            status, message = apply_app_gateway_actions(network_client, gateway, policy['actions'], status_log, dry_run)
                            if status != 'No Change':
                                impacted_resources.append({
                                    'Policy': policy['name'],
                                    'Resource': gateway.name,
                                    'Actions': ', '.join([action['type'] for action in policy['actions']]),
                                    'Status': status,
                                    'Message': message
                                })
                        except Exception as e:
                            logging.error(f"Failed to apply actions: {e}")
    return impacted_resources

def apply_app_gateway_actions(network_client, gateway, actions, status_log, dry_run=True):
    status = 'No Change'
    message = 'No applicable actions found'
    for action in actions:
        action_type = action['type']
        if action_type == 'log':
            status, message = log_empty_backend_pool(gateway, dry_run)
        elif action_type == 'delete':
            try:
                print(colored(f"Deleting Application Gateway: {gateway.name}", "red"))
                status, message = delete_application_gateway(network_client, gateway, status_log, dry_run)
            except Exception as e:
                logging.error(f"Failed to delete application gateway: {e}")
    return status, message

def log_empty_backend_pool(gateway, dry_run=True):
    logging.info(f"Empty backend pool found in Application Gateway: {gateway.name}")
    if dry_run:
        return 'Dry Run', f'Would log empty backend pool in Application Gateway: {gateway.name}'
    else:
        return 'Success', f'Logged empty backend pool in Application Gateway: {gateway.name}'

def get_waste_cost_details(subscription_id):
    """Retrieve waste cost details for a subscription."""
    consumption_client = ConsumptionManagementClient(credential, subscription_id)
    scope = f"/subscriptions/{subscription_id}"
    waste_costs = defaultdict(float)

    try:
        usage_details = consumption_client.usage_details.list(scope)
        for detail in usage_details:
            # Assuming 'instance_name' or 'id' contains the resource group and resource name
            # Adjust parsing logic based on actual data structure
            
            resource_group_name = detail.instance_name.split('/')[4]
            resource_name = detail.instance_name.split('/')[-1]
            cost = detail.cost_in_usd  # Adjust attribute name if necessary

            # Sum costs by resource group and resource
            waste_costs[resource_group_name] += cost
            waste_costs[resource_name] += cost

    except Exception as e:
        logging.error(f"Failed to retrieve waste cost details for subscription {subscription_id}: {e}")

    return waste_costs

def calculate_waste_cost(data):
    """Calculate waste cost based on impact and cost per unit."""
    data['waste_cost'] = data['impact'] * data['cost_per_unit']
    return data

def apply_policies(policies, dry_run, subscription_id, impacted_resources, non_impacted_resources, status_log):
    """Apply policies to resources."""

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
                    apply_actions(vm, actions, status_log, dry_run, subscription_id)
                    impacted_resources.append({'SubscriptionId': subscription_id, 'Policy': policy['name'], 'Resource': vm.name, 'Actions': ', '.join([action['type'] for action in actions])})
                    resources_impacted = True
            if not resources_impacted:
                non_impacted_resources.append({'SubscriptionId': subscription_id, 'Policy': policy['name'], 'ResourceType': 'VM'})

        elif resource_type == 'azure.disk':
            disks = compute_client.disks.list()
            for disk in disks:
                logging.info(f"Evaluating disk {disk.name} for deletion.")
                if not evaluate_exclusions(disk, exclusions) and evaluate_filters(disk, filters):
                    apply_actions(disk, actions, status_log, dry_run, subscription_id)
                    impacted_resources.append({'SubscriptionId': subscription_id, 'Policy': policy['name'], 'Resource': disk.name, 'Actions': ', '.join([action['type'] for action in actions])})
                    resources_impacted = True
            if not resources_impacted:
                non_impacted_resources.append({'SubscriptionId': subscription_id, 'Policy': policy['name'], 'ResourceType': 'Disk'})

        elif resource_type == 'azure.resourcegroup':
            resource_groups = resource_client.resource_groups.list()
            for resource_group in resource_groups:
                if not evaluate_exclusions(resource_group, exclusions) and evaluate_filters(resource_group, filters):
                    apply_actions(resource_group, actions, status_log, dry_run, subscription_id)
                    impacted_resources.append({'SubscriptionId': subscription_id, 'Policy': policy['name'], 'Resource': resource_group.name, 'Actions': ', '.join([action['type'] for action in actions])})
                    resources_impacted = True
            if not resources_impacted:
                non_impacted_resources.append({'SubscriptionId': subscription_id, 'Policy': policy['name'], 'ResourceType': 'Resource Group'})

        elif resource_type == 'azure.storage':
            storage_accounts = storage_client.storage_accounts.list()
            for storage_account in storage_accounts:
                if not evaluate_exclusions(storage_account, exclusions) and evaluate_filters(storage_account, filters):
                    apply_actions(storage_account, actions, status_log, dry_run, subscription_id)
                    impacted_resources.append({'SubscriptionId': subscription_id, 'Policy': policy['name'], 'Resource': storage_account.name, 'Actions': ', '.join([action['type'] for action in actions])})
                    resources_impacted = True
            if not resources_impacted:
                non_impacted_resources.append({'SubscriptionId': subscription_id, 'Policy': policy['name'], 'ResourceType': 'Storage Account'})

        elif resource_type == 'azure.publicip':
            public_ips = network_client.public_ip_addresses.list_all()
            for public_ip in public_ips:
                if not evaluate_exclusions(public_ip, exclusions) and evaluate_filters(public_ip, filters):
                    apply_actions(public_ip, actions, status_log, dry_run, subscription_id)
                    impacted_resources.append({'SubscriptionId': subscription_id, 'Policy': policy['name'], 'Resource': public_ip.name, 'Actions': ', '.join([action['type'] for action in actions])})
                    resources_impacted = True
                    
            if not resources_impacted:
                non_impacted_resources.append({'SubscriptionId': subscription_id, 'Policy': policy['name'], 'ResourceType': 'Public IP'})

        elif resource_type == 'azure.sql':
            servers = sql_client.servers.list()
            for server in servers:
                resource_group_name = server.id.split('/')[4]
                databases = sql_client.databases.list_by_server(resource_group_name, server.name)
                for db in databases:
                    logging.info(f"Database: {db.name}, Current DTU: {db.sku.capacity}")
                    status, message = scale_sql_database(db, policy['actions'][0]['tiers'], status_log, dry_run, subscription_id)
                    if status != 'No Change':
                        impacted_resources.append({'SubscriptionId': subscription_id, 'Policy': policy['name'], 'Resource': db.name, 'Actions': 'scale', 'Status': status, 'Message': message})
                        resources_impacted = True
            if not resources_impacted:
                non_impacted_resources.append({'SubscriptionId': subscription_id, 'Policy': policy['name'], 'ResourceType': 'SQL Database'})

        elif resource_type == 'azure.applicationgateway':
            policy_results = review_application_gateways([policy], status_log, dry_run=dry_run)
            impacted_resources.extend([{'SubscriptionId': subscription_id, **res} for res in policy_results])
            if policy_results:
                resources_impacted = True
            else:
                non_impacted_resources.append({'SubscriptionId': subscription_id, 'Policy': policy['name'], 'ResourceType': 'Application Gateway'})

def process_subscription(subscription, mode, summary_reports, impacted_resources, non_impacted_resources, status_log):
    """Process a single subscription for cost optimization."""
    global resource_client, cost_management_client, compute_client, storage_client, network_client, sql_client
    
    subscription_id = subscription.subscription_id
    resource_client = ResourceManagementClient(credential, subscription_id)
    cost_management_client = CostManagementClient(credential)
    compute_client = ComputeManagementClient(credential, subscription_id)
    storage_client = StorageManagementClient(credential, subscription_id)
    network_client = NetworkManagementClient(credential, subscription_id)
    sql_client = SqlManagementClient(credential, subscription_id)

    logging.info(f'Processing subscription: {subscription_id}')
    tc.track_event("SubscriptionProcessingStarted", {"SubscriptionId": subscription_id})

    try:
        policy_file = config['policies']['policy_file']
        schema_file = config['policies']['schema_file']
        policies = load_policies(policy_file, schema_file)
        cost_data = get_cost_data(f'/subscriptions/{subscription_id}')
        if cost_data:
            analyze_cost_data(cost_data, subscription_id, summary_reports)
        apply_policies(policies, mode == 'dry-run', subscription_id=subscription_id, impacted_resources=impacted_resources, non_impacted_resources=non_impacted_resources, status_log=status_log)
        tc.flush()
    except Exception as e:
        logging.error(f"Error in subscription {subscription_id}: {e}")
        tc.track_exception()
        tc.flush()

def main(mode, all_subscriptions):
    """Main function to execute cost optimization."""
    logging.info('Cost Optimizer Function triggered.')
    tc.track_event("FunctionTriggered")

    summary_reports = []
    impacted_resources = []
    non_impacted_resources = []
    status_log = []

    if all_subscriptions:
        subscriptions = subscription_client.subscriptions.list()
        for subscription in subscriptions:
            process_subscription(subscription, mode, summary_reports, impacted_resources, non_impacted_resources, status_log)
    else:
        subscription_id = os.getenv('AZURE_SUBSCRIPTION_ID')
        subscription = subscription_client.subscriptions.get(subscription_id)
        process_subscription(subscription, mode, summary_reports, impacted_resources, non_impacted_resources, status_log)

    # Display all reports and logs in a consolidated manner
    if summary_reports:
        table_summary = PrettyTable()
        table_summary.field_names = ["Subscription ID", "Summary Report", "Cost"]
        for summary in summary_reports:
            table_summary.add_row([summary["SubscriptionId"], "Total Cost", f"{summary['TotalCost']:.2f}"])
            table_summary.add_row([summary["SubscriptionId"], "Average Daily Cost", f"{summary['AverageDailyCost']:.2f}"])
            table_summary.add_row([summary["SubscriptionId"], "Maximum Daily Cost", f"{summary['MaximumDailyCost']:.2f}"])
            table_summary.add_row([summary["SubscriptionId"], "Minimum Daily Cost", f"{summary['MinimumDailyCost']:.2f}"])
        print(colored("Cost Summary Reports:", "cyan", attrs=["bold"]))
        print(colored(table_summary.get_string(), "cyan"))
        
    if impacted_resources:
        table = PrettyTable()
        table.field_names = ["Subscription ID", "Policy", "Resource", "Actions"]
        for resource in impacted_resources:
            table.add_row([resource['SubscriptionId'], wrap_text(resource['Policy']), wrap_text(resource['Resource']), wrap_text(resource['Actions'])])
        print(colored("Impacted Resources:", "cyan", attrs=["bold"]))
        print(colored(table.get_string(), "cyan"))
        tc.track_event("ImpactedResources", {"Resources": impacted_resources})

    if non_impacted_resources:
        table_non_impacted = PrettyTable()
        table_non_impacted.field_names = ["Subscription ID", "Policy", "Resource Type"]
        for resource in non_impacted_resources:
            table_non_impacted.add_row([resource['SubscriptionId'], wrap_text(resource['Policy']), wrap_text(resource['ResourceType'])])
        print(colored("Non-Impacted Resources:", "cyan", attrs=["bold"]))
        print(colored(table_non_impacted.get_string(), "cyan"))

    if status_log:
        table_status = PrettyTable()
        table_status.field_names = ["Subscription ID", "Resource", "Action", "Status", "Message"]
        for log in status_log:
            color = "green" if log['Status'] == "Success" else "red"
            table_status.add_row([log['SubscriptionId'], wrap_text(log['Resource']), wrap_text(log['Action']), colored(log['Status'], color, attrs=["bold"]), wrap_text(log['Message'])])
        print(colored("Operation Status:", "cyan", attrs=["bold"]))
        print(colored(table_status.get_string(), "black"))
        tc.track_event("OperationStatus", {"Status": status_log})

    # Calculate and display waste cost details
    if impacted_resources:
        table_waste_cost = PrettyTable()
        table_waste_cost.field_names = ["Subscription ID", "Resource", "Monthly Waste Cost", "Potential Yearly Waste Cost"]
        
        for resource in impacted_resources:
            resource_id = resource['Resource']
            monthly_cost = sum([cost for res, cost in get_waste_cost_details(resource['SubscriptionId']).items() if res == resource_id])
            yearly_cost = monthly_cost * 12
            table_waste_cost.add_row([resource['SubscriptionId'], wrap_text(resource_id), f"{monthly_cost:.2f}", f"{yearly_cost:.2f}"])
        
        print(colored("Waste Cost Details:", "cyan", attrs=["bold"]))
        print(colored(table_waste_cost.get_string(), "cyan"))
        tc.track_event("WasteCostDetails", {"WasteCosts": table_waste_cost.get_string()})

if __name__ == "__main__":
    print(colored(r""" _______                            _______                    _______            _       _                   
(_______)                          (_______)            _     (_______)       _  (_)     (_)                  
 _______ _____ _   _  ____ _____    _       ___   ___ _| |_    _     _ ____ _| |_ _ ____  _ _____ _____  ____ 
|  ___  (___  ) | | |/ ___) ___ |  | |     / _ \ /___|_   _)  | |   | |  _ (_   _) |    \| (___  ) ___ |/ ___)
| |   | |/ __/| |_| | |   | ____|  | |____| |_| |___ | | |_   | |___| | |_| || |_| | | | | |/ __/| ____| |    
|_|   |_(_____)____/|_|   |_____)   \______)___/(___/   \__)   \_____/|  __/  \__)_|_|_|_|_(_____)_____)_|    
                                                                      |_|                                     
    """, "light_blue"))

    print(colored("Running Azure Cost Optimizer Tool...", "black"))
    print(colored("Please wait...", "black"))
    for i in range(10):
        time.sleep(0.2)
    print(colored("Azure Cost Optimizer Tool is ready!", "green"))
    print(colored("="*110, "black"))
    parser = argparse.ArgumentParser(description="Azure Cost Optimization Tool")
    parser.add_argument('--mode', choices=['dry-run', 'apply'], required=True, help="Mode to run the function (dry-run or apply)")
    parser.add_argument('--all-subscriptions', action='store_true', help="Process all subscriptions in the tenant")
    args = parser.parse_args()
    main(args.mode, args.all_subscriptions)
    print(colored("Azure Cost Optimizer Tool completed!", "green"))
    print(colored("="*110, "black"))
