import argparse
import logging
import os
import sys
import time
from datetime import datetime, timedelta, timezone
import json
import yaml
import jsonschema
import pandas as pd
import matplotlib.pyplot as plt
from dotenv import load_dotenv
from prettytable import PrettyTable
from termcolor import colored
from sklearn.ensemble import IsolationForest  # type: ignore
import textwrap
from collections import defaultdict
import pytz
import io
from functools import wraps
from azure.identity import DefaultAzureCredential
from azure.mgmt.resource import ResourceManagementClient
from azure.mgmt.costmanagement import CostManagementClient
from azure.mgmt.compute import ComputeManagementClient
from azure.mgmt.storage import StorageManagementClient
from azure.mgmt.network import NetworkManagementClient
from azure.mgmt.sql import SqlManagementClient
from azure.mgmt.subscription import SubscriptionClient
from azure.mgmt.monitor import MonitorManagementClient
from azure.mgmt.sql.models import Sku, Database
from azure.storage.filedatalake import DataLakeServiceClient
from applicationinsights import TelemetryClient
from azure.mgmt.compute.models import StorageAccountTypes
import matplotlib.pyplot as plt


# Set up logging
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

from azure.identity import ClientSecretCredential

def get_client_credentials(tenant_id: str):
    """Return credentials for the given tenant ID."""
    client_id = os.getenv("AZURE_CLIENT_ID")
    client_secret = os.getenv("AZURE_CLIENT_SECRET")
    if not (client_id and client_secret):
        raise ValueError("Azure client credentials are not set.")
    return ClientSecretCredential(tenant_id=tenant_id, client_id=client_id, client_secret=client_secret)

def get_subscription_client(tenant_id: str):
    """Return a SubscriptionClient for the given tenant."""
    credential = get_client_credentials(tenant_id)
    return SubscriptionClient(credential)

# Clients
subscription_client = SubscriptionClient(credential)
monitor_client = MonitorManagementClient(
    credential, subscription_id=subscription_client
)

# Verify that the necessary environment variables are set and log their values
required_env_vars = [
    "AZURE_CLIENT_ID",
    "AZURE_TENANT_ID",
    "AZURE_CLIENT_SECRET",
    "AZURE_SUBSCRIPTION_ID",
]
for var in required_env_vars:
    value = os.getenv(var)
    if not value:
        logger.error(f"Environment variable {var} is not set.")
        sys.exit(1)
    logger.info(f"{var}: {value}")


def retry(max_retries=3, delay=5, backoff=2, jitter=True, exceptions=(Exception,)):
    """Retry decorator with exponential backoff and optional jitter."""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            retries = 0
            current_delay = delay
            while retries < max_retries:
                try:
                    return func(*args, **kwargs)
                except exceptions as e:
                    retries += 1
                    sleep_time = current_delay * (1 + (0.5 if jitter else 0))
                    logger.warning(f"Exception occurred: {e}. Retrying in {sleep_time:.2f} seconds...")
                    time.sleep(sleep_time)
                    current_delay *= backoff
            raise
        return wrapper
    return decorator


def load_policies(policy_file, schema_file):
    """Load and validate policies from the YAML file against the schema."""
    with open(policy_file, "r") as file:
        policies = yaml.safe_load(file)
    logger.info(
        f"Loaded {len(policies.get('policies', []))} policies from {policy_file}"
    )

    with open(schema_file, "r") as file:
        schema = json.load(file)
    logger.info(f"Validating policies against the schema from {schema_file}")

    try:
        jsonschema.validate(instance=policies, schema=schema)
        logger.info("Policy validation successful.")
    except jsonschema.exceptions.ValidationError as e:
        logger.error(f"Policy validation failed: {e.message}")
        raise

    enabled_policies = [
        policy
        for policy in policies.get("policies", [])
        if policy.get("enabled", False)
    ]
    logger.info(f"Returning {len(enabled_policies)} enabled policies.")
    return enabled_policies


