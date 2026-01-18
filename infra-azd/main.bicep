// ============================================================================
// Azure Cost Optimizer - Main Infrastructure Template (AVM)
// ============================================================================
// Uses Azure Verified Modules (AVM) for production-ready deployments
// Custom module retained for: App Registration (MS Graph extension)
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

// AI Model configuration
@description('Azure AI Agent model deployment name')
param azureAiAgentModelDeploymentName string = 'gpt-4o'

// ============================================================================
// Variables
// ============================================================================

var abbrs = loadJsonContent('./abbreviations.json')
var resourceToken = toLower(uniqueString(subscription().id, environmentName, location))

var defaultTags = {
  'azd-env-name': environmentName
  application: 'azure-cost-optimizer'
  'managed-by': 'bicep-avm'
}

var finalTags = union(defaultTags, tags)

// Resource names
var rgName = !empty(resourceGroupName) ? resourceGroupName : '${abbrs.resourcesResourceGroups}${environmentName}'

// Role Definition IDs
var storageBlobDataContributorRoleId = 'ba92f5b4-2d11-453d-a403-e96b0029c9fe'
var acrPullRoleId = '7f951dda-4ed3-4680-a7ca-43fe172d538d'
var readerRoleId = 'acdd72a7-3385-48ef-bd42-f606fba81ae7'

// Computed Container App name for frontend FQDN (to avoid circular dependencies)
var frontendContainerAppName = '${abbrs.appContainerApps}frontend-${resourceToken}'

// ============================================================================
// Resource Group
// ============================================================================

resource rg 'Microsoft.Resources/resourceGroups@2024-03-01' = {
  name: rgName
  location: location
  tags: finalTags
}

// ============================================================================
// AVM: User Assigned Managed Identity
// ============================================================================

module managedIdentity 'br/public:avm/res/managed-identity/user-assigned-identity:0.4.0' = {
  name: 'managed-identity-${resourceToken}'
  scope: rg
  params: {
    name: '${abbrs.managedIdentityUserAssignedIdentities}${resourceToken}'
    location: location
    tags: finalTags
  }
}

// ============================================================================
// AVM: Log Analytics Workspace
// ============================================================================

module logAnalytics 'br/public:avm/res/operational-insights/workspace:0.9.1' = {
  name: 'log-analytics-${resourceToken}'
  scope: rg
  params: {
    name: '${abbrs.operationalInsightsWorkspaces}${resourceToken}'
    location: location
    tags: finalTags
    skuName: 'PerGB2018'
    dataRetention: 30
  }
}

// ============================================================================
// AVM: Application Insights
// ============================================================================

module applicationInsights 'br/public:avm/res/insights/component:0.4.2' = {
  name: 'app-insights-${resourceToken}'
  scope: rg
  params: {
    name: '${abbrs.insightsComponents}${resourceToken}'
    location: location
    tags: finalTags
    workspaceResourceId: logAnalytics.outputs.resourceId
    kind: 'web'
    applicationType: 'web'
  }
}

// ============================================================================
// AVM: Key Vault
// ============================================================================

module keyVault 'br/public:avm/res/key-vault/vault:0.11.0' = {
  name: 'key-vault-${resourceToken}'
  scope: rg
  params: {
    name: '${abbrs.keyVaultVaults}${resourceToken}'
    location: location
    tags: finalTags
    sku: 'standard'
    enableRbacAuthorization: true
    enablePurgeProtection: false
    roleAssignments: [
      {
        principalId: managedIdentity.outputs.principalId
        roleDefinitionIdOrName: 'Key Vault Secrets User'
        principalType: 'ServicePrincipal'
      }
    ]
  }
}

// ============================================================================
// AVM: Storage Account
// ============================================================================

module storageAccount 'br/public:avm/res/storage/storage-account:0.14.3' = {
  name: 'storage-${resourceToken}'
  scope: rg
  params: {
    name: '${abbrs.storageStorageAccounts}${resourceToken}'
    location: location
    tags: finalTags
    skuName: 'Standard_LRS'
    kind: 'StorageV2'
    allowBlobPublicAccess: false
    minimumTlsVersion: 'TLS1_2'
    blobServices: {
      containers: [
        {
          name: 'recommendations'
          publicAccess: 'None'
        }
        {
          name: 'exports'
          publicAccess: 'None'
        }
        {
          name: 'policies'
          publicAccess: 'None'
        }
      ]
      deleteRetentionPolicyEnabled: true
      deleteRetentionPolicyDays: 7
    }
    roleAssignments: [
      {
        principalId: managedIdentity.outputs.principalId
        roleDefinitionIdOrName: storageBlobDataContributorRoleId
        principalType: 'ServicePrincipal'
      }
    ]
  }
}

