// ============================================================================
// Azure Cost Optimizer - Main Infrastructure Template
// ============================================================================
// This is the main orchestrator for deploying all Azure resources
// Use with Azure Developer CLI: azd up
// ============================================================================

targetScope = 'subscription'

// Import Microsoft Graph extension for App Registration
extension microsoftGraphV1_0

// ============================================================================
// Parameters
// ============================================================================

@minLength(1)
@maxLength(64)
@description('Name of the environment (e.g., dev, staging, prod)')
param environmentName string

@minLength(1)
@description('Primary location for all resources')
param location string

@description('Name of the resource group')
param resourceGroupName string = ''

@description('Tags to apply to all resources')
param tags object = {}

// Optional: Use existing resources
@description('Use existing Azure OpenAI resource')
param useExistingOpenAI bool = false

@description('Existing Azure OpenAI resource name')
param existingOpenAIName string = ''

@description('Existing Azure OpenAI resource group')
param existingOpenAIResourceGroup string = ''

// Container configuration
@description('Backend container image')
param backendImageName string = ''

@description('Frontend container image')
param frontendImageName string = ''

// App Registration configuration
@description('User Object ID for Admin role assignment (optional)')
param userObjectId string = ''

@description('Frontend redirect URIs')
param frontendRedirectUris array = [
  'http://localhost:3000'
]

// ============================================================================
// Variables
// ============================================================================

var abbrs = loadJsonContent('./abbreviations.json')
var resourceToken = toLower(uniqueString(subscription().id, environmentName, location))

var defaultTags = {
  'azd-env-name': environmentName
  'application': 'azure-cost-optimizer'
  'managed-by': 'bicep'
}

var finalTags = union(defaultTags, tags)

// Resource names
var rgName = !empty(resourceGroupName) ? resourceGroupName : '${abbrs.resourcesResourceGroups}${environmentName}'

// ============================================================================
// Resource Group
// ============================================================================

resource rg 'Microsoft.Resources/resourceGroups@2024-03-01' = {
  name: rgName
  location: location
  tags: finalTags
}

// ============================================================================
// Monitoring Module
// ============================================================================

module monitoring './modules/monitoring.bicep' = {
  name: 'monitoring-${resourceToken}'
  scope: rg
  params: {
    location: location
    tags: finalTags
    logAnalyticsName: '${abbrs.operationalInsightsWorkspaces}${resourceToken}'
    applicationInsightsName: '${abbrs.insightsComponents}${resourceToken}'
  }
}

// ============================================================================
// Security Module (Key Vault & Managed Identity)
// ============================================================================

module security './modules/security.bicep' = {
  name: 'security-${resourceToken}'
  scope: rg
  params: {
    location: location
    tags: finalTags
    keyVaultName: '${abbrs.keyVaultVaults}${resourceToken}'
    managedIdentityName: '${abbrs.managedIdentityUserAssignedIdentities}${resourceToken}'
  }
}

// ============================================================================
// Storage Module
// ============================================================================

module storage './modules/storage.bicep' = {
  name: 'storage-${resourceToken}'
  scope: rg
  params: {
    location: location
    tags: finalTags
    storageAccountName: '${abbrs.storageStorageAccounts}${resourceToken}'
    managedIdentityPrincipalId: security.outputs.managedIdentityPrincipalId
  }
}

// ============================================================================
// Azure OpenAI Module
// ============================================================================

module openai './modules/openai.bicep' = {
  name: 'openai-${resourceToken}'
  scope: rg
  params: {
    location: location
    tags: finalTags
    openAIName: '${abbrs.cognitiveServicesAccounts}${resourceToken}'
    keyVaultName: security.outputs.keyVaultName
    managedIdentityPrincipalId: security.outputs.managedIdentityPrincipalId
    useExisting: useExistingOpenAI
    existingOpenAIName: existingOpenAIName
    existingOpenAIResourceGroup: existingOpenAIResourceGroup
    deployments: [
      {
        name: 'gpt-4o'
        modelName: 'gpt-4o'
        modelVersion: '2024-08-06'
        skuName: 'GlobalStandard'
        capacity: 10
      }
    ]
  }
}

// ============================================================================
// Azure AI Foundry Module (Agent Framework)
// ============================================================================

module aiFoundry './modules/ai-foundry.bicep' = {
  name: 'ai-foundry-${resourceToken}'
  scope: rg
  params: {
    location: location
    tags: finalTags
    aiServicesName: '${abbrs.cognitiveServicesAccounts}foundry-${resourceToken}'
    projectName: '${environmentName}-project'
    keyVaultName: security.outputs.keyVaultName
    managedIdentityPrincipalId: security.outputs.managedIdentityPrincipalId
    deployments: [
      {
        name: 'gpt-4o'
        modelName: 'gpt-4o'
        modelVersion: '2024-08-06'
        skuName: 'GlobalStandard'
        capacity: 10
      }
    ]
  }
}