@retry(max_retries=5, delay=10, backoff=2, exceptions=(Exception,))
def get_cost_data(scope):
    """Retrieve cost data from Azure."""
    try:
        logger.info(f"Retrieving cost data for scope: {scope}")

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
    try:
        df = preprocess_cost_data(cost_data, subscription_id)
        log_daily_metrics(df)

        trend_data = trend_analysis(df, subscription_id)
        anomalies = detect_anomalies_isolation_forest(df, subscription_id)
        generate_summary_report(df, subscription_id, summary_reports)

        return trend_data, anomalies
    except Exception as e:
        logger.error(f"Error analyzing cost data for subscription {subscription_id}: {e}")
        return [], []

def preprocess_cost_data(cost_data, subscription_id):
    """Preprocess cost data and convert to a DataFrame."""
    cet = pytz.timezone("CET")
    now_cet = datetime.now(cet)

    data = [
        {"date": pd.to_datetime(str(item[1]), format="%Y%m%d").tz_localize("UTC").tz_convert(cet), 
         "cost": item[0], 
         "SubscriptionId": subscription_id}
        for item in cost_data.rows
        if pd.to_datetime(str(item[1]), format="%Y%m%d").tz_localize("UTC").tz_convert(cet).date() < now_cet.date()
    ]

    if not data:
        logger.warning(f"No valid cost data found for subscription {subscription_id}.")
        return pd.DataFrame()

    df = pd.DataFrame(data)
    df.set_index("date", inplace=True)
    df = df.asfreq("D")  # Ensure daily frequency

    # Fill missing or NaN values
    df["cost"] = df["cost"].fillna(0)  # Replace NaN with 0 or a default value
    df["SubscriptionId"] = df["SubscriptionId"].fillna(subscription_id)  # Replace NaN with the subscription ID

    return df

def log_daily_metrics(df):
    """Log daily metrics from the cost data."""
    for date, row in df.iterrows():
        logger.info(f"Date: {date.date()}, Cost: {row['cost']}")
        tc.track_metric("DailyCost", row["cost"], properties={"Date": date.date().isoformat()})

def trend_analysis(df, subscription_id):
    """Analyze cost trends over time and plot the trend."""
    if df.empty:
        logger.warning(f"No data available for trend analysis for subscription {subscription_id}.")
        return []

    try:
        trend_data = df.reset_index().to_dict(orient="records")
        
        plt.figure(figsize=(10, 5))
        df["cost"].plot(title=f"Cost Trend Over Time for Subscription {subscription_id}")
        plt.xlabel("Date")
        plt.ylabel("Cost")
        plot_file = f"cost_trend_{subscription_id}.png"
        plt.savefig(plot_file)
        plt.close()

        logger.info(f"Trend analysis plot saved as {plot_file}.")
        tc.track_event("TrendAnalysisCompleted", {"SubscriptionId": subscription_id})
        return trend_data
    except Exception as e:
        logger.error(f"Error generating trend analysis for subscription {subscription_id}: {e}")
        return []

# def detect_anomalies_isolation_forest(df, subscription_id):
#     """Detect anomalies in the cost data using Isolation Forest."""
#     model = IsolationForest(contamination=0.025)
#     df["anomaly"] = model.fit_predict(df[["cost"]])
#     anomalies = df[df["anomaly"] == -1]
#     anomaly_list = []

#     if not anomalies.empty:
#         for _, row in anomalies.iterrows():
#             tc.track_event(
#                 "AnomalyDetectedIsolationForest",
#                 {
#                     "SubscriptionId": subscription_id,
#                     "Date": row.name.date().isoformat(),
#                     "Cost": row["cost"],
#                 },
#             )
#             table = PrettyTable()
#             table.field_names = ["Subscription ID", "Anomaly Detected", "Date", "Cost"]
#             table.add_row(
#                 [
#                     subscription_id,
#                     "Isolation Forest Algorithm",
#                     row.name.date().isoformat(),
#                     f'{row["cost"]:.2f}',
#                 ]
#             )
#             print(colored(table, "red"))
#     else:
#         logger.info(
#             f"No anomalies detected in cost data for subscription {subscription_id} using Isolation Forest."
#         )
#         tc.track_event(
#             "NoAnomaliesDetectedIsolationForest", {"SubscriptionId": subscription_id}
#         )
#     return anomaly_list

