# Azure Cost Optimizer

![Description of Image](./ACOlogo.png)

Azure Cost Optimizer is a Python-based tool designed to help manage and optimize costs in Azure environments by applying policies defined in YAML or JSON files. It retrieves cost data from Azure, analyzes it for trends and anomalies, and applies cost-saving actions based on defined policies.

## Features

- **Stop unused virtual machines** based on tags and usage.
- **Delete unattached disks** based on tags.
- **Delete all resources** in a resource group based on tags.
- **Delete unattached Public  IP Addressess**. (WIP)
- **SQL DTU Scaling**: Dynamically scale Azure SQL databases based on defined policies and schedules.
- Analyze cost data for trends and **anomalies**.
- Generate **summary reports**.

## Setup

### Prerequisites

1. **Azure Subscription**: Ensure you have an active Azure subscription.
2. **Azure CLI**: Install the Azure CLI for authentication and managing Azure resources.
3. **Python 3.8+**: Ensure Python 3.8 or later is installed on your machine.

### Installation

1. Clone the repository:
    ```sh
    git clone https://github.com/jachahbar/azure-cost-optimizer.git
    cd azure-cost-optimizer
    ```

2. Install dependencies:
    ```sh
    pip install -r requirements.txt
    ```

3. Configure your Azure credentials and subscription ID:
    - Set the environment variables `AZURE_SUBSCRIPTION_ID`, `APPINSIGHTS_INSTRUMENTATIONKEY`, `AZURE_CLIENT_ID`, `AZURE_TENANT_ID`, and `AZURE_CLIENT_SECRET` in your environment.

4. Define your policies in `policies/policies.yaml`.

5. Validate your policies against the schema in `src/schema.json`:
    ```sh
    python src/main.py
    ```

## Usage

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

```python src/main.py```

### SQL Scaling Module
The sql_scaling.py script allows for dynamic scaling of Azure SQL databases based on defined tiers and schedules.


### Project Files
- src/main.py: The main script to enforce policies defined in policies.yaml.
- src/schema.json: The JSON schema defining the structure of the policies.
- src/sql_scaling.py: Script to manage scaling of Azure SQL databases based on defined policies.
- policies/policies.yaml: YAML file where you define your policies for various Azure resources.
### Contributing
Contributions are welcome! Please open an issue or submit a pull request with your changes.

### License
This project is licensed under the MIT License - see the LICENSE file for details.


### Acknowledgements
https://github.com/Azure/azure-sdk-for-python for Python for providing the necessary tools to interact with Azure services