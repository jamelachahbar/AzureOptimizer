import argparse
import logging
import os
import sys
import time
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
from azure.mgmt.sql.models import Sku, Database
from azure.mgmt.subscription import SubscriptionClient
import pandas as pd
import matplotlib.pyplot as plt
from dotenv import load_dotenv
from prettytable import PrettyTable
from termcolor import colored
from sklearn.ensemble import IsolationForest
import textwrap
from collections import defaultdict
import pytz
from azure.storage.filedatalake import DataLakeServiceClient
import io

# Set up logging
#logging.basicConfig(level=logging.DEBUG, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

# Set FORCE_COLOR to 1 to ensure color output
os.environ["FORCE_COLOR"] = "1"
# Check if environment variables are already set, if not, load from .env file
if not os.getenv("AZURE_CLIENT_ID"):
    load_dotenv()

# Load configuration from config.yaml
config_file = os.getenv("CONFIG_FILE", "configs/config.yaml")
if not config_file:
    raise Exception("CONFIG_FILE environment variable not set.")
with open(config_file, "r") as file:
    config = yaml.safe_load(file)

# Initialize Application Insights Telemetry Client
instrumentation_key = os.getenv("APPINSIGHTS_INSTRUMENTATIONKEY")
if not instrumentation_key:
    raise Exception("Instrumentation key was required but not provided")
tc = TelemetryClient(instrumentation_key)

# Authentication
credential = DefaultAzureCredential()
# Clients
subscription_client = SubscriptionClient(credential)

# Verify that the necessary environment variables are set and log their values
required_env_vars = [
    "AZURE_CLIENT_ID",
    "AZURE_TENANT_ID",
    "AZURE_CLIENT_SECRET",
    "AZURE_SUBSCRIPTION_ID",
    "AZURE_STORAGE_ACCOUNT_NAME",
    "AZURE_STORAGE_FILE_SYSTEM_NAME",
    "ADLS_DIRECTORY_PATH"
]
for var in required_env_vars:
    value = os.getenv(var)
    if not value:
        logger.error(f"Environment variable {var} is not set.")
        sys.exit(1)
    logger.info(f"{var}: {value}")

# Read environment variables for storage account and file system
account_name = os.getenv('AZURE_STORAGE_ACCOUNT_NAME')
file_system_name = os.getenv('AZURE_STORAGE_FILE_SYSTEM_NAME')
directory_path = os.getenv('ADLS_DIRECTORY_PATH')

# Check if environment variables are set correctly
if not account_name or not file_system_name:
    logger.error("Environment variables AZURE_STORAGE_ACCOUNT_NAME or AZURE_STORAGE_FILE_SYSTEM_NAME are not set.")
else:
    logger.info(f"Using storage account: {account_name}")
    logger.info(f"Using file system: {file_system_name}")

# Authentication and client setup
service_client = DataLakeServiceClient(
    account_url=f"https://{account_name}.dfs.core.windows.net",
    credential=credential
)

# Function to list files in a directory
def list_files_in_directory(directory_path):
    try:
        file_system_client = service_client.get_file_system_client(file_system_name)
        paths = file_system_client.get_paths(path=directory_path)

        files = []
        folders = []
        for path in paths:
            if path.is_directory:
                folders.append(path.name)
            else:
                files.append(path.name)

        logger.info(f"Folders in directory {directory_path}: {folders}")
        logger.info(f"Files in directory {directory_path}: {files}")

        return files
    except Exception as e:
        logger.error(f"Error listing files in directory {directory_path}: {e}")
        return []

def read_parquet_file_from_adls(file_path):
    try:
        file_system_client = service_client.get_file_system_client(file_system_name)
        file_client = file_system_client.get_file_client(file_path)

        download = file_client.download_file()
        downloaded_bytes = download.readall()

        df = pd.read_parquet(io.BytesIO(downloaded_bytes))
        return df
    except Exception as e:
        logger.error(f"Error reading Parquet file {file_path}: {e}")
        return pd.DataFrame()

# Function to fetch cost data from ADLS
def fetch_cost_data_from_adls(directory_path):
    try:
        files = list_files_in_directory(directory_path)
        all_data = []

        for file in files:
            if file.endswith('.parquet'):
                logger.info(f"Reading file: {file}")
                df = read_parquet_file_from_adls(file)
                all_data.append(df)

        if all_data:
            combined_df = pd.concat(all_data, ignore_index=True)
            combined_df['BilledCost'] = combined_df['BilledCost'].astype(float)  # Ensure BilledCost is float
            return combined_df
        else:
            logger.warning("No Parquet files found in the specified directory.")
            return pd.DataFrame()
    except Exception as e:
        logger.error(f"Error fetching cost data from ADLS: {e}")
        raise

def load_policies(policy_file, schema_file):
    """Load and validate policies from the YAML file against the schema."""
    with open(policy_file, "r") as file:
        policies = yaml.safe_load(file)
    with open(schema_file, "r") as file:
        schema = json.load(file)
    jsonschema.validate(instance=policies, schema=schema)
    return policies["policies"]