def detect_anomalies_isolation_forest(df, subscription_id):
    """Detect anomalies in the cost data using Isolation Forest."""
    model = IsolationForest(contamination=0.025)
    df["anomaly"] = model.fit_predict(df[["cost"]])
    anomalies = df[df["anomaly"] == -1]
    anomaly_list = []

    if not anomalies.empty:
        for _, row in anomalies.iterrows():
            anomaly_data = {
                "SubscriptionId": subscription_id,
                "Date": row.name.date().isoformat(),
                "Cost": round(row["cost"], 2),
                "Algorithm": "Isolation Forest",
            }
            anomaly_list.append(anomaly_data)

            # Tracking the event
            tc.track_event(
                "AnomalyDetectedIsolationForest",
                anomaly_data,
            )
    else:
        logger.info(
            f"No anomalies detected in cost data for subscription {subscription_id} using Isolation Forest."
        )
        tc.track_event(
            "NoAnomaliesDetectedIsolationForest", {"SubscriptionId": subscription_id}
        )

    # Return the anomalies as JSON-compatible list of dictionaries
    return anomaly_list

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
            days = filter["days"]
            threshold = filter.get("threshold", 10)
            if not last_used_filter(resource, days, threshold):
                logger.info(
                    f"Resource {resource.name} does not meet last_used filter with threshold {threshold}"
                )
                return False
        elif filter_type == "unattached":
            if not unattached_filter(resource):
                logger.info(f"Resource {resource.name} does not meet unattached filter")
                return False
        elif filter_type == "tag":
            if not tag_filter(resource, filter["key"], filter["value"]):
                logger.info(f"Resource {resource.name} does not meet tag filter")
                return False
        elif filter_type == "sku":
            if not sku_filter(resource, filter["values"]):
                logger.info(f"Resource {resource.name} does not meet sku filter")
                return False
        elif filter_type == "stopped":
            if not is_vm_stopped(resource):
                logger.info(f"Resource {resource.name} is not stopped (deallocated)")
                return False
    logger.info(f"Resource {resource.name} meets all filters")
    return True


def is_vm_stopped(vm):
    """Check if a VM is stopped (deallocated)."""
    resource_group_name = vm.id.split("/")[4]
    vm_instance_view = compute_client.virtual_machines.instance_view(
        resource_group_name, vm.name
    )
    statuses = vm_instance_view.statuses
    return any(status.code == "PowerState/deallocated" for status in statuses)


def evaluate_exclusions(resource, exclusions):
    """Evaluate if a resource meets any of the exclusion criteria."""
    for exclusion in exclusions:
        exclusion_type = exclusion["type"]
        if exclusion_type == "tag":
            if tag_filter(resource, exclusion["key"], exclusion["value"]):
                return True
    return False


def last_used_filter(resource, days, threshold):
    """Check if a resource was last used within a specified number of days and meets the CPU threshold."""
    last_used_date, avg_cpu = get_last_used_date(resource, days, threshold)
    print(f"last_used_date: {last_used_date}, avg_cpu: {avg_cpu}")  # Debug statement

    if (
        datetime.now(timezone.utc) - last_used_date
    ).days <= days and avg_cpu < threshold:
        logger.info(
            f"Resource {resource.name} was last used within {days} days with average CPU usage {avg_cpu:.2f}% which is below the threshold of {threshold}%."
        )
        return True
    logger.info(
        f"Resource {resource.name} was either not used within {days} days or its average CPU usage {avg_cpu:.2f}% is above the threshold of {threshold}%."
    )
    return False


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
    elif isinstance(
        resource, network_client.network_interfaces.models.NetworkInterface
    ):
        # Check if the NIC is attached to a private endpoint
        if resource.private_endpoint:
            logger.info(
                f"NIC {resource.name} is attached to a private endpoint and will not be deleted."
            )
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


