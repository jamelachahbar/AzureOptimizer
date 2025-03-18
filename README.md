
# Azure Optimizer
[![Azure Cost Optimization Workflow](https://github.com/jamelachahbar/CostOptTool/actions/workflows/ci.yml/badge.svg)](https://github.com/jamelachahbar/CostOptTool/actions/workflows/ci.yml)
[![Azure Cost Optimization Workflow Apply Mode](https://github.com/jamelachahbar/CostOptTool/actions/workflows/cd.yml/badge.svg)](https://github.com/jamelachahbar/CostOptTool/actions/workflows/cd.yml)

<img src="" alt="Description" width="300"/>

Azure Optimizer is a Python-based tool used to optimize Azure resource costs by applying various policies to resources across multiple subscriptions. It identifies resources that meet specific criteria and applies actions such as scaling, stopping, or deleting them to reduce costs. The tool also provides detailed reports and logs the financial impact of the applied policies.

## Features
- **Apply Policies**: Apply predefined policies to resources, such as stopping unused VMs, deleting unattached disks, scaling SQL databases, etc.
    - **Stop unused virtual machines** based on tags and usage.
    - **Delete unattached disks** based on tags. 1
    - **Delete all resources** in a resource group based on tags.
    - **Delete idle Application Gateway**.
    - **Delete unattached Public IP Addresses**.
    - **Delete unattached Network Interfaces**.
    - **SQL DTU Scaling**: Dynamically scale Azure SQL databases based on defined policies and schedules.
    - **Storage Account SKU change**: Update Storage Account SKU to Standard_LRS for specific SKUs and tags
    - **Downgrade disks of deallocated VM's**: Automatically downgrade disks of deallocated VM's.
- Analyze cost data for trends and **anomalies**.
- Generate **summary reports**.
- **Multi-Subscription Support**: Process multiple subscriptions within a tenant.
- **Application Insights Integration**: Track events and metrics in Azure Application Insights. (Work in progress)

## Policies:

### Example Policies:

1. **Stop Unused VMs**
   ```yaml
   name: stop-unused-vms
   resource: azure.vm
   filters:
     - type: last_used
       days: 30
       threshold: 5
   actions:
     - type: stop
   ```

2. **Delete Unattached Disks**
   ```yaml
   name: delete-unused-disks
   resource: azure.disk
   filters:
     - type: unattached
   actions:
     - type: delete
   ```

3. **Delete Resources in Group**
   ```yaml
   name: delete-resources-in-group
   resource: azure.resourcegroup
   filters:
     - type: tag
       key: delete
       value: true
   actions:
     - type: delete
   ```

4. **Delete Idle Application Gateway**
   ```yaml
   name: delete-idle-application-gateway
   resource: azure.applicationgateway
   filters:
     - type: empty_backend_pools
   actions:
     - type: delete
   ```

5. **Delete Unattached Public IPs**
   ```yaml
   name: delete-unattached-public-ips
   resource: azure.publicip
   filters:
     - type: unattached
   actions:
     - type: delete
   ```

6. **Delete Unattached Network Interfaces**
   ```yaml
   name: delete-unattached-nics
   resource: azure.nic
   filters:
     - type: unattached
   actions:
     - type: delete
   ```

7. **Scale SQL Database DTU**
   ```yaml
   name: scale-sql-database-dtu
   resource: azure.sql
   actions:
     - type: scale_sql_database
       tiers:
         - name: Standard
           min_dtu: 10
           max_dtu: 100
           off_peak_dtu: 50
           peak_dtu: 100
   ```



7.  **Storage Account SKU change**
    ```yaml
    name: update-storage-account-sku
    description: Update Storage Account SKU to Standard_LRS for specific SKUs and tags
    resource: "azure.storage"
    filters:
      - type: "sku"
        values: ["Standard_GRS", "Standard_RAGRS", "Standard_ZRS", "Standard_GZRS"]
      - type: "tag"
        key: "costopt"
        value: "true"
    ```
## Setup

### Prerequisites

1. **Azure Subscription**: Ensure you have an active Azure subscription.
2. **Azure CLI**: Install the Azure CLI for authentication and managing Azure resources.
3. **Python 3.8+**: Ensure Python 3.8 or later is installed on your machine.
4. **Azure SDK for Python**
5. Configuration file (**config.yaml**)

### Installation

1. Clone the repository:
    ```sh
    git clone https://github.com/jamelachahbar/CostOptTool.git
    cd CostOptTool
    ```

2. Install dependencies:
    ```sh
    pip install -r requirements.txt
    ```

3. Configure your Azure credentials and subscription ID:
    - Set the environment variables `AZURE_SUBSCRIPTION_ID`, `APPINSIGHTS_INSTRUMENTATIONKEY`, `AZURE_CLIENT_ID`, `AZURE_TENANT_ID`, and `AZURE_CLIENT_SECRET` in your environment.

4. Define your policies in `policies/policies.yaml`.

### Usage

### Running Locally

To run the script locally, ensure that you have set the required environment variables for Azure authentication. You can set these variables in your shell or create a `.env` file.

Example of setting environment variables in the shell:
```sh
export AZURE_SUBSCRIPTION_ID="your_subscription_id"
export APPINSIGHTS_INSTRUMENTATIONKEY="your_application_insights_instrumentation_key"
export AZURE_CLIENT_ID="your_client_id"
export AZURE_TENANT_ID="your_tenant_id"
export AZURE_CLIENT_SECRET="your_client_secret"
```

### Running the Optimizer
Execute the main script to apply your policies:

**Dry run mode** can be used to see if any action will be taken before actually applying actions:

```sh
python src/main.py --mode dry-run
```

```sh
python src/main.py --mode dry-run [--all-subscriptions]
```

#### Arguments
- **--mode**: Mode to run the tool (dry-run or apply)
- **--all-subscriptions**: Process all subscriptions in the tenant

**Example**

Dry run mode for a single subscription:

```sh
python src/main.py --mode dry-run
```

Apply mode for all subscriptions:

```sh
python src/main.py --mode apply --all-subscriptions
```

**Work In Progress -->**
Apply mode for all subscriptions + getting cost from adls:

```sh
python src/main.py --mode apply --all-subscriptions --use-adls
```

### Output

The tool provides detailed output, including:

- Cost Analysis Report: Trend and anomaly detection in cost data.
- Policy Application Summary: Summary of impacted and non-impacted resources for each policy.
- Operation Status: Detailed status of each operation performed on the resources.
- Subscription Details: Outputs are clearly labeled with subscription IDs for clarity.

**Example Output**

```
 _______                            _______                    _______            _       _
(_______)                          (_______)            _     (_______)       _  (_)     (_)
 _______ _____ _   _  ____ _____    _       ___   ___ _| |_    _     _ ____ _| |_ _ ____  _ _____ _____  ____
|  ___  (___  ) | | |/ ___) ___ |  | |     / _ \ /___|_   _)  | |   | |  _ (_   _) |    \| (___  ) ___ |/ ___)
| |   | |/ __/| |_| | |   | ____|  | |____| |_| |___ | | |_   | |___| | |_| || |_| | | | | |/ __/| ____| |
|_|   |_(_____)____/|_|   |_____)   \______)___/(___/   \__)   \_____/|  __/  \__)_|_|_|_|_(_____)_____)_|
                                                                      |_|

Running Azure Cost Optimizer Tool...
Please wait...
Azure Cost Optimizer Tool is ready!
==============================================================================================================
Cost Analysis for Subscription ID: <subscription_id>
+----------------------------+------------+---------+
|      Anomaly Detected      |    Date    |   Cost  |
+----------------------------+------------+---------+
| Isolation Forest Algorithm | 2024-06-04 | €218.72 |
+----------------------------+------------+---------+

Impacted Resources for Subscription ID: <subscription_id>
+------------------------+---------------+---------+
|         Policy         |    Resource   | Actions |
+------------------------+---------------+---------+
| scale-sql-database-dtu |     master    |  scale  |
| scale-sql-database-dtu | costopttestdb |  scale  |
| scale-sql-database-dtu |  onpremdgwsql |  scale  |
+------------------------+---------------+---------+

Non-Impacted Resources for Subscription ID: <subscription_id>
+--------------------------------+---------------------+
|             Policy             |    Resource Type    |
+--------------------------------+---------------------+
|        stop-unused-vms         |          VM         |
|      delete-unused-disks       |         Disk        |
|  delete-unattached-public-ips  |      Public IP      |
|   delete-resources-in-group    |    Resource Group   |
|   update-storage-account-sku   |   Storage Account   |
| delete-empty-backend-pool-app- | Application Gateway |
|            gateways            |                     |
+--------------------------------+---------------------+

Operation Status for Subscription ID: <subscription_id>
+---------------+--------+---------+--------------------------------+
|    Resource   | Action |  Status |            Message             |
+---------------+--------+---------+--------------------------------+
| costopttestdb | scale  | Dry Run | Dry run mode, no action taken. |
|               |        |         |     Would scale DTU to 50      |
|  onpremdgwsql | scale  | Dry Run | Dry run mode, no action taken. |
|               |        |         |     Would scale DTU to 50      |
+---------------+--------+---------+--------------------------------+

Azure Cost Optimizer Tool completed!
==============================================================================================================