def get_cost_data(scope):
    """Retrieve cost data from Azure."""
    try:
        logger.info(f"Retrieving cost data for scope: {scope}")
        time.sleep(15)  # Delay to avoid rate limiting

        cet = pytz.timezone("CET")
        now_cet = datetime.now(cet)

        start_date = (now_cet - timedelta(days=30)).isoformat()
        end_date = now_cet.isoformat()

        cost_data = cost_management_client.query.usage(
            scope,
            {
                "type": "Usage",
                "timeframe": "Custom",
                "timePeriod": {"from": start_date, "to": end_date},
                "dataset": {
                    "granularity": "Daily",
                    "aggregation": {
                        "totalCost": {"name": "PreTaxCost", "function": "Sum"}
                    },
                },
            },
        )

        return cost_data
    except Exception as e:
        logger.error(f"Failed to retrieve cost data for scope {scope}: {e}")
        return None

def analyze_cost_data(cost_data, subscription_id, summary_reports):
    """Analyze cost data until yesterday, detect trends, anomalies, and generate reports."""
    data = []
    cet = pytz.timezone("CET")
    now_cet = datetime.now(cet)

    for item in cost_data.rows:
        try:
            date_str = str(item[1])
            date = pd.to_datetime(date_str, format="%Y%m%d")
            date = date.tz_localize("UTC").tz_convert(cet)

            if date.date() < now_cet.date():
                data.append({"date": date, "cost": item[0]})
        except Exception as e:
            logger.error(f"Error parsing date: {e}, Item: {item}")

    df = pd.DataFrame(data)
    df["date"] = pd.to_datetime(df["date"])
    df.set_index("date", inplace=True)
    df = df.asfreq("D")

    for _, row in df.iterrows():
        logger.info(f"Date: {row.name.date()}, Cost: {row['cost']}")
        tc.track_metric(
            "DailyCost", row["cost"], properties={"Date": row.name.date().isoformat()}
        )

    trend_analysis(df, subscription_id)
    detect_anomalies_isolation_forest(df, subscription_id)
    generate_summary_report(df, subscription_id, summary_reports)

def trend_analysis(df, subscription_id):
    """Analyze cost trends over time and plot the trend."""
    df["cost"].plot(
        title=f"Cost Trend Over Time for Subscription {subscription_id}",
        figsize=(10, 5),
    )
    plt.xlabel("Date")
    plt.ylabel("Cost")
    plt.savefig(f"cost_trend_{subscription_id}.png")
    plt.close()
    logger.info(f"Trend analysis plot saved as cost_trend_{subscription_id}.png.")
    tc.track_event("TrendAnalysisCompleted", {"SubscriptionId": subscription_id})

def detect_anomalies_isolation_forest(df, subscription_id):
    """Detect anomalies in the cost data using Isolation Forest."""
    model = IsolationForest(contamination=0.025)
    df["anomaly"] = model.fit_predict(df[["cost"]])
    anomalies = df[df["anomaly"] == -1]

    if not anomalies.empty:
        for _, row in anomalies.iterrows():
            tc.track_event(
                "AnomalyDetectedIsolationForest",
                {
                    "SubscriptionId": subscription_id,
                    "Date": row.name.date().isoformat(),
                    "Cost": row["cost"],
                },
            )
            table = PrettyTable()
            table.field_names = ["Subscription ID", "Anomaly Detected", "Date", "Cost"]
            table.add_row(
                [
                    subscription_id,
                    "Isolation Forest Algorithm",
                    row.name.date().isoformat(),
                    f'{row["cost"]:.2f}',
                ]
            )
            print(colored(table, "red"))
    else:
        logger.info(
            f"No anomalies detected in cost data for subscription {subscription_id} using Isolation Forest."
        )
        tc.track_event(
            "NoAnomaliesDetectedIsolationForest", {"SubscriptionId": subscription_id}
        )

def generate_summary_report(df, subscription_id, summary_reports):
    """Generate a summary report of the cost data."""
    total_cost = df["cost"].sum()
    avg_cost = df["cost"].mean()
    max_cost = df["cost"].max()
    min_cost = df["cost"].min()

    logger.info(f"Total Cost for subscription {subscription_id}: {total_cost}")
    logger.info(f"Average Daily Cost for subscription {subscription_id}: {avg_cost}")
    logger.info(f"Maximum Daily Cost for subscription {subscription_id}: {max_cost}")
    logger.info(f"Minimum Daily Cost for subscription {subscription_id}: {min_cost}")

    summary_reports.append(
        {
            "SubscriptionId": subscription_id,
            "TotalCost": total_cost,
            "AverageDailyCost": avg_cost,
            "MaximumDailyCost": max_cost,
            "MinimumDailyCost": min_cost,
        }
    )

    tc.track_event(
        "SummaryReportGenerated",
        {
            "SubscriptionId": subscription_id,
            "TotalCost": total_cost,
            "AverageDailyCost": avg_cost,
            "MaximumDailyCost": max_cost,
            "MinimumDailyCost": min_cost,
        },
    )
    tc.track_metric(
        "TotalCost", total_cost, properties={"SubscriptionId": subscription_id}
    )
    tc.track_metric(
        "AverageDailyCost", avg_cost, properties={"SubscriptionId": subscription_id}
    )
    tc.track_metric(
        "MaximumDailyCost", max_cost, properties={"SubscriptionId": subscription_id}
    )
    tc.track_metric(
        "MinimumDailyCost", min_cost, properties={"SubscriptionId": subscription_id}
    )