def get_last_used_date(resource, days, threshold=5):
    """
    Get the last used date of a VM based on average CPU usage over a specified number of days.

    Parameters:
    - resource: The VM resource object.
    - days: The number of days to check for activity.
    - threshold: The CPU usage threshold below which the VM is considered as not used (in percentage).

    Returns:
    - A tuple of (last used date, average CPU usage).
    """
    resource_id = resource.id
    end_time = (
        datetime.now(timezone.utc)
        .replace(microsecond=0)
        .isoformat()
        .replace("+00:00", "Z")
    )
    start_time = (
        (datetime.now(timezone.utc) - timedelta(days=days))
        .replace(microsecond=0)
        .isoformat()
        .replace("+00:00", "Z")
    )

    # Initialize monitor client
    monitor_client = MonitorManagementClient(credential, resource_id.split("/")[2])

    # Format timespan in ISO 8601 format
    timespan = f"{start_time}/{end_time}"

    # Query CPU usage metrics
    metrics_data = monitor_client.metrics.list(
        resource_id,
        timespan=timespan,
        interval="PT1H",
        metricnames="Percentage CPU",
        aggregation="Average",
    )

    cpu_usages = [
        data.average
        for metric in metrics_data.value
        for data in metric.timeseries[0].data
        if data.average is not None
    ]

    if not cpu_usages:
        logger.info(
            f"No CPU usage data available for VM: {resource.name} in the last {days} days."
        )
        return (
            datetime.fromisoformat(start_time.replace("Z", "+00:00")),
            0.0,
        )  # Return a tuple with default CPU usage

    # Log CPU usage data for debugging purposes
    logger.info(
        f"CPU usage data for VM: {resource.name} in the last {days} days: {cpu_usages}"
    )

    # Check if the average CPU usage is below the threshold
    average_cpu_usage = sum(cpu_usages) / len(cpu_usages)
    logger.info(f"Average CPU usage for VM: {resource.name}: {average_cpu_usage:.2f}%")

    if average_cpu_usage < threshold:
        return (
            datetime.fromisoformat(start_time.replace("Z", "+00:00")),
            average_cpu_usage,
        )

    # If the VM was used, find the last time it was above the threshold
    for data in reversed(metrics_data.value[0].timeseries[0].data):
        if data.average and data.average >= threshold:
            return data.time_stamp, average_cpu_usage

    # If all CPU usage values are below the threshold, return the start_time
    return datetime.fromisoformat(start_time.replace("Z", "+00:00")), average_cpu_usage


