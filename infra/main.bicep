// ========================================
// Azure Optimizer - Main Bicep Template
// ========================================
// This template deploys all required Azure resources for Azure Optimizer
// 
// NOTE: This version deploys Azure resources only.
// App Registration and API permissions are configured via deploy.ps1 script.
// 
// For pure Infrastructure as Code with Microsoft Graph extension, see:
// - main-with-graph.bicep (requires Bicep 0.24.0+)
// - MICROSOFT_GRAPH_BICEP_SETUP.md (setup guide)

targetScope = 'subscription'

@description('Location for all resources')
param location string = 'eastus'

@description('Resource group name')
param resourceGroupName string = 'AzureOptimizer-RG'

@description('Azure OpenAI account name')
param openAIAccountName string = 'azureoptimizer-openai-${uniqueString(subscription().subscriptionId)}'

@description('Storage account name')
param storageAccountName string = 'azureoptimizer${uniqueString(subscription().subscriptionId)}'

@description('Service Principal Object ID for RBAC assignments')
param servicePrincipalObjectId string

@description('GPT-4 model deployment configuration')
param gpt4Deployment object = {
  name: 'gpt-4'
  modelName: 'gpt-4'
  modelVersion: '0613'
  skuCapacity: 1
  skuName: 'Standard'
}

@description('Tags to apply to all resources')
param tags object = {
  Environment: 'Production'
  Application: 'AzureOptimizer'
  ManagedBy: 'Bicep'
}

// ========================================
// Resource Group
// ========================================
resource rg 'Microsoft.Resources/resourceGroups@2024-03-01' = {
  name: resourceGroupName
  location: location
  tags: tags
}

// ========================================
// Azure OpenAI Service
// ========================================
module openAI 'br/public:avm/res/cognitive-services/account:0.14.1' = {
  scope: rg
  name: 'openai-deployment'
  params: {
    name: openAIAccountName
    location: location
    kind: 'OpenAI'
    customSubDomainName: openAIAccountName
    sku: 'S0'
    deployments: [
      {
        name: gpt4Deployment.name
        model: {
          format: 'OpenAI'
          name: gpt4Deployment.modelName
          version: gpt4Deployment.modelVersion
        }
        sku: {
          name: gpt4Deployment.skuName
          capacity: gpt4Deployment.skuCapacity
        }
      }
    ]
    tags: tags
  }
}

// ========================================
// Storage Account
// ========================================
module storage 'br/public:avm/res/storage/storage-account:0.30.0' = {
  scope: rg
  name: 'storage-deployment'
  params: {
    name: storageAccountName
    location: location
    skuName: 'Standard_LRS'
    kind: 'StorageV2'
    accessTier: 'Hot'
    allowBlobPublicAccess: false
    minimumTlsVersion: 'TLS1_2'
    supportsHttpsTrafficOnly: true
    blobServices: {
      containers: [
        {
          name: 'costopttool'
          publicAccess: 'None'
        }
      ]
    }
    tags: tags
  }
}

// ========================================
// RBAC Role Assignments - Subscription Level
// ========================================

// Contributor Role
module contributorRole 'br/public:avm/res/authorization/role-assignment/sub-scope:0.1.1' = {
  name: 'contributor-role-assignment'
  params: {
    principalId: servicePrincipalObjectId
    roleDefinitionIdOrName: 'Contributor'
    principalType: 'ServicePrincipal'
  }
}

// Reader Role
module readerRole 'br/public:avm/res/authorization/role-assignment/sub-scope:0.1.1' = {
  name: 'reader-role-assignment'
  params: {
    principalId: servicePrincipalObjectId
    roleDefinitionIdOrName: 'Reader'
    principalType: 'ServicePrincipal'
  }
}

// Cost Management Reader Role
module costManagementReaderRole 'br/public:avm/res/authorization/role-assignment/sub-scope:0.1.1' = {
  name: 'cost-mgmt-reader-role-assignment'
  params: {
    principalId: servicePrincipalObjectId
    roleDefinitionIdOrName: 'Cost Management Reader'
    principalType: 'ServicePrincipal'
  }
}

// Monitoring Reader Role
module monitoringReaderRole 'br/public:avm/res/authorization/role-assignment/sub-scope:0.1.1' = {
  name: 'monitoring-reader-role-assignment'
  params: {
    principalId: servicePrincipalObjectId
    roleDefinitionIdOrName: 'Monitoring Reader'
    principalType: 'ServicePrincipal'
  }
}

// Monitoring Contributor Role
module monitoringContributorRole 'br/public:avm/res/authorization/role-assignment/sub-scope:0.1.1' = {
  name: 'monitoring-contributor-role-assignment'
  params: {
    principalId: servicePrincipalObjectId
    roleDefinitionIdOrName: 'Monitoring Contributor'
    principalType: 'ServicePrincipal'
  }
}

// ========================================
// RBAC Role Assignments - Resource Group Level
// ========================================
module storageBlobDataContributorRole 'br/public:avm/res/authorization/role-assignment/rg-scope:0.1.1' = {
  scope: rg
  name: 'storage-blob-contributor-role'
  params: {
    principalId: servicePrincipalObjectId
    roleDefinitionIdOrName: 'Storage Blob Data Contributor'
    principalType: 'ServicePrincipal'
  }
}

// ========================================
// Outputs
// ========================================
@description('The resource ID of the OpenAI account')
output openAIResourceId string = openAI.outputs.resourceId

@description('The endpoint of the OpenAI account')
output openAIEndpoint string = openAI.outputs.endpoint

@description('The name of the OpenAI deployment')
output openAIDeploymentName string = gpt4Deployment.name

@description('The resource ID of the storage account')
output storageAccountResourceId string = storage.outputs.resourceId

@description('The name of the storage account')
output storageAccountName string = storage.outputs.name

@description('The primary blob endpoint')
output storageBlobEndpoint string = storage.outputs.primaryBlobEndpoint

@description('The name of the resource group')
output resourceGroupName string = rg.name

@description('The location of the deployed resources')
output deploymentLocation string = location

@description('Subscription ID')
output subscriptionId string = subscription().subscriptionId

@description('Tenant ID')
output tenantId string = subscription().tenantId