def evaluate_filters(resource, filters):
    """Evaluate if a resource meets the defined filters."""
    for filter in filters:
        filter_type = filter["type"]
        if filter_type == "last_used":
            if not last_used_filter(resource, filter["days"]):
                return False
        elif filter_type == "unattached":
            if not unattached_filter(resource):
                return False
        elif filter_type == "tag":
            if not tag_filter(resource, filter["key"], filter["value"]):
                return False
        elif filter_type == "sku":
            if not sku_filter(resource, filter["values"]):
                return False
    return True

def evaluate_exclusions(resource, exclusions):
    """Evaluate if a resource meets any of the exclusion criteria."""
    for exclusion in exclusions:
        exclusion_type = exclusion["type"]
        if exclusion_type == "tag":
            if tag_filter(resource, exclusion["key"], exclusion["value"]):
                return True
    return False

def last_used_filter(resource, days):
    """Check if a resource was last used within a specified number of days."""
    last_used_date = get_last_used_date(resource)
    return (datetime.now() - last_used_date).days <= days

def unattached_filter(resource):
    """Check if a resource is unattached."""
    logger.info(f"Checking if resource {resource.name} is unattached.")
    
    # Check if the resource is a Public IP Address
    if isinstance(resource, network_client.public_ip_addresses.models.PublicIPAddress):
        if resource.ip_configuration is None:
            # Check for associations with Load Balancers and NAT Gateways
            associated_lb = network_client.load_balancers.list_all()
            for lb in associated_lb:
                for frontend_ip in lb.frontend_ip_configurations:
                    if (
                        frontend_ip.public_ip_address
                        and frontend_ip.public_ip_address.id == resource.id
                    ):
                        return False
            associated_nat_gateways = network_client.nat_gateways.list_all()
            for nat_gateway in associated_nat_gateways:
                for public_ip in nat_gateway.public_ip_addresses:
                    if public_ip.id == resource.id:
                        return False
            return True
        else:
            return False
    
    # Check if the resource is a Network Interface (NIC)
    elif isinstance(resource, network_client.network_interfaces.models.NetworkInterface):
        # Check if the NIC is attached to a private endpoint
        if resource.private_endpoint:
            logger.info(f"NIC {resource.name} is attached to a private endpoint and will not be deleted.")
            return False
        return not resource.virtual_machine
    
    # Default case: check if the resource is managed by another resource
    return resource.managed_by is None

def tag_filter(resource, key, value):
    """Check if a resource has a specific tag."""
    if not hasattr(resource, "tags"):
        logger.error(f"Resource {resource} does not have tags attribute.")
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
        action_type = action["type"]
        if dry_run:
            action_description = f"[Dry Run] Action: {action_type} on Resource: {resource.name} in Subscription: {subscription_id}"
            logger.info(action_description)
            status_log.append(
                {
                    "SubscriptionId": subscription_id,
                    "Resource": resource.name,
                    "Action": action_type,
                    "Status": "Dry Run",
                    "Message": action_description,
                }
            )
        else:
            if action_type == "stop":
                status, message = stop_vm(resource)
                status_log.append(
                    {
                        "SubscriptionId": subscription_id,
                        "Resource": resource.name,
                        "Action": "stop",
                        "Status": status,
                        "Message": message,
                    }
                )
            elif action_type == "delete":
                if isinstance(resource, compute_client.disks.models.Disk):
                    status, message = delete_disk(resource)
                    status_log.append(
                        {
                            "SubscriptionId": subscription_id,
                            "Resource": resource.name,
                            "Action": "delete",
                            "Status": status,
                            "Message": message,
                        }
                    )
                elif isinstance(
                    resource, resource_client.resource_groups.models.ResourceGroup
                ):
                    status, message = delete_resource_group(resource)
                    status_log.append(
                        {
                            "SubscriptionId": subscription_id,
                            "Resource": resource.name,
                            "Action": "delete",
                            "Status": status,
                            "Message": message,
                        }
                    )
                elif isinstance(
                    resource, network_client.public_ip_addresses.models.PublicIPAddress
                ):
                    status, message = delete_public_ip(resource)
                    status_log.append(
                        {
                            "SubscriptionId": subscription_id,
                            "Resource": resource.name,
                            "Action": "delete",
                            "Status": status,
                            "Message": message,
                        }
                    )
                elif isinstance(resource, network_client.network_interfaces.models.NetworkInterface):
                    status, message = delete_network_interface(resource)
                    status_log.append(
                        {
                            "SubscriptionId": subscription_id,
                            "Resource": resource.name,
                            "Action": "delete",
                            "Status": status,
                            "Message": message,
                        }
                    )
                elif isinstance(
                    resource,
                    network_client.application_gateways.models.ApplicationGateway,
                ):
                    status, message = delete_application_gateway(
                        network_client, resource, status_log, dry_run
                    )
            elif action_type == "update_sku":
                if isinstance(
                    resource, storage_client.storage_accounts.models.StorageAccount
                ):
                    status, message = update_storage_account_sku(
                        resource, action["sku"]
                    )
                    status_log.append(
                        {
                            "SubscriptionId": subscription_id,
                            "Resource": resource.name,
                            "Action": "update_sku",
                            "Status": status,
                            "Message": message,
                        }
                    )
            elif action_type == "scale_sql_database":
                status, message = scale_sql_database(
                    resource, action["tiers"], status_log, dry_run, subscription_id
                )
            elif isinstance(resource, network_client.network_interfaces.models.NetworkInterface):
                status, message = delete_network_interface(resource)
                status_log.append(
                        {
                            "SubscriptionId": subscription_id,
                            "Resource": resource.name,
                            "Action": "delete",
                            "Status": status,
                            "Message": message,
                        }
                    )