def apply_actions(resource, actions, status_log, dry_run, subscription_id):
    """Apply actions to a resource and include cost data."""
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
                logger.info(
                    f"Action stop applied to VM {resource.name} with status: {status}"
                )
            elif action_type == "downgrade_disks":
                if isinstance(
                    resource, compute_client.virtual_machines.models.VirtualMachine
                ):
                    status, message = downgrade_disks_of_vm(
                        resource, status_log, dry_run, subscription_id
                    )
                elif isinstance(resource, compute_client.disks.models.Disk):
                    status, message = downgrade_disk(resource)
                status_log.append(
                    {
                        "SubscriptionId": subscription_id,
                        "Resource": resource.name,
                        "Action": "downgrade_disks",
                        "Status": status,
                        "Message": message,
                    }
                )
                logger.info(
                    f"Action downgrade_disks applied to {resource.name} with status: {status} and message: {message}"
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
                    logger.info(
                        f"Action delete applied to Disk {resource.name} with status: {status} and message: {message}"
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
                    logger.info(
                        f"Action delete applied to Resource Group {resource.name} with status: {status} and message: {message}"
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
                    logger.info(
                        f"Action delete applied to Public IP {resource.name} with status: {status} and message: {message}"
                    )
                elif isinstance(
                    resource, network_client.network_interfaces.models.NetworkInterface
                ):
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
                    logger.info(
                        f"Action delete applied to Network Interface {resource.name} with status: {status} and message: {message}"
                    )
                elif isinstance(
                    resource,
                    network_client.application_gateways.models.ApplicationGateway,
                ):
                    status, message = delete_application_gateway(
                        network_client, resource, status_log, dry_run
                    )
                    logger.info(
                        f"Action delete applied to Application Gateway {resource.name} with status: {status} and message: {message}"
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
                    logger.info(
                        f"Action update_sku applied to Storage Account {resource.name} with status: {status} and message: {message}"
                    )
            elif action_type == "scale_sql_database":
                status, message = scale_sql_database(
                    resource, action["tiers"], status_log, dry_run, subscription_id
                )
                logger.info(
                    f"Action scale_sql_database applied to SQL Database {resource.name} with status: {status} and message: {message}"
                )


def delete_network_interface(nic):
    """Delete an unattached network interface."""
    try:
        logger.info(f"Deleting Network Interface: {nic.name}")
        resource_group_name = nic.id.split("/")[4]
        async_delete = network_client.network_interfaces.begin_delete(
            resource_group_name, nic.name
        )
        async_delete.result()
        tc.track_event("NetworkInterfaceDeleted", {"NetworkInterfaceName": nic.name})
        return "Success", "Network Interface deleted successfully."
    except Exception as e:
        logger.error(f"Failed to delete Network Interface {nic.name}: {e}")
        tc.track_event(
            "NetworkInterfaceDeletionFailed",
            {"NetworkInterfaceName": nic.name, "Error": str(e)},
        )
        return "Failed", f"Failed to delete Network Interface: {e}"


def stop_vm(vm):
    """Stop a VM."""
    try:
        logger.info(f"Checking status of VM: {vm.name}")
        resource_group_name = vm.id.split("/")[4]
        instance_view = compute_client.virtual_machines.instance_view(
            resource_group_name, vm.name
        )
        statuses = instance_view.statuses
        for status in statuses:
            if "PowerState" in status.code and "deallocated" in status.code:
                message = f"VM {vm.name} is already deallocated."
                logger.info(message)
                tc.track_event("VMAlreadyDeallocated", {"VMName": vm.name})
                return "No Action", message
        async_stop = compute_client.virtual_machines.begin_deallocate(
            resource_group_name, vm.name
        )
        async_stop.result()
        tc.track_event("VMDeallocated", {"VMName": vm.name})
        return "Success", f"VM deallocated successfully."
    except Exception as e:
        logger.error(f"Failed to deallocate VM {vm.name}: {e}")
        tc.track_event("VMDeallocateFailed", {"VMName": vm.name, "Error": str(e)})
        return "Failed", f"Failed to deallocate VM: {e}"


def downgrade_disk(disk):
    """Downgrade a disk to Standard_LRS."""
    resource_group_name = disk.id.split("/")[4]
    disk_name = disk.name

    try:
        if disk.sku.name != StorageAccountTypes.standard_lrs:
            disk.sku.name = StorageAccountTypes.standard_lrs
            async_update = compute_client.disks.begin_create_or_update(
                resource_group_name, disk_name, disk
            )
            async_update.result()
            updated_disk = compute_client.disks.get(resource_group_name, disk_name)
            if updated_disk.sku.name == StorageAccountTypes.standard_lrs:
                logger.info(f"Successfully downgraded disk {disk_name} to Standard_LRS")
                return (
                    "Success",
                    f"Successfully downgraded disk {disk_name} to Standard_LRS",
                )
            else:
                logger.error(
                    f"Failed to downgrade disk {disk_name}. Current SKU: {updated_disk.sku.name}"
                )
                return (
                    "Failed",
                    f"Failed to downgrade disk {disk_name}. Current SKU: {updated_disk.sku.name}",
                )
        else:
            logger.info(f"Disk {disk_name} is already {disk.sku.name}")
            return "No Action", f"Disk {disk_name} is already {disk.sku.name}"

    except Exception as e:
        logger.error(f"Failed to downgrade disk {disk_name}: {e}")
        return "Failed", f"Failed to downgrade disk {disk_name}: {e}"


def is_vm_deallocated(vm):
    """Check if a VM is deallocated."""
    resource_group_name = vm.id.split("/")[4]
    vm_instance_view = compute_client.virtual_machines.instance_view(
        resource_group_name, vm.name
    )
    statuses = vm_instance_view.statuses
    return any(status.code == "PowerState/deallocated" for status in statuses)


def downgrade_disks_of_vm(vm, status_log, dry_run=True, subscription_id=None):
    """Downgrade disks of a VM."""
    try:
        resource_group_name = vm.id.split("/")[4]
        vm_instance = compute_client.virtual_machines.get(
            resource_group_name, vm.name, expand="instanceView"
        )

        # Process the OS disk
        os_disk = vm_instance.storage_profile.os_disk
        if os_disk.managed_disk:
            os_disk_id = os_disk.managed_disk.id
            os_disk_name = os_disk_id.split("/")[-1]
            os_disk_rg = os_disk_id.split("/")[4]
            logger.info(
                f"Processing OS disk {os_disk_name} with ID {os_disk_id} in RG {os_disk_rg}"
            )
            try:
                managed_disk = compute_client.disks.get(os_disk_rg, os_disk_name)
                if dry_run:
                    log_entry = {
                        "SubscriptionId": subscription_id,
                        "Resource": managed_disk.name,
                        "Action": "downgrade_disks",
                        "Status": "Dry Run",
                        "Message": f"Would downgrade OS disk {managed_disk.name} to Standard_LRS",
                    }
                    status_log.append(log_entry)
                else:
                    status, message = downgrade_disk(managed_disk)
                    log_entry = {
                        "SubscriptionId": subscription_id,
                        "Resource": managed_disk.name,
                        "Action": "downgrade_disks",
                        "Status": status,
                        "Message": message,
                    }
                    status_log.append(log_entry)
            except Exception as e:
                log_entry = {
                    "SubscriptionId": subscription_id,
                    "Resource": os_disk_name,
                    "Action": "downgrade_disks",
                    "Status": "Failed",
                    "Message": f"Failed to downgrade OS disk {os_disk_name} for VM {vm.name}: {e}",
                }
                status_log.append(log_entry)
                logger.error(
                    f"Failed to downgrade OS disk {os_disk_name} for VM {vm.name}: {e}"
                )

        # Process the data disks
        for disk in vm_instance.storage_profile.data_disks:
            if disk.managed_disk:
                data_disk_id = disk.managed_disk.id
                data_disk_name = data_disk_id.split("/")[-1]
                data_disk_rg = data_disk_id.split("/")[4]
                logger.info(
                    f"Processing data disk {data_disk_name} with ID {data_disk_id} in RG {data_disk_rg}"
                )
                try:
                    managed_disk = compute_client.disks.get(
                        data_disk_rg, data_disk_name
                    )
                    if dry_run:
                        log_entry = {
                            "SubscriptionId": subscription_id,
                            "Resource": managed_disk.name,
                            "Action": "downgrade_disks",
                            "Status": "Dry Run",
                            "Message": f"Would downgrade data disk {managed_disk.name} to Standard_LRS",
                        }
                        status_log.append(log_entry)
                    else:
                        status, message = downgrade_disk(managed_disk)
                        log_entry = {
                            "SubscriptionId": subscription_id,
                            "Resource": managed_disk.name,
                            "Action": "downgrade_disks",
                            "Status": status,
                            "Message": message,
                        }
                        status_log.append(log_entry)
                except Exception as e:
                    log_entry = {
                        "SubscriptionId": subscription_id,
                        "Resource": data_disk_name,
                        "Action": "downgrade_disks",
                        "Status": "Failed",
                        "Message": f"Failed to downgrade data disk {data_disk_name} for VM {vm.name}: {e}",
                    }
                    status_log.append(log_entry)
                    logger.error(
                        f"Failed to downgrade data disk {data_disk_name} for VM {vm.name}: {e}"
                    )
        return "Success", "Disk downgrades processed."
    except Exception as e:
        log_entry = {
            "SubscriptionId": subscription_id,
            "Resource": vm.name,
            "Action": "downgrade_disks",
            "Status": "Failed",
            "Message": f"Failed to process disks for VM {vm.name}: {e}",
        }
        status_log.append(log_entry)
        logger.error(f"Failed to process disks for VM {vm.name}: {e}")
        return "Failed", f"Failed to process disks for VM {vm.name}: {e}"


def delete_disk(disk):
    """Delete a disk."""
    try:
        logger.info(f"Attempting to delete disk: {disk.name}")
        resource_group_name = disk.id.split("/")[4]
        logger.info(f"Disk resource group: {resource_group_name}")
        logger.info(f"Disk details: {disk}")
        async_delete = compute_client.disks.begin_delete(resource_group_name, disk.name)
        async_delete.result()
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
            logger.info("Deleting resource group, please wait...")
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
        async_delete.result()
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
                "Cost": 0,
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
                    "Cost": 0,
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
                    "Cost": 0,
                }
            )
            return "Failed", f"Failed to delete Application Gateway: {e}"


def update_storage_account_sku(storage_account, new_sku):
    """Update the SKU of a storage account."""
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
    """Scale a SQL database."""
    current_time = datetime.now().time()
    for tier in tiers:
        if tier["name"] in database.sku.name:
            # Check if off_peak_start and off_peak_end are provided
            off_peak_start = tier.get("off_peak_start")
            off_peak_end = tier.get("off_peak_end")

            # Default to off-peak DTU if no schedule is specified
            if off_peak_start is None or off_peak_end is None:
                new_dtu = tier["off_peak_dtu"]
            else:
                # Parse the off-peak times if provided
                off_peak_start = datetime.strptime(off_peak_start, "%H:%M").time()
                off_peak_end = datetime.strptime(off_peak_end, "%H:%M").time()

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
                        "Cost": 0,
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
                    "Cost": 0,
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
    """Review application gateways."""
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
                                        "Cost": 0,
                                    }
                                )
                        except Exception as e:
                            logger.error(f"Failed to apply actions: {e}")
    return impacted_resources