// ============================================================================
// AVM: Container Registry
// ============================================================================

module containerRegistry 'br/public:avm/res/container-registry/registry:0.7.0' = {
  name: 'container-registry-${resourceToken}'
  scope: rg
  params: {
    name: '${abbrs.containerRegistryRegistries}${resourceToken}'
    location: location
    tags: finalTags
    acrSku: 'Standard'
    acrAdminUserEnabled: true
    publicNetworkAccess: 'Enabled'
    retentionPolicyStatus: 'enabled'
    retentionPolicyDays: 7
    diagnosticSettings: [
      {
        name: 'default'
        workspaceResourceId: logAnalytics.outputs.resourceId
        logCategoriesAndGroups: [
          {
            categoryGroup: 'allLogs'
          }
        ]
        metricCategories: [
          {
            category: 'AllMetrics'
          }
        ]
      }
    ]
  }
}

// ACR Pull role assignment for managed identity
module registryPullRole 'br/public:avm/ptn/authorization/resource-role-assignment:0.1.2' = {
  name: 'container-registry-role-assignment-pull'
  scope: rg
  params: {
    principalId: managedIdentity.outputs.principalId
    resourceId: containerRegistry.outputs.resourceId
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', acrPullRoleId)
  }
}

// ============================================================================
// AVM Pattern: Azure AI Foundry (Hub + Project + AI Services)
// ============================================================================

module aiFoundry 'br/public:avm/ptn/ai-ml/ai-foundry:0.4.0' = {
  name: 'ai-foundry-${resourceToken}'
  scope: rg
  params: {
    baseName: 'azopt${take(environmentName, 6)}'
    location: location
    tags: finalTags
    aiFoundryConfiguration: {
      disableLocalAuth: false
      roleAssignments: [
        {
          principalId: managedIdentity.outputs.principalId
          roleDefinitionIdOrName: 'Cognitive Services User'
          principalType: 'ServicePrincipal'
        }
        {
          principalId: managedIdentity.outputs.principalId
          roleDefinitionIdOrName: 'Cognitive Services OpenAI User'
          principalType: 'ServicePrincipal'
        }
      ]
    }
    aiModelDeployments: [
      {
        name: 'gpt-4o'
        model: {
          format: 'OpenAI'
          name: 'gpt-4o'
          version: '2024-08-06'
        }
        sku: {
          name: 'GlobalStandard'
          capacity: 10
        }
        raiPolicyName: 'Microsoft.DefaultV2'
      }
    ]
  }
}

// AzureML Data Scientist role for AI Project access
module aiServicesDataScientistRole 'br/public:avm/ptn/authorization/resource-role-assignment:0.1.2' = {
  name: 'ai-services-data-scientist-role'
  scope: rg
  params: {
    principalId: managedIdentity.outputs.principalId
    resourceId: resourceId('Microsoft.CognitiveServices/accounts', aiFoundry.outputs.aiServicesName)
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', 'f6c7c914-8db3-469d-8ca1-694a8f32e121')
  }
}

// ============================================================================
// AVM: Container Apps Environment
// ============================================================================

module containerAppsEnv 'br/public:avm/res/app/managed-environment:0.8.0' = {
  name: 'container-apps-env-${resourceToken}'
  scope: rg
  params: {
    name: '${abbrs.appManagedEnvironments}${resourceToken}'
    location: location
    tags: finalTags
    logAnalyticsWorkspaceResourceId: logAnalytics.outputs.resourceId
    zoneRedundant: false
    internal: false
    workloadProfiles: [
      {
        name: 'Consumption'
        workloadProfileType: 'Consumption'
      }
    ]
  }
}

// ============================================================================
// Custom: Microsoft Graph - App Registration for React Frontend
// NOTE: Placed before container apps to avoid circular dependencies
// ============================================================================

// Computed frontend FQDN for redirect URI (avoids circular dependency with frontend module)
var computedFrontendFqdn = '${frontendContainerAppName}.${containerAppsEnv.outputs.defaultDomain}'

module appRegistration './modules/app-registration.bicep' = {
  name: 'app-registration-${resourceToken}'
  scope: rg
  params: {
    applicationDisplayName: 'AzureOptimizer-${environmentName}'
    redirectUris: union(frontendRedirectUris, [
      'https://${computedFrontendFqdn}'
    ])
    userObjectId: userObjectId
  }
}