def delete_network_interface(nic):
    """Delete an unattached network interface."""
    try:
        logger.info(f"Deleting Network Interface: {nic.name}")
        resource_group_name = nic.id.split("/")[4]
        async_delete = network_client.network_interfaces.begin_delete(resource_group_name, nic.name)
        async_delete.result()  # Wait for the operation to complete
        tc.track_event("NetworkInterfaceDeleted", {"NetworkInterfaceName": nic.name})
        return "Success", "Network Interface deleted successfully."
    except Exception as e:
        logger.error(f"Failed to delete Network Interface {nic.name}: {e}")
        tc.track_event("NetworkInterfaceDeletionFailed", {"NetworkInterfaceName": nic.name, "Error": str(e)})
        return "Failed", f"Failed to delete Network Interface: {e}"

def stop_vm(vm):
    """Stop a VM."""
    try:
        logger.info(f"Stopping VM: {vm.name}")
        async_stop = compute_client.virtual_machines.begin_deallocate(
            vm.resource_group_name, vm.name
        )
        async_stop.result()  # Wait for the operation to complete
        tc.track_event("VMStopped", {"VMName": vm.name})
        return "Success", "VM stopped successfully."
    except Exception as e:
        logger.error(f"Failed to stop VM {vm.name}: {e}")
        tc.track_event("VMStopFailed", {"VMName": vm.name, "Error": str(e)})
        return "Failed", f"Failed to stop VM: {e}"

def delete_disk(disk):
    """Delete a disk."""
    try:
        logger.info(f"Attempting to delete disk: {disk.name}")
        resource_group_name = disk.id.split("/")[4]
        logger.info(f"Disk resource group: {resource_group_name}")
        logger.info(f"Disk details: {disk}")
        async_delete = compute_client.disks.begin_delete(resource_group_name, disk.name)
        async_delete.result()  # Wait for the operation to complete
        tc.track_event("DiskDeleted", {"DiskName": disk.name})
        return "Success", "Disk deleted successfully."
    except Exception as e:
        logger.error(f"Failed to delete Disk {disk.name}: {e}")
        tc.track_event("DiskDeletionFailed", {"DiskName": disk.name, "Error": str(e)})
        return "Failed", f"Failed to delete disk: {e}"

def delete_resource_group(resource_group):
    """Delete all resources in a resource group."""
    try:
        logger.info(f"Deleting Resource Group: {resource_group.name}")
        delete_operation = resource_client.resource_groups.begin_delete(
            resource_group.name
        )
        while not delete_operation.done():
            print("Deleting resource group, please wait...")
            time.sleep(10)
        operation_status = delete_operation.status()
        if operation_status == "Succeeded":
            tc.track_event(
                "ResourceGroupDeleted", {"ResourceGroupName": resource_group.name}
            )
            logger.info(f"Resource Group {resource_group.name} deleted successfully.")
            return "Success", "Resource group deleted successfully."
        else:
            tc.track_event(
                "ResourceGroupDeletionFailed",
                {
                    "ResourceGroupName": resource_group.name,
                    "Error": "Deletion operation did not succeed",
                },
            )
            logger.error(
                f"Failed to delete Resource Group {resource_group.name}: Deletion operation did not succeed"
            )
            return (
                "Failed",
                "Failed to delete resource group: Deletion operation did not succeed",
            )
    except Exception as e:
        logger.error(f"Failed to delete Resource Group {resource_group.name}: {e}")
        tc.track_event(
            "ResourceGroupDeletionFailed",
            {"ResourceGroupName": resource_group.name, "Error": str(e)},
        )
        return "Failed", f"Failed to delete resource group: {e}"

def delete_public_ip(public_ip):
    """Delete a public IP address."""
    try:
        logger.info(f"Deleting Public IP: {public_ip.name}")
        resource_group_name = public_ip.id.split("/")[4]
        logger.info(f"Public IP resource group: {resource_group_name}")
        logger.info(f"Public IP details: {public_ip}")
        async_delete = network_client.public_ip_addresses.begin_delete(
            resource_group_name, public_ip.name
        )
        async_delete.result()  # Wait for the operation to complete
        tc.track_event("PublicIPDeleted", {"PublicIPName": public_ip.name})
        return "Success", "Public IP deleted successfully."
    except Exception as e:
        logger.error(f"Failed to delete Public IP {public_ip.name}: {e}")
        tc.track_event(
            "PublicIPDeletionFailed", {"PublicIPName": public_ip.name, "Error": str(e)}
        )
        return "Failed", f"Failed to delete Public IP: {e}"