def apply_app_gateway_actions(
    network_client, gateway, actions, status_log, dry_run=True
):
    """Apply actions to an application gateway."""
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
    """Log empty backend pool."""
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


def evaluate_unattached_filter(disk):
    """Check if a disk is unattached."""
    if not disk.managed_by:
        logger.info(f"Disk {disk.name} is unattached.")
        return True
    logger.info(f"Disk {disk.name} is attached.")
    return False


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

        resources_impacted = False

        if resource_type == "azure.vm":
            vms = compute_client.virtual_machines.list_all()
            for vm in vms:
                logger.info(f"Evaluating VM {vm.name}")
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
                logger.info(f"Evaluating disk {disk.name}")
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
                if not evaluate_exclusions(nic, exclusions) and evaluate_filters(
                    nic, filters
                ):
                    apply_actions(nic, actions, status_log, dry_run, subscription_id)
                    impacted_resources.append(
                        {
                            "SubscriptionId": subscription_id,
                            "Policy": policy["name"],
                            "Resource": nic.name,
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
                        "ResourceType": "Network Interface",
                    }
                )


def process_subscription(
    subscription,
    tenant_id,
    mode,
    summary_reports,
    impacted_resources,
    non_impacted_resources,
    status_log,
    start_date,
    end_date,
):
    """Process a subscription."""
    global resource_client, cost_management_client, compute_client, storage_client, network_client, sql_client

    subscription_id = subscription.subscription_id
    resource_client = ResourceManagementClient(credential, subscription_id)
    cost_management_client = CostManagementClient(credential)
    compute_client = ComputeManagementClient(credential, subscription_id)
    storage_client = StorageManagementClient(credential, subscription_id)
    network_client = NetworkManagementClient(credential, subscription_id)
    sql_client = SqlManagementClient(credential, subscription_id)

    logger.info(f"Processing subscription: {subscription_id}")
    tc.track_event("SubscriptionProcessingStarted", {"SubscriptionId": subscription_id})

    trend_data = []
    anomalies = []

    try:
        policy_file = config["policies"]["policy_file"]
        schema_file = config["policies"]["schema_file"]
        policies = load_policies(policy_file, schema_file)
        cost_data = get_cost_data(f"/subscriptions/{subscription_id}")
        if cost_data:
            trend_data, anomalies = analyze_cost_data(
                cost_data, subscription_id, summary_reports
            )
        if mode == "apply":
            logger.info(f"Applying policies to subscription: {subscription_id}")
            apply_policies(
                policies,
                dry_run=False,
                subscription_id=subscription_id,
                impacted_resources=impacted_resources,
                non_impacted_resources=non_impacted_resources,
                status_log=status_log,
            )
        else:
            logger.info(
                f"Dry run mode, policies will not be applied to subscription: {subscription_id}"
            )
            apply_policies(
                policies,
                dry_run=True,
                subscription_id=subscription_id,
                impacted_resources=impacted_resources,
                non_impacted_resources=non_impacted_resources,
                status_log=status_log,
            )
    except Exception as e:
        logger.error(f"Error processing subscription {subscription_id}: {e}")
        tc.track_exception()
    finally:
        logger.info(f"Completed processing subscription: {subscription_id}")
        tc.track_event(
            "SubscriptionProcessingCompleted", {"SubscriptionId": subscription_id}
        )

    return trend_data, anomalies