// ============================================================================
// Subscription-level Reader Role Assignment for Managed Identity
// Required for backend to access Azure resources (Cost Management, Advisor, etc.)
// ============================================================================

resource subscriptionReaderRole 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(subscription().id, resourceToken, 'reader-role')
  properties: {
    principalId: managedIdentity.outputs.principalId
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', readerRoleId)
    principalType: 'ServicePrincipal'
  }
}

// ============================================================================
// AVM: Backend Container App
// ============================================================================

module backend 'br/public:avm/res/app/container-app:0.11.0' = {
  name: 'backend-${resourceToken}'
  scope: rg
  params: {
    name: '${abbrs.appContainerApps}backend-${resourceToken}'
    location: location
    tags: union(finalTags, { 'azd-service-name': 'backend' })
    environmentResourceId: containerAppsEnv.outputs.resourceId
    workloadProfileName: 'Consumption'
    managedIdentities: {
      userAssignedResourceIds: [
        managedIdentity.outputs.resourceId
      ]
    }
    containers: [
      {
        name: 'backend'
        image: !empty(backendImageName) ? backendImageName : 'mcr.microsoft.com/azuredocs/containerapps-helloworld:latest'
        resources: {
          cpu: '0.5'
          memory: '1Gi'
        }
        env: [
          {
            name: 'AZURE_CLIENT_ID'
            value: managedIdentity.outputs.clientId
          }
          {
            name: 'AZURE_TENANT_ID'
            value: subscription().tenantId
          }
          {
            name: 'AZURE_SUBSCRIPTION_ID'
            value: subscription().subscriptionId
          }
          {
            name: 'PROJECT_ENDPOINT'
            value: 'https://${aiFoundry.outputs.aiServicesName}.services.ai.azure.com/api/projects/${aiFoundry.outputs.aiProjectName}'
          }
          {
            name: 'AI_SERVICES_NAME'
            value: aiFoundry.outputs.aiServicesName
          }
          {
            name: 'AZURE_AI_AGENT_MODEL_DEPLOYMENT_NAME'
            value: azureAiAgentModelDeploymentName
          }
          {
            name: 'AZURE_OPENAI_ENDPOINT'
            value: 'https://${aiFoundry.outputs.aiServicesName}.openai.azure.com/'
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
            name: 'STORAGE_ACCOUNT_URL'
            value: storageAccount.outputs.primaryBlobEndpoint
          }
          {
            name: 'APPLICATIONINSIGHTS_CONNECTION_STRING'
            value: applicationInsights.outputs.connectionString
          }
        ]
        probes: [
          {
            type: 'Liveness'
            httpGet: {
              path: '/health'
              port: 5000
            }
            initialDelaySeconds: 30
            periodSeconds: 30
          }
          {
            type: 'Readiness'
            httpGet: {
              path: '/health'
              port: 5000
            }
            initialDelaySeconds: 5
            periodSeconds: 10
          }
        ]
      }
    ]
    registries: [
      {
        server: containerRegistry.outputs.loginServer
        identity: managedIdentity.outputs.resourceId
      }
    ]
    ingressExternal: true
    ingressTargetPort: 5000
    ingressTransport: 'http'
    ingressAllowInsecure: false
    corsPolicy: {
      allowedOrigins: ['*']
      allowedMethods: ['GET', 'POST', 'PUT', 'DELETE', 'OPTIONS']
      allowedHeaders: ['*']
    }
    scaleMinReplicas: 0
    scaleMaxReplicas: 3
    scaleRules: [
      {
        name: 'http-scaling'
        http: {
          metadata: {
            concurrentRequests: '50'
          }
        }
      }
    ]
  }
}

// ============================================================================
// AVM: Frontend Container App
// ============================================================================