def delete_application_gateway(
    network_client, application_gateway, status_log, dry_run=True
):
    """Delete an application gateway."""
    logger.info(f"Deleting Application Gateway: {application_gateway.name}")
    resource_group_name = application_gateway.id.split("/")[4]
    if dry_run:
        status_log.append(
            {
                "Resource": application_gateway.name,
                "Action": "delete",
                "Status": "Dry Run",
                "Message": "Dry run mode, no action taken",
            }
        )
        return (
            "Dry Run",
            f"Would delete Application Gateway: {application_gateway.name} due to empty backend pools",
        )
    else:
        try:
            async_delete = network_client.application_gateways.begin_delete(
                resource_group_name, application_gateway.name
            )
            async_delete.result()
            tc.track_event(
                "ApplicationGatewayDeleted",
                {"ApplicationGatewayName": application_gateway.name},
            )
            status_log.append(
                {
                    "Resource": application_gateway.name,
                    "Action": "delete",
                    "Status": "Success",
                    "Message": "Application Gateway deleted successfully",
                }
            )
            return "Success", "Application Gateway deleted successfully."
        except Exception as e:
            logger.error(
                f"Failed to delete Application Gateway {application_gateway.name}: {e}"
            )
            tc.track_event(
                "ApplicationGatewayDeletionFailed",
                {"ApplicationGatewayName": application_gateway.name, "Error": str(e)},
            )
            status_log.append(
                {
                    "Resource": application_gateway.name,
                    "Action": "delete",
                    "Status": "Failed",
                    "Message": f"Failed to delete Application Gateway: {e}",
                }
            )
            return "Failed", f"Failed to delete Application Gateway: {e}"

def update_storage_account_sku(storage_account, new_sku):
    """Update the SKU of a storage account"""
    try:
        logger.info(f"Updating storage account SKU: {storage_account.name}")
        storage_client.storage_accounts.update(
            resource_group_name=storage_account.id.split("/")[4],
            account_name=storage_account.name,
            parameters={"sku": {"name": new_sku}},
        )
        tc.track_event(
            "StorageAccountSkuUpdated",
            {"StorageAccountName": storage_account.name, "NewSku": new_sku},
        )
        return "Success", f"Storage account SKU updated to {new_sku}."
    except Exception as e:
        logger.error(
            f"Failed to update storage account SKU {storage_account.name}: {e}"
        )
        tc.track_event(
            "StorageAccountSkuUpdateFailed",
            {"StorageAccountName": storage_account.name, "Error": str(e)},
        )
        return "Failed", f"Failed to update storage account SKU: {e}"

def simple_scale_sql_database(
    sql_client, database, new_dtu, min_dtu, max_dtu, dry_run=True
):
    """Simple function to scale a SQL database DTU without any conditions."""
    try:
        current_sku = database.sku
        logger.info(f"Database: {database.name}, Current DTU: {current_sku.capacity}")
        print(f"Database: {database.name}, Current DTU: {current_sku.capacity}")

        if new_dtu == current_sku.capacity:
            logger.info("Current DTU is already optimal.")
            return "No Change", "Current DTU is already optimal."

        if new_dtu < min_dtu:
            new_dtu = min_dtu
        elif new_dtu > max_dtu:
            new_dtu = max_dtu

        resource_group_name = database.id.split("/")[4]
        server_name = database.id.split("/")[8]
        database_name = database.name
        logger.info(f"Scaling SQL database {database.name} to {new_dtu} DTU.")

        valid_dtus = {
            "Basic": [5],
            "Standard": [10, 20, 50, 100, 200, 400, 800, 1600, 3000],
            "Premium": [125, 250, 500, 1000, 1750, 4000],
        }
        if new_dtu not in valid_dtus[current_sku.tier]:
            logger.error(f"DTU {new_dtu} is not valid for tier {current_sku.tier}.")
            return "Error", f"DTU {new_dtu} is not valid for tier {current_sku.tier}."

        new_sku = Sku(name=current_sku.name, tier=current_sku.tier, capacity=new_dtu)
        update_parameters = Database(
            location=database.location, sku=new_sku, min_capacity=new_dtu
        )
        logger.info(f"Update parameters: {update_parameters}")

        if dry_run:
            logger.info("This is a dry run. No changes will be made.")
            return "Dry Run", f"Would scale DTU to {new_dtu}."
        else:
            sql_client.databases.begin_create_or_update(
                resource_group_name, server_name, database_name, update_parameters
            ).result()
            while True:
                database = sql_client.databases.get(
                    resource_group_name, server_name, database_name
                )
                if database.sku.capacity == new_dtu:
                    break
                else:
                    logger.info("Operation in progress...")
                    time.sleep(10)
            logger.info(f"Database {database.name} scaled to {new_dtu} DTU.")
            return "Success", f"Scaled DTU to {new_dtu}."
    except Exception as e:
        logger.error(f"Error scaling SQL database {database.name}: {str(e)}")
        return "Error", str(e)