import threading

stop_event = threading.Event()


def stop():
    stop_event.set()


def main(mode="dry-run", tenant_id=None, all_subscriptions=True, stop_event=None):
    if not tenant_id:
        raise ValueError("Tenant ID must be provided.")
    global execution_data
    trend_data_all = []
    anomalies_all = []
    execution_data = []
    summary_reports = []
    impacted_resources = []
    non_impacted_resources = []
    status_log = []
    anomalies_all_reports = "anomalies_all.json"
    summary_reports_file = "summary_reports.json"
    execution_data_file = "execution_data.json"

    try:
        start_time = time.time()
        subscription_client = get_subscription_client(tenant_id)

        if all_subscriptions:
            subscriptions = subscription_client.subscriptions.list()
            for subscription in subscriptions:
                if stop_event and stop_event.is_set():
                    logger.info("Optimizer stopped.")
                    return "Optimizer stopped."
                try:
                    trend_data, anomalies = process_subscription(
                        subscription,
                        tenant_id,
                        mode,
                        summary_reports,
                        impacted_resources,
                        non_impacted_resources,
                        status_log,
                        start_date=None,
                        end_date=None,
                    )
                    trend_data_all.extend(trend_data)
                    anomalies_all.extend(anomalies)  # Add anomalies
                except Exception as e:
                    logger.error(f"Error processing subscription {subscription.subscription_id}: {e}")
        else:
            subscription_id = config["subscription"]["id"]
            subscription = subscription_client.subscriptions.get(subscription_id)
            if stop_event and stop_event.is_set():
                logger.info("Optimizer stopped by user.")
                return "Optimizer stopped."
            trend_data, anomalies = process_subscription(
                subscription,
                tenant_id,
                mode,
                summary_reports,
                impacted_resources,
                non_impacted_resources,
                status_log,
                start_date=None,
                end_date=None,
            )
            trend_data_all.extend(trend_data)
            anomalies_all.extend(anomalies)  # Add anomalies

        end_time = time.time()
        execution_time = end_time - start_time

        tc.track_event("OptimizerExecutionCompleted", {"ExecutionTime": execution_time})

        # Write results to JSON files
        with open(summary_reports_file, "w") as file:
            json.dump(summary_reports, file, indent=4, default=str)

        with open(execution_data_file, "w") as file:
            json.dump(status_log, file, indent=4, default=str)

        with open(anomalies_all_reports, "w") as file:
            json.dump(anomalies_all, file, indent=4, default=str)

        logger.info(f"Optimizer execution completed in {execution_time:.2f} seconds.")
        print("Summary Reports:", json.dumps(summary_reports, indent=4, default=str))
        print("Execution Data:", json.dumps(status_log, indent=4, default=str))
        print("Anomalies:", json.dumps(anomalies_all, indent=4, default=str))
        return {
            "summary_reports": summary_reports,
            "status_log": status_log,
            "impacted_resources": impacted_resources,
            "non_impacted_resources": non_impacted_resources,
            "trend_data": trend_data_all,
            "anomalies": anomalies_all,
        }
    except Exception as e:
        logger.error(f"Optimizer error: {e}")
        return {
            "summary_reports": [],
            "status_log": [],
            "impacted_resources": [],
            "non_impacted_resources": [],
            "trend_data": [],
            "anomalies": [],
            "error": str(e),
        }
