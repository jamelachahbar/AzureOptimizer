// ========================================
// Azure Optimizer - Main Bicep Template
// ========================================
// This template deploys all required Azure resources for Azure Optimizer
// INCLUDING Microsoft Graph resources (App Registration, Service Principal, App Roles, API Permissions)
//
// REQUIREMENTS:
// - Azure CLI with Bicep 0.24.0+ (for Microsoft Graph extension support)
// - Global Administrator or Application.ReadWrite.All + AppRoleAssignment.ReadWrite.All permissions
// - bicepconfig.json configured (see MICROSOFT_GRAPH_BICEP_SETUP.md)
//
// See MICROSOFT_GRAPH_BICEP_SETUP.md for detailed setup instructions

targetScope = 'subscription'

// Import Microsoft Graph extension (requires Bicep 0.24.0+)
extension microsoftGraphV1_0

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

@description('User Object ID for App Role assignment')
param userObjectId string

@description('Redirect URIs for the SPA application')
param redirectUris array = [
  'http://localhost:3000'
]

@description('Application display name')
param applicationDisplayName string = 'AzureOptimizerApp'

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
// Microsoft Graph Resources
// ========================================

// App Role GUIDs (must be unique and consistent)
var adminRoleId = 'f8e7a3f4-7b8c-4d2e-9f1a-5b6c8d9e0f2a'
var userRoleId = 'a1b2c3d4-e5f6-7890-1234-567890abcdef'

// API Permission IDs
// Microsoft Graph API
var microsoftGraphAppId = '00000003-0000-0000-c000-000000000000'
var userReadPermissionId = 'e1fe6dd8-ba31-4d61-89e7-88639da4683d' // User.Read (Delegated)
var directoryReadAllPermissionId = '06da0dbc-49e2-44d2-8312-53f166ab848a' // Directory.Read.All (Delegated)

// Azure Management API
var azureManagementAppId = '797f4846-ba00-4fd7-ba43-dac1f8f63013'
var userImpersonationPermissionId = '41094075-9dad-400e-a0bd-54e686782033' // user_impersonation (Delegated)

// Application Registration
resource application 'Microsoft.Graph/applications@v1.0' = {
  uniqueName: applicationDisplayName
  displayName: applicationDisplayName
  signInAudience: 'AzureADandPersonalMicrosoftAccount'
  
  // SPA Configuration
  spa: {
    redirectUris: redirectUris
  }
  
  // API Configuration
  api: {
    requestedAccessTokenVersion: 2
  }
  
  // App Roles
  appRoles: [
    {
      id: adminRoleId
      allowedMemberTypes: [
        'User'
      ]
      description: 'Administrators have full access to all Azure Optimizer features'
      displayName: 'Admin'
      isEnabled: true
      value: 'Admin'
    }
    {
      id: userRoleId
      allowedMemberTypes: [
        'User'
      ]
      description: 'Users have read-only access to Azure Optimizer features'
      displayName: 'User'
      isEnabled: true
      value: 'User'
    }
  ]
  
  // Required API Permissions
  requiredResourceAccess: [
    {
      // Microsoft Graph
      resourceAppId: microsoftGraphAppId
      resourceAccess: [
        {
          id: userReadPermissionId
          type: 'Scope' // Delegated permission
        }
        {
          id: directoryReadAllPermissionId
          type: 'Scope' // Delegated permission
        }
      ]
    }
    {
      // Azure Management API
      resourceAppId: azureManagementAppId
      resourceAccess: [
        {
          id: userImpersonationPermissionId
          type: 'Scope' // Delegated permission
        }
      ]
    }
  ]
}

// Service Principal for the Application
resource servicePrincipal 'Microsoft.Graph/servicePrincipals@v1.0' = {
  appId: application.appId
  accountEnabled: true
  
  // Tags for enterprise apps
  tags: [
    'WindowsAzureActiveDirectoryIntegratedApp'
  ]
}

// Assign user to Admin role
resource userRoleAssignment 'Microsoft.Graph/appRoleAssignedTo@v1.0' = {
  appRoleId: adminRoleId
  principalId: userObjectId
  resourceId: servicePrincipal.id
}

// Grant delegated permissions (requires admin consent)
resource oauth2PermissionGrant 'Microsoft.Graph/oauth2PermissionGrants@v1.0' = {
  clientId: servicePrincipal.id
  consentType: 'AllPrincipals' // Admin consent for all users
  principalId: null // null for admin consent to all users
  resourceId: servicePrincipal.id
  scope: 'User.Read Directory.Read.All user_impersonation'
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

@description('The Application (Client) ID')
output applicationClientId string = application.appId

@description('The Application Object ID')
output applicationObjectId string = application.id

@description('The Service Principal Object ID')
output servicePrincipalId string = servicePrincipal.id

@description('Subscription ID')
output subscriptionId string = subscription().subscriptionId

@description('Tenant ID')
output tenantId string = subscription().tenantId