def scale_sql_database(database, tiers, status_log, dry_run=True, subscription_id=None):
    current_time = datetime.now().time()
    for tier in tiers:
        if tier["name"] in database.sku.name:
            off_peak_start = datetime.strptime(tier["off_peak_start"], "%H:%M").time()
            off_peak_end = datetime.strptime(tier["off_peak_end"], "%H:%M").time()

            if off_peak_start < off_peak_end:
                is_off_peak = off_peak_start <= current_time < off_peak_end
            else:  # Over midnight
                is_off_peak = not (off_peak_end <= current_time < off_peak_start)

            new_dtu = tier["off_peak_dtu"] if is_off_peak else tier["peak_dtu"]

            if new_dtu == database.sku.capacity:
                message = "Current DTU is already optimal. No scaling required."
                logger.info(f"Database: {database.name}, {message}")
                status_log.append(
                    {
                        "SubscriptionId": subscription_id,
                        "Resource": database.name,
                        "Action": "scale",
                        "Status": "No Change",
                        "Message": message,
                    }
                )
                return "No Change", message

            logger.info(
                f"Database: {database.name}, Current DTU: {database.sku.capacity}, New DTU: {new_dtu}"
            )
            message = (
                f"Dry run mode, no action taken. Would scale DTU to {new_dtu}"
                if dry_run
                else f"Scaled DTU to {new_dtu}"
            )
            logger.info(f"Scale status for {database.name}: {message}")
            status_log.append(
                {
                    "SubscriptionId": subscription_id,
                    "Resource": database.name,
                    "Action": "scale",
                    "Status": "Dry Run" if dry_run else "Success",
                    "Message": message,
                }
            )
            if not dry_run:
                simple_scale_sql_database(
                    sql_client,
                    database,
                    new_dtu,
                    tier["min_dtu"],
                    tier["max_dtu"],
                    dry_run,
                )
            return "Success", message
    return "No Change", "Current DTU is already optimal."

def wrap_text(text, width=30):
    """Wrap text to a given width."""
    return "\n".join(textwrap.wrap(text, width))

def review_application_gateways(policies, status_log, dry_run=True):
    impacted_resources = []
    for policy in policies:
        if policy["resource"] == "azure.applicationgateway":
            logger.info(
                "Reviewing application gateways for policy: {}".format(policy["name"])
            )
            gateways = network_client.application_gateways.list_all()
            for gateway in gateways:
                if not gateway.backend_address_pools or any(
                    not pool.backend_addresses for pool in gateway.backend_address_pools
                ):
                    if evaluate_filters(gateway, policy["filters"]):
                        try:
                            status, message = apply_app_gateway_actions(
                                network_client,
                                gateway,
                                policy["actions"],
                                status_log,
                                dry_run,
                            )
                            if status != "No Change":
                                impacted_resources.append(
                                    {
                                        "Policy": policy["name"],
                                        "Resource": gateway.name,
                                        "Actions": ", ".join(
                                            [
                                                action["type"]
                                                for action in policy["actions"]
                                            ]
                                        ),
                                        "Status": status,
                                        "Message": message,
                                    }
                                )
                        except Exception as e:
                            logger.error(f"Failed to apply actions: {e}")
    return impacted_resources

def apply_app_gateway_actions(
    network_client, gateway, actions, status_log, dry_run=True
):
    status = "No Change"
    message = "No applicable actions found"
    for action in actions:
        action_type = action["type"]
        if action_type == "log":
            status, message = log_empty_backend_pool(gateway, dry_run)
        elif action_type == "delete":
            try:
                print(colored(f"Deleting Application Gateway: {gateway.name}", "red"))
                status, message = delete_application_gateway(
                    network_client, gateway, status_log, dry_run
                )
            except Exception as e:
                logger.error(f"Failed to delete application gateway: {e}")
    return status, message

def log_empty_backend_pool(gateway, dry_run=True):
    logger.info(f"Empty backend pool found in Application Gateway: {gateway.name}")
    if dry_run:
        return (
            "Dry Run",
            f"Would log empty backend pool in Application Gateway: {gateway.name}",
        )
    else:
        return (
            "Success",
            f"Logged empty backend pool in Application Gateway: {gateway.name}",
        )