module frontend 'br/public:avm/res/app/container-app:0.11.0' = {
  name: 'frontend-${resourceToken}'
  scope: rg
  params: {
    name: '${abbrs.appContainerApps}frontend-${resourceToken}'
    location: location
    tags: union(finalTags, { 'azd-service-name': 'frontend' })
    environmentResourceId: containerAppsEnv.outputs.resourceId
    workloadProfileName: 'Consumption'
    managedIdentities: {
      userAssignedResourceIds: [
        managedIdentity.outputs.resourceId
      ]
    }
    containers: [
      {
        name: 'frontend'
        image: !empty(frontendImageName) ? frontendImageName : 'mcr.microsoft.com/azuredocs/containerapps-helloworld:latest'
        resources: {
          cpu: '0.25'
          memory: '0.5Gi'
        }
        env: [
          {
            name: 'BACKEND_URL'
            value: 'https://${backend.outputs.fqdn}'
          }
          {
            name: 'AZURE_CLIENT_ID'
            value: managedIdentity.outputs.clientId
          }
          {
            name: 'REACT_APP_AZURE_CLIENT_ID'
            value: appRegistration.outputs.applicationClientId
          }
          {
            name: 'REACT_APP_AZURE_TENANT_ID'
            value: subscription().tenantId
          }
          {
            name: 'APPLICATIONINSIGHTS_CONNECTION_STRING'
            value: applicationInsights.outputs.connectionString
          }
        ]
        probes: [
          {
            type: 'Liveness'
            httpGet: {
              path: '/health'
              port: 80
            }
            initialDelaySeconds: 10
            periodSeconds: 30
          }
        ]
      }
    ]
    registries: [
      {
        server: containerRegistry.outputs.loginServer
        identity: managedIdentity.outputs.resourceId
      }
    ]
    ingressExternal: true
    ingressTargetPort: 80
    ingressTransport: 'http'
    ingressAllowInsecure: false
    scaleMinReplicas: 0
    scaleMaxReplicas: 3
    scaleRules: [
      {
        name: 'http-scaling'
        http: {
          metadata: {
            concurrentRequests: '100'
          }
        }
      }
    ]
  }
}

// ============================================================================
// Outputs - Aligned with azure.yaml expectations
// ============================================================================

// Core infrastructure
output AZURE_LOCATION string = location
output AZURE_RESOURCE_GROUP string = rg.name
output resourceGroupName string = rg.name

// Container Registry (required by azd for docker builds)
output AZURE_CONTAINER_REGISTRY_ENDPOINT string = containerRegistry.outputs.loginServer
output containerRegistryLoginServer string = containerRegistry.outputs.loginServer
output containerRegistryName string = containerRegistry.outputs.name

// Service endpoints
output SERVICE_BACKEND_URI string = 'https://${backend.outputs.fqdn}'
output SERVICE_FRONTEND_URI string = 'https://${frontend.outputs.fqdn}'
output containerAppFQDN string = frontend.outputs.fqdn

// Monitoring
output applicationInsightsConnectionString string = applicationInsights.outputs.connectionString
output AZURE_APPLICATION_INSIGHTS_CONNECTION_STRING string = applicationInsights.outputs.connectionString
output applicationInsightsInstrumentationKey string = applicationInsights.outputs.instrumentationKey

// Storage
output AZURE_STORAGE_ACCOUNT_NAME string = storageAccount.outputs.name

// Key Vault
output AZURE_KEY_VAULT_NAME string = keyVault.outputs.name
output keyVaultUri string = keyVault.outputs.uri

// AI Foundry
output aiFoundryAccountName string = aiFoundry.outputs.aiServicesName
output aiProjectName string = aiFoundry.outputs.aiProjectName
output AZURE_AI_PROJECT_ENDPOINT string = 'https://${aiFoundry.outputs.aiServicesName}.services.ai.azure.com/api/projects/${aiFoundry.outputs.aiProjectName}'
output aiProjectEndpoint string = 'https://${aiFoundry.outputs.aiServicesName}.services.ai.azure.com/api/projects/${aiFoundry.outputs.aiProjectName}'
output AZURE_AI_SERVICES_NAME string = aiFoundry.outputs.aiServicesName
output AZURE_OPENAI_ENDPOINT string = 'https://${aiFoundry.outputs.aiServicesName}.openai.azure.com/'
output openAiEndpoint string = 'https://${aiFoundry.outputs.aiServicesName}.openai.azure.com/'

// Managed Identity
output AZURE_MANAGED_IDENTITY_CLIENT_ID string = managedIdentity.outputs.clientId
output userManagedIdentityClientId string = managedIdentity.outputs.clientId
output userManagedIdentityPrincipalId string = managedIdentity.outputs.principalId

// Container Apps Environment
output AZURE_CONTAINER_APPS_ENVIRONMENT_NAME string = containerAppsEnv.outputs.name
output containerAppsEnvironmentDefaultDomain string = containerAppsEnv.outputs.defaultDomain

// App Registration
output AZURE_APP_CLIENT_ID string = appRegistration.outputs.applicationClientId
output AZURE_APP_OBJECT_ID string = appRegistration.outputs.applicationObjectId

// Subscription info
output AZURE_SUBSCRIPTION_ID string = subscription().subscriptionId
