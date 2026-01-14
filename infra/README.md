# Azure Optimizer - Infrastructure as Code

This directory contains Infrastructure as Code (IaC) templates for deploying Azure Optimizer using Bicep.

## Overview

The Bicep templates deploy the following resources:

- **Azure OpenAI**: Cognitive Services account with GPT-4 model deployment
- **Storage Account**: Blob storage for policies and optimization data
- **RBAC Roles**: Comprehensive role assignments for the Service Principal
- **Resource Group**: Container for all Azure Optimizer resources

## Prerequisites

- Azure CLI (latest version)
- Bicep CLI (included with Azure CLI)
- An Azure subscription with appropriate permissions
- Service Principal for backend authentication

## Deployment Options

### Option 1: Automated Deployment with PowerShell Script

The easiest way to deploy is using the PowerShell deployment script:

```powershell
cd C:\__repos\AzureOptimizer\infra
.\deploy.ps1
```

**Optional Parameters:**
```powershell
# Deploy with custom parameters
.\deploy.ps1 -ServicePrincipalName "MyCustomSP" -UserEmail "user@example.com"

# Run in WhatIf mode to preview changes
.\deploy.ps1 -WhatIf
```

### Option 2: Manual Bicep Deployment

For more control, deploy manually using Azure CLI:

1. **Create Service Principal first:**
   ```powershell
   az ad sp create-for-rbac --name "AzureOptimizerSP" --role Reader --scopes /subscriptions/<subscription-id>
   ```

2. **Get the Service Principal Object ID:**
   ```powershell
   $spObjectId = az ad sp list --display-name "AzureOptimizerSP" --query "[0].id" -o tsv
   ```

3. **Update the parameters file:**
   Edit `main.bicepparam` and replace `<REPLACE_WITH_SP_OBJECT_ID>` with the actual Object ID.

4. **Deploy the Bicep template:**
   ```powershell
   az deployment sub create `
       --location eastus `
       --template-file main.bicep `
       --parameters main.bicepparam
   ```

5. **Configure App Registration** (run the relevant sections from `deploy.ps1`)

## File Structure

```
infra/
├── main.bicep              # Main Bicep template
├── main.bicepparam         # Parameters file
├── deploy.ps1              # Automated deployment script
└── README.md               # This file
```

## Bicep Template Features

### Azure Verified Modules (AVM)

The template uses Azure Verified Modules for best practices:

- **Cognitive Services Account** (`avm/res/cognitive-services/account:0.14.1`)
  - OpenAI service with GPT-4 deployment
  - Secure endpoint configuration
  - Model deployment automation

- **Storage Account** (`avm/res/storage/storage-account:0.30.0`)
  - Blob storage with private access
  - TLS 1.2 minimum
  - Blob container creation

- **Role Assignments** (`avm/res/authorization/role-assignment/*`)
  - Subscription-level RBAC roles
  - Resource-level RBAC roles
  - Service Principal assignments

### RBAC Roles Assigned

| Role | Scope | Purpose |
|------|-------|---------|
| Contributor | Subscription | Manage Azure resources |
| Reader | Subscription + Management Group | Read access to all resources |
| Cost Management Reader | Subscription | Read cost data |
| Monitoring Reader | Subscription | Read monitoring data |
| Monitoring Contributor | Subscription | Write monitoring data |
| Storage Blob Data Contributor | Storage Account | Blob storage access |

### Security Features

- ✅ TLS 1.2 minimum for storage
- ✅ Public blob access disabled
- ✅ HTTPS-only traffic
- ✅ Hot access tier for performance
- ✅ Service Principal-based authentication
- ✅ Role-based access control (RBAC)

## Outputs

The deployment provides the following outputs:

- `openAIResourceId` - Resource ID of Azure OpenAI
- `openAIEndpoint` - HTTPS endpoint for Azure OpenAI
- `openAIDeploymentName` - Name of GPT-4 deployment
- `storageAccountResourceId` - Resource ID of storage account
- `storageAccountName` - Name of storage account
- `storageBlobEndpoint` - Primary blob endpoint URL
- `resourceGroupName` - Name of resource group
- `subscriptionId` - Azure subscription ID
- `tenantId` - Azure tenant ID

## Post-Deployment

After deployment completes:

1. **Environment files are automatically created:**
   - `ui/backend/.env` - Backend configuration
   - `ui/frontend/.env` - Frontend configuration

2. **Store the Client Secret securely** (if new Service Principal was created)

3. **Start the application:**
   ```powershell
   # Backend
   cd C:\__repos\AzureOptimizer\ui\backend
   python app.py

   # Frontend (new terminal)
   cd C:\__repos\AzureOptimizer\ui\frontend
   npm start
   ```

## Updating Infrastructure

To update existing infrastructure:

1. Modify `main.bicep` or `main.bicepparam`
2. Run the deployment script again:
   ```powershell
   .\deploy.ps1
   ```

Bicep will automatically detect and apply only the necessary changes.

## Cleanup

To remove all deployed resources:

```powershell
# Delete the resource group and all resources
az group delete --name AzureOptimizer-RG --yes --no-wait

# Optionally delete the Service Principal
az ad sp delete --id $(az ad sp list --display-name "AzureOptimizerSP" --query "[0].appId" -o tsv)
```

## Troubleshooting

### Permission Errors

If you see permission errors during deployment:
- Ensure you have Owner or Contributor + User Access Administrator roles
- For App Registration, you need Application.ReadWrite.All in Microsoft Graph

### Service Principal Not Found

If the script can't find the Service Principal:
```powershell
# List all service principals
az ad sp list --display-name "AzureOptimizer" --query "[].{Name:displayName, ObjectId:id, AppId:appId}"
```

### Deployment Validation

To validate the template without deploying:
```powershell
.\deploy.ps1 -WhatIf
```

## Best Practices

1. **Use Parameters File**: Always use `main.bicepparam` for environment-specific values
2. **Tag Resources**: Modify the `tags` parameter to match your organization's tagging policy
3. **Regional Deployment**: Update `location` parameter for your preferred region
4. **Secret Management**: Store Service Principal secrets in Azure Key Vault
5. **Version Control**: Commit only `main.bicep` and `main.bicepparam` (without secrets)

## Additional Resources

- [Azure Bicep Documentation](https://learn.microsoft.com/azure/azure-resource-manager/bicep/)
- [Azure Verified Modules](https://azure.github.io/Azure-Verified-Modules/)
- [Bicep Best Practices](https://learn.microsoft.com/azure/azure-resource-manager/bicep/best-practices)