def apply_policies(
    policies,
    dry_run,
    subscription_id,
    impacted_resources,
    non_impacted_resources,
    status_log,
):
    """Apply policies to resources."""

    for policy in policies:
        resource_type = policy["resource"]
        filters = policy["filters"]
        actions = policy["actions"]
        exclusions = policy.get("exclusions", [])

        resources_impacted = (
            False  # Flag to check if any resources are impacted by the policy
        )

        if resource_type == "azure.vm":
            vms = compute_client.virtual_machines.list_all()
            for vm in vms:
                if not evaluate_exclusions(vm, exclusions) and evaluate_filters(
                    vm, filters
                ):
                    apply_actions(vm, actions, status_log, dry_run, subscription_id)
                    impacted_resources.append(
                        {
                            "SubscriptionId": subscription_id,
                            "Policy": policy["name"],
                            "Resource": vm.name,
                            "Actions": ", ".join(
                                [action["type"] for action in actions]
                            ),
                        }
                    )
                    resources_impacted = True
            if not resources_impacted:
                non_impacted_resources.append(
                    {
                        "SubscriptionId": subscription_id,
                        "Policy": policy["name"],
                        "ResourceType": "VM",
                    }
                )

        elif resource_type == "azure.disk":
            disks = compute_client.disks.list()
            for disk in disks:
                logger.info(f"Evaluating disk {disk.name} for deletion.")
                if not evaluate_exclusions(disk, exclusions) and evaluate_filters(
                    disk, filters
                ):
                    apply_actions(disk, actions, status_log, dry_run, subscription_id)
                    impacted_resources.append(
                        {
                            "SubscriptionId": subscription_id,
                            "Policy": policy["name"],
                            "Resource": disk.name,
                            "Actions": ", ".join(
                                [action["type"] for action in actions]
                            ),
                        }
                    )
                    resources_impacted = True
            if not resources_impacted:
                non_impacted_resources.append(
                    {
                        "SubscriptionId": subscription_id,
                        "Policy": policy["name"],
                        "ResourceType": "Disk",
                    }
                )

        elif resource_type == "azure.resourcegroup":
            resource_groups = resource_client.resource_groups.list()
            for resource_group in resource_groups:
                if not evaluate_exclusions(
                    resource_group, exclusions
                ) and evaluate_filters(resource_group, filters):
                    apply_actions(
                        resource_group, actions, status_log, dry_run, subscription_id
                    )
                    impacted_resources.append(
                        {
                            "SubscriptionId": subscription_id,
                            "Policy": policy["name"],
                            "Resource": resource_group.name,
                            "Actions": ", ".join(
                                [action["type"] for action in actions]
                            ),
                        }
                    )
                    resources_impacted = True
            if not resources_impacted:
                non_impacted_resources.append(
                    {
                        "SubscriptionId": subscription_id,
                        "Policy": policy["name"],
                        "ResourceType": "Resource Group",
                    }
                )

        elif resource_type == "azure.storage":
            storage_accounts = storage_client.storage_accounts.list()
            for storage_account in storage_accounts:
                if not evaluate_exclusions(
                    storage_account, exclusions
                ) and evaluate_filters(storage_account, filters):
                    apply_actions(
                        storage_account, actions, status_log, dry_run, subscription_id
                    )
                    impacted_resources.append(
                        {
                            "SubscriptionId": subscription_id,
                            "Policy": policy["name"],
                            "Resource": storage_account.name,
                            "Actions": ", ".join(
                                [action["type"] for action in actions]
                            ),
                        }
                    )
                    resources_impacted = True
            if not resources_impacted:
                non_impacted_resources.append(
                    {
                        "SubscriptionId": subscription_id,
                        "Policy": policy["name"],
                        "ResourceType": "Storage Account",
                    }
                )

        elif resource_type == "azure.publicip":
            public_ips = network_client.public_ip_addresses.list_all()
            for public_ip in public_ips:
                if not evaluate_exclusions(public_ip, exclusions) and evaluate_filters(
                    public_ip, filters
                ):
                    apply_actions(
                        public_ip, actions, status_log, dry_run, subscription_id
                    )
                    impacted_resources.append(
                        {
                            "SubscriptionId": subscription_id,
                            "Policy": policy["name"],
                            "Resource": public_ip.name,
                            "Actions": ", ".join(
                                [action["type"] for action in actions]
                            ),
                        }
                    )
                    resources_impacted = True

            if not resources_impacted:
                non_impacted_resources.append(
                    {
                        "SubscriptionId": subscription_id,
                        "Policy": policy["name"],
                        "ResourceType": "Public IP",
                    }
                )

        elif resource_type == "azure.sql":
            servers = sql_client.servers.list()
            for server in servers:
                resource_group_name = server.id.split("/")[4]
                databases = sql_client.databases.list_by_server(
                    resource_group_name, server.name
                )
                for db in databases:
                    logger.info(f"Database: {db.name}, Current DTU: {db.sku.capacity}")
                    status, message = scale_sql_database(
                        db,
                        policy["actions"][0]["tiers"],
                        status_log,
                        dry_run,
                        subscription_id,
                    )
                    if status != "No Change":
                        impacted_resources.append(
                            {
                                "SubscriptionId": subscription_id,
                                "Policy": policy["name"],
                                "Resource": db.name,
                                "Actions": "scale",
                                "Status": status,
                                "Message": message,
                            }
                        )
                        resources_impacted = True
            if not resources_impacted:
                non_impacted_resources.append(
                    {
                        "SubscriptionId": subscription_id,
                        "Policy": policy["name"],
                        "ResourceType": "SQL Database",
                    }
                )

        elif resource_type == "azure.applicationgateway":
            policy_results = review_application_gateways(
                [policy], status_log, dry_run=dry_run
            )
            impacted_resources.extend(
                [{"SubscriptionId": subscription_id, **res} for res in policy_results]
            )
            if policy_results:
                resources_impacted = True
            else:
                non_impacted_resources.append(
                    {
                        "SubscriptionId": subscription_id,
                        "Policy": policy["name"],
                        "ResourceType": "Application Gateway",
                    }
                )
        elif resource_type == "azure.nic":
            nics = network_client.network_interfaces.list_all()
            for nic in nics:
                if not evaluate_exclusions(nic, exclusions) and evaluate_filters(nic, filters):
                    apply_actions(nic, actions, status_log, dry_run, subscription_id)
                    impacted_resources.append(
                        {
                            "SubscriptionId": subscription_id,
                            "Policy": policy["name"],
                            "Resource": nic.name,
                            "Actions": ", ".join([action["type"] for action in actions]),
                        }
                    )
                    resources_impacted = True
            if not resources_impacted:
                non_impacted_resources.append(
                    {
                        "SubscriptionId": subscription_id,
                        "Policy": policy["name"],
                        "ResourceType": "Network Interface",
                    }
                )

