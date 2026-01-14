// ============================================================================
// Azure OpenAI Module
// ============================================================================

@description('Location for the OpenAI resource')
param location string

@description('Tags to apply to all resources')
param tags object = {}

@description('Name of the OpenAI account')
param openAIName string

@description('Key Vault name for storing secrets')
param keyVaultName string

@description('Managed Identity Principal ID for RBAC')
param managedIdentityPrincipalId string

@description('Use existing OpenAI resource')
param useExisting bool = false

@description('Existing OpenAI resource name')
param existingOpenAIName string = ''

@description('Existing OpenAI resource group')
param existingOpenAIResourceGroup string = ''

@description('Model deployments to create')
param deployments array = []

// ============================================================================
// Existing or New OpenAI Account
// ============================================================================

resource existingOpenAI 'Microsoft.CognitiveServices/accounts@2024-10-01' existing = if (useExisting) {
  name: existingOpenAIName
  scope: resourceGroup(existingOpenAIResourceGroup)
}

resource openAI 'Microsoft.CognitiveServices/accounts@2024-10-01' = if (!useExisting) {
  name: openAIName
  location: location
  tags: tags
  kind: 'OpenAI'
  sku: {
    name: 'S0'
  }
  properties: {
    customSubDomainName: openAIName
    publicNetworkAccess: 'Enabled'
    networkAcls: {
      defaultAction: 'Allow'
    }
  }
}

// ============================================================================
// Model Deployments
// ============================================================================

@batchSize(1)
resource openAIDeployments 'Microsoft.CognitiveServices/accounts/deployments@2024-10-01' = [for deployment in deployments: if (!useExisting) {
  parent: openAI
  name: deployment.name
  sku: {
    name: deployment.skuName
    capacity: deployment.capacity
  }
  properties: {
    model: {
      format: 'OpenAI'
      name: deployment.modelName
      version: deployment.modelVersion
    }
    raiPolicyName: 'Microsoft.Default'
  }
}]

// ============================================================================
// Key Vault Secret for API Key
// ============================================================================

resource keyVault 'Microsoft.KeyVault/vaults@2023-07-01' existing = {
  name: keyVaultName
}

resource openAIKeySecret 'Microsoft.KeyVault/vaults/secrets@2023-07-01' = if (!useExisting) {
  parent: keyVault
  name: 'azure-openai-key'
  properties: {
    value: openAI.listKeys().key1
  }
}

// ============================================================================
// RBAC: Cognitive Services OpenAI User for Managed Identity
// ============================================================================

var cognitiveServicesOpenAIUserRole = subscriptionResourceId('Microsoft.Authorization/roleDefinitions', '5e0bd9bd-7b93-4f28-af87-19fc36ad61bd')

resource openAIRoleAssignment 'Microsoft.Authorization/roleAssignments@2022-04-01' = if (!useExisting) {
  scope: openAI
  name: guid(openAI.id, managedIdentityPrincipalId, cognitiveServicesOpenAIUserRole)
  properties: {
    roleDefinitionId: cognitiveServicesOpenAIUserRole
    principalId: managedIdentityPrincipalId
    principalType: 'ServicePrincipal'
  }
}

// ============================================================================
// Outputs
// ============================================================================

output openAIId string = useExisting ? existingOpenAI.id : openAI.id
output openAIName string = useExisting ? existingOpenAI.name : openAI.name
output endpoint string = useExisting ? existingOpenAI.properties.endpoint : openAI.properties.endpoint