// ============================================================================
// Microsoft Graph - App Registration for React Frontend
// ============================================================================
// Note: MS Graph resources are deployed at resource group scope but 
// the extension handles tenant-level Entra ID operations automatically

module appRegistration './modules/app-registration.bicep' = {
  name: 'app-registration-${resourceToken}'
  scope: rg
  params: {
    applicationDisplayName: 'AzureOptimizer-${environmentName}'
    redirectUris: union(frontendRedirectUris, [
      'https://${frontend.outputs.fqdn}'
    ])
    userObjectId: userObjectId
  }
}

// ============================================================================
// Container Apps Environment
// ============================================================================

module containerAppsEnv './modules/container-apps-env.bicep' = {
  name: 'container-apps-env-${resourceToken}'
  scope: rg
  params: {
    location: location
    tags: finalTags
    containerAppsEnvName: '${abbrs.appManagedEnvironments}${resourceToken}'
    logAnalyticsWorkspaceId: monitoring.outputs.logAnalyticsWorkspaceId
  }
}

// ============================================================================
// Backend Container App
// ============================================================================

module backend './modules/container-app-backend.bicep' = {
  name: 'backend-${resourceToken}'
  scope: rg
  params: {
    location: location
    tags: finalTags
    containerAppName: '${abbrs.appContainerApps}backend-${resourceToken}'
    containerAppsEnvironmentId: containerAppsEnv.outputs.containerAppsEnvironmentId
    managedIdentityId: security.outputs.managedIdentityId
    imageName: !empty(backendImageName) ? backendImageName : 'mcr.microsoft.com/azuredocs/containerapps-helloworld:latest'
    
    // Environment variables
    envVars: [
      {
        name: 'AZURE_OPENAI_ENDPOINT'
        value: openai.outputs.endpoint
      }
      {
        name: 'AZURE_OPENAI_DEPLOYMENT_NAME'
        value: 'gpt-4o'
      }
      {
        name: 'AZURE_OPENAI_API_VERSION'
        value: '2024-12-01-preview'
      }
      {
        name: 'AZURE_AI_PROJECT_ENDPOINT'
        value: aiFoundry.outputs.projectEndpoint
      }
      {
        name: 'AZURE_AI_MODEL_DEPLOYMENT_NAME'
        value: 'gpt-4o'
      }
      {
        name: 'STORAGE_ACCOUNT_URL'
        value: storage.outputs.blobEndpoint
      }
      {
        name: 'APPLICATIONINSIGHTS_CONNECTION_STRING'
        value: monitoring.outputs.applicationInsightsConnectionString
      }
      {
        name: 'AZURE_CLIENT_ID'
        value: security.outputs.managedIdentityClientId
      }
    ]
    
    // Secrets from Key Vault
    secrets: [
      {
        name: 'azure-openai-key'
        keyVaultUrl: '${security.outputs.keyVaultUri}secrets/azure-openai-key'
        identity: security.outputs.managedIdentityId
      }
      {
        name: 'azure-ai-services-key'
        keyVaultUrl: '${security.outputs.keyVaultUri}secrets/azure-ai-services-key'
        identity: security.outputs.managedIdentityId
      }
    ]
  }
}

// ============================================================================
// Frontend Container App
// ============================================================================

module frontend './modules/container-app-frontend.bicep' = {
  name: 'frontend-${resourceToken}'
  scope: rg
  params: {
    location: location
    tags: finalTags
    containerAppName: '${abbrs.appContainerApps}frontend-${resourceToken}'
    containerAppsEnvironmentId: containerAppsEnv.outputs.containerAppsEnvironmentId
    imageName: !empty(frontendImageName) ? frontendImageName : 'mcr.microsoft.com/azuredocs/containerapps-helloworld:latest'
    backendUrl: backend.outputs.fqdn
  }
}

// ============================================================================
// Outputs
// ============================================================================

output AZURE_LOCATION string = location
output AZURE_RESOURCE_GROUP string = rg.name

// Service endpoints
output SERVICE_BACKEND_URI string = backend.outputs.uri
output SERVICE_FRONTEND_URI string = frontend.outputs.uri

// Resource IDs for reference
output AZURE_KEY_VAULT_NAME string = security.outputs.keyVaultName
output AZURE_STORAGE_ACCOUNT_NAME string = storage.outputs.storageAccountName
output AZURE_OPENAI_ENDPOINT string = openai.outputs.endpoint
output AZURE_CONTAINER_APPS_ENVIRONMENT_NAME string = containerAppsEnv.outputs.containerAppsEnvironmentName

// AI Foundry outputs
output AZURE_AI_PROJECT_ENDPOINT string = aiFoundry.outputs.projectEndpoint
output AZURE_AI_SERVICES_NAME string = aiFoundry.outputs.aiServicesName

// Managed Identity
output AZURE_MANAGED_IDENTITY_CLIENT_ID string = security.outputs.managedIdentityClientId

// App Registration outputs
output AZURE_APP_CLIENT_ID string = appRegistration.outputs.applicationClientId
output AZURE_APP_OBJECT_ID string = appRegistration.outputs.applicationObjectId