def process_subscription(subscription, mode, summary_reports, impacted_resources, non_impacted_resources, status_log, start_date, end_date, use_adls=False):
    global resource_client, cost_management_client, compute_client, storage_client, network_client, sql_client
    
    subscription_id = subscription.subscription_id
    resource_client = ResourceManagementClient(credential, subscription_id)
    cost_management_client = CostManagementClient(credential)
    compute_client = ComputeManagementClient(credential, subscription_id)
    storage_client = StorageManagementClient(credential, subscription_id)
    network_client = NetworkManagementClient(credential, subscription_id)
    sql_client = SqlManagementClient(credential, subscription_id)

    logger.info(f'Processing subscription: {subscription_id}')
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

        return {}
    except Exception as e:
        logger.error(f"Error in subscription {subscription_id}: {e}")
        tc.track_exception()
        tc.flush()
        return {}

def main(mode, all_subscriptions, use_adls=False):
    logger.info('Cost Optimizer Function triggered.')
    tc.track_event("FunctionTriggered")

    summary_reports = []
    impacted_resources = []
    non_impacted_resources = []
    status_log = []

    # Define the start and end dates for the past 30 days
    cet = pytz.timezone("CET")
    now_cet = datetime.now(cet)
    start_date = (now_cet - timedelta(days=30)).strftime('%Y-%m-%dT%H:%M:%SZ')
    end_date = now_cet.strftime('%Y-%m-%dT%H:%M:%SZ')

    try:
        if all_subscriptions:
            subscriptions = subscription_client.subscriptions.list()
            for subscription in subscriptions:
                subscription_id = subscription.subscription_id
                process_subscription(subscription, mode, summary_reports, impacted_resources, non_impacted_resources, status_log, start_date, end_date, use_adls)
        else:
            subscription_id = os.getenv('AZURE_SUBSCRIPTION_ID')
            subscription = subscription_client.subscriptions.get(subscription_id)
            process_subscription(subscription, mode, summary_reports, impacted_resources, non_impacted_resources, status_log, start_date, end_date, use_adls)

        if impacted_resources:
            table_impacted_resources = PrettyTable()
            table_impacted_resources.field_names = ["Subscription ID", "Policy", "Resource", "Actions"]
            for resource in impacted_resources:
                table_impacted_resources.add_row([resource["SubscriptionId"], resource["Policy"], wrap_text(resource["Resource"]), resource["Actions"]])
            print(colored("Impacted Resources:", "cyan", attrs=["bold"]))
            print(colored(table_impacted_resources.get_string(), "cyan"))

        if non_impacted_resources:
            table_non_impacted_resources = PrettyTable()
            table_non_impacted_resources.field_names = ["Subscription ID", "Policy", "ResourceType"]
            for resource in non_impacted_resources:
                table_non_impacted_resources.add_row([resource["SubscriptionId"], resource["Policy"], resource["ResourceType"]])
            print(colored("Non-Impacted Resources:", "cyan", attrs=["bold"]))
            print(colored(table_non_impacted_resources.get_string(), "cyan"))

        if status_log:
            table_status_log = PrettyTable()
            table_status_log.field_names = ["Subscription ID", "Resource", "Action", "Status", "Message"]
            for status in status_log:
                table_status_log.add_row([status["SubscriptionId"], wrap_text(status["Resource"]), status["Action"], status["Status"], wrap_text(status["Message"])])
            print(colored("Action Status Log:", "cyan", attrs=["bold"]))
            print(colored(table_status_log.get_string(), "cyan"))

    except KeyError as e:
        logger.error(f"KeyError: {e}")
    except Exception as e:
        logger.error(f"An unexpected error occurred: {e}")

    logger.info("Azure Cost Optimizer Tool completed!")

if __name__ == "__main__":
    print(
        colored(
            r""" _______                            _______                    _______            _       _                   
(_______)                          (_______)            _     (_______)       _  (_)     (_)                  
 _______ _____ _   _  ____ _____    _       ___   ___ _| |_    _     _ ____ _| |_ _ ____  _ _____ _____  ____ 
|  ___  (___  ) | | |/ ___) ___ |  | |     / _ \ /___|_   _)  | |   | |  _ (_   _) |    \| (___  ) ___ |/ ___)
| |   | |/ __/| |_| | |   | ____|  | |____| |_| |___ | | |_   | |___| | |_| || |_| | | | | |/ __/| ____| |    
|_|   |_(_____)____/|_|   |_____)   \______)___/(___/   \__)   \_____/|  __/  \__)_|_|_|_|_(_____)_____)_|    
                                                                      |_|                                     
    """,
            "light_blue",
        )
    )

    print(colored("Running Azure Cost Optimizer Tool...", "black"))
    print(colored("Please wait...", "black"))
    for i in range(10):
        time.sleep(0.2)
    print(colored("Azure Cost Optimizer Tool is ready!", "green"))
    print(colored("=" * 110, "black"))
    parser = argparse.ArgumentParser(description="Azure Cost Optimization Tool")
    parser.add_argument(
        "--mode",
        choices=["dry-run", "apply"],
        required=True,
        help="Mode to run the function (dry-run or apply)",
    )
    parser.add_argument(
        "--all-subscriptions",
        action="store_true",
        help="Process all subscriptions in the tenant",
    )
    parser.add_argument(
        "--use-adls",
        action="store_true",
        help="Use Azure Data Lake Storage for waste cost data",
    )
    args = parser.parse_args()
    main(args.mode, args.all_subscriptions, args.use_adls)
    print(colored("Azure Cost Optimizer Tool completed!", "green"))
    print(colored("=" * 110, "black"))
