
# Azure Cost Optimizer
[![Azure Cost Optimization Workflow](https://github.com/jamelachahbar/CostOptTool/actions/workflows/ci.yml/badge.svg)](https://github.com/jamelachahbar/CostOptTool/actions/workflows/ci.yml)
[![Azure Cost Optimization Workflow Apply Mode](https://github.com/jamelachahbar/CostOptTool/actions/workflows/cd.yml/badge.svg)](https://github.com/jamelachahbar/CostOptTool/actions/workflows/cd.yml)

<img src="./newacologo1.png" alt="Description" width="300"/>

Azure Cost Optimizer is a Python-based tool used to optimize Azure resource costs by applying various policies to resources across multiple subscriptions. It identifies resources that meet specific criteria and applies actions such as scaling, stopping, or deleting them to reduce costs. The tool also provides detailed reports and logs the financial impact of the applied policies.

## 🚀 New: AI-Powered Cost Optimization Agent

Azure Cost Optimizer now includes an **intelligent AI agent** powered by:

- **Azure AI Foundry** - Enterprise-grade agent hosting with persistent agents
- **Microsoft Agent Framework v2** - Latest SDK for building agentic applications
- **Microsoft Learn MCP Integration** - Live documentation search using Model Context Protocol
- **Function Calling** - Curated Azure documentation links and actionable recommendations

### Agent Features
- 🤖 **Smart Recommendations** - AI-generated advice for each cost optimization recommendation
- 📚 **Live Documentation** - Real-time search of Microsoft Learn for current, accurate links
- 🔧 **Actionable Steps** - Clear bullet points and decisions for each recommendation
- 🔄 **Graceful Fallback** - Azure OpenAI fallback if Foundry is unavailable

## Features
- **Apply Policies**: Apply predefined policies to resources, such as stopping unused VMs, deleting unattached disks, scaling SQL databases, etc.
    - **Stop unused virtual machines** based on tags and usage.
    - **Delete unattached disks** based on tags.
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

## Policies

### Example Policies

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

1. **Azure Subscription**: Ensure you have an active Azure subscription with appropriate permissions.
2. **Azure CLI**: Install the Azure CLI (latest version) for authentication and managing Azure resources.
3. **Node.js & npm**: Required for the React frontend (Node.js 18+ recommended).
4. **Python 3.12+**: Required for the Flask backend.
5. **Permissions**: You need permissions to:
   - Create App Registrations
   - Create Service Principals
   - Assign RBAC roles at subscription/management group level
   - Create Azure resources (OpenAI, Storage Account)
   - Grant admin consent for API permissions

### Quick Setup Options

#### Option 1: Complete Setup Script (Recommended)

The fastest way to set up everything with a single script:

```powershell
# Clone the repository
git clone https://github.com/jamelachahbar/AzureOptimizer.git
cd AzureOptimizer/ui/backend

# Run the complete setup script
.\setup-complete.ps1
```

**Optional parameters:**
```powershell
# Customize settings
.\setup-complete.ps1 `
    -ResourceGroupName "MyOptimizer-RG" `
    -Location "eastus" `
    -UserEmail "your.email@example.com" `
    -ServicePrincipalName "MyOptimizerSP"
```

This single script creates:
- ✅ Resource Group
- ✅ Azure OpenAI resource with GPT-4 model
- ✅ Storage Account with blob container
- ✅ Service Principal with all required RBAC roles
- ✅ App Registration for frontend authentication
- ✅ App Roles (Admin/User) and role assignments
- ✅ API Permissions (Microsoft Graph, Azure Management API)
- ✅ Environment files (.env) for backend and frontend

#### Option 2: Azure Developer CLI (azd) - Recommended for Cloud Deployment

For production deployments with Container Apps:

```powershell
# Clone the repository
git clone https://github.com/jamelachahbar/AzureOptimizer.git
cd AzureOptimizer

# Login to Azure
azd auth login

# Deploy everything (infrastructure + containers)
azd up
```

This deploys:
- ✅ Azure Container Apps (frontend + backend)
- ✅ Azure Container Registry
- ✅ Azure AI Foundry (for AI agent)
- ✅ Azure OpenAI with GPT-4o
- ✅ Storage Account with blob container
- ✅ Key Vault for secrets
- ✅ Application Insights for monitoring
- ✅ User Managed Identity with RBAC roles
- ✅ App Registration for React frontend (via MS Graph)

#### Option 3: Infrastructure as Code with Bicep

For production deployments or infrastructure-as-code workflows:

```powershell
# Clone the repository
git clone https://github.com/jamelachahbar/AzureOptimizer.git
cd AzureOptimizer/infra

# Deploy using Bicep
.\deploy.ps1
```

The Bicep deployment uses Azure Verified Modules (AVM) for best practices and includes:
- Parameterized Bicep templates
- Idempotent deployments
- What-if capability for preview
- Comprehensive RBAC configuration
- Detailed infrastructure documentation

See [infra/README.md](infra/README.md) for detailed Bicep deployment instructions.

#### Option 3: Manual Step-by-Step Setup

If you prefer to run setup scripts individually:

```powershell
cd AzureOptimizer/ui/backend

# 1. Create Azure resources (OpenAI, Storage, Service Principal)
.\setup-azure-resources.ps1

# 2. Configure App Registration with roles and permissions
.\setup-frontend-roles.ps1

# 3. Assign RBAC permissions
.\setup-app-permissions.ps1
```

### What Gets Configured

All setup methods configure:

| Component | Details |
|-----------|---------|
| **Azure AI Foundry** | AI project with GPT-4o model deployment for agent hosting |
| **Azure OpenAI** | Cognitive Services account with GPT-4 deployment (fallback) |
| **Storage Account** | Blob storage with `costopttool` container for policies/schemas |
| **Service Principal** | Backend authentication with client ID and secret |
| **App Registration** | Frontend SPA authentication (supports work/school + personal accounts) |
| **RBAC Roles (Subscription)** | Contributor, Reader, Cost Management Reader, Monitoring Reader/Contributor |
| **RBAC Roles (AI Foundry)** | Azure AI User, Azure AI Owner for agent creation |
| **RBAC Roles (Storage)** | Storage Blob Data Contributor |
| **RBAC Roles (Management Group)** | Reader (root level - for listing all subscriptions) |
| **App Roles** | Admin (full access) and User (read-only) |
| **API Permissions** | Microsoft Graph (User.Read, Directory.Read.All), Azure Management API (user_impersonation) |
| **Environment Files** | `.env` files for backend and frontend auto-generated |

### Environment Configuration

After running any setup option, you'll find these files:

**Backend** (`ui/backend/.env`):
```env
# Azure Authentication
AZURE_CLIENT_ID=<service-principal-client-id>
AZURE_CLIENT_SECRET=<service-principal-secret>
AZURE_TENANT_ID=<your-tenant-id>
AZURE_SUBSCRIPTION_ID=<your-subscription-id>

# Azure OpenAI (fallback)
AZURE_OPENAI_ENDPOINT=<openai-endpoint>
AZURE_OPENAI_API_KEY=<openai-key>
AZURE_OPENAI_DEPLOYMENT_NAME=gpt-4

# Azure AI Foundry (Agent Framework)
AZURE_AI_PROJECT_ENDPOINT=<foundry-project-endpoint>
AZURE_AI_MODEL_DEPLOYMENT_NAME=gpt-4o

# Storage
STORAGE_ACCOUNT_URL=<storage-url>
```

**Frontend** (`ui/frontend/.env`):
```env
REACT_APP_AZURE_CLIENT_ID=<app-registration-id>
REACT_APP_AZURE_TENANT_ID=<your-tenant-id>
REACT_APP_REDIRECT_URI=http://localhost:3000
```

### Install Application Dependencies

After Azure setup completes, install the application dependencies:

**Backend:**
```powershell
cd ui/backend
python -m venv venv
venv\Scripts\activate  # Windows
# or: source venv/bin/activate  # Linux/Mac
pip install -r requirements.txt
```

**Frontend:**
```powershell
   cd ui/frontend
   npm install
   ```

5. Start the application:
   
   Backend:
   ```sh
   cd ui/backend
   python app.py
   ```

   Frontend (in a separate terminal):
   ```sh
   cd ui/frontend
   npm start
   ```

6. Access the UI:
   - Open http://localhost:3000
   - Log in with your Microsoft account (work/school or personal)
   - Admin users can use Apply mode; regular users have read-only access

### What Gets Configured

The automated setup configures:

✅ **Authentication**: SPA with support for organizational and personal Microsoft accounts  
✅ **Authorization**: Admin and User roles with proper permissions  
✅ **API Access**: Azure Management API for subscription listing  
✅ **Backend Access**: Service Principal with multi-subscription Reader role  
✅ **Storage**: Blob storage for policies and configuration  
✅ **AI Integration**: Azure OpenAI for intelligent recommendations  

### Manual Configuration (if needed)

If you prefer manual setup or need to reconfigure:

1. **Create App Registration**:
   - Portal → Azure Active Directory → App registrations → New registration
   - Configure as SPA with redirect URI: http://localhost:3000
   - Add API permissions: User.Read, Azure Management API

2. **Create Service Principal**:
   - `az ad sp create-for-rbac --name AzureOptimizerSP`
   - Assign necessary RBAC roles

3. **Define policies** in `policies/policies.yaml`

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
