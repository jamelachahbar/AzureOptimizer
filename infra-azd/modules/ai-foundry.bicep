// ============================================================================
// Azure AI Foundry Module
// ============================================================================
// Deploys Azure AI Foundry (AI Services) with project for agent hosting
// ============================================================================

@description('Location for resources')
param location string

@description('Tags to apply to resources')
param tags object

@description('AI Services account name')
param aiServicesName string

@description('AI Foundry project name')
param projectName string

@description('Key Vault name for storing secrets')
param keyVaultName string

@description('Managed Identity Principal ID for RBAC')
param managedIdentityPrincipalId string

@description('Model deployments configuration')
param deployments array = [
  {
    name: 'gpt-4o'
    modelName: 'gpt-4o'
    modelVersion: '2024-08-06'
    skuName: 'GlobalStandard'
    capacity: 10
  }
]

// ============================================================================
// Variables
// ============================================================================

// Built-in role definition IDs
var azureAIUserRoleId = '53ca6127-db72-4b80-b1b0-d745d6d5456d'
var azureAIOwnerRoleId = 'c883944f-8b7b-4483-af10-35834be79c4a'
var cognitiveServicesOpenAIContributorRoleId = 'a001fd3d-188f-4b5d-821b-7da978bf7442'

// ============================================================================
// AI Services Account (Foundry)
// ============================================================================

resource aiServices 'Microsoft.CognitiveServices/accounts@2025-04-01-preview' = {
  name: aiServicesName
  location: location
  tags: tags
  kind: 'AIServices'
  sku: {
    name: 'S0'
  }
  identity: {
    type: 'SystemAssigned'
  }
  properties: {
    customSubDomainName: aiServicesName
    publicNetworkAccess: 'Enabled'
    allowProjectManagement: true
    networkAcls: {
      defaultAction: 'Allow'
    }
  }
}

// ============================================================================
// Model Deployments
// ============================================================================

resource modelDeployments 'Microsoft.CognitiveServices/accounts/deployments@2025-04-01-preview' = [for deployment in deployments: {
  parent: aiServices
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
    raiPolicyName: 'Microsoft.DefaultV2'
  }
}]

// ============================================================================
// AI Foundry Project
// ============================================================================

resource aiProject 'Microsoft.CognitiveServices/accounts/projects@2025-04-01-preview' = {
  parent: aiServices
  name: projectName
  location: location
  tags: tags
  properties: {}
  dependsOn: [
    modelDeployments
  ]
}

// ============================================================================
// RBAC Assignments for Managed Identity
// ============================================================================

// Azure AI User - For agent data plane access
resource azureAIUserRole 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(aiServices.id, managedIdentityPrincipalId, azureAIUserRoleId)
  scope: aiServices
  properties: {
    principalId: managedIdentityPrincipalId
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', azureAIUserRoleId)
    principalType: 'ServicePrincipal'
  }
}

// Azure AI Owner - For full agent management
resource azureAIOwnerRole 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(aiServices.id, managedIdentityPrincipalId, azureAIOwnerRoleId)
  scope: aiServices
  properties: {
    principalId: managedIdentityPrincipalId
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', azureAIOwnerRoleId)
    principalType: 'ServicePrincipal'
  }
}

// Cognitive Services OpenAI Contributor - For model access
resource cognitiveServicesContributorRole 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(aiServices.id, managedIdentityPrincipalId, cognitiveServicesOpenAIContributorRoleId)
  scope: aiServices
  properties: {
    principalId: managedIdentityPrincipalId
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', cognitiveServicesOpenAIContributorRoleId)
    principalType: 'ServicePrincipal'
  }
}

// ============================================================================
// Store API Key in Key Vault
// ============================================================================

resource keyVault 'Microsoft.KeyVault/vaults@2023-07-01' existing = {
  name: keyVaultName
}

resource aiServicesKeySecret 'Microsoft.KeyVault/vaults/secrets@2023-07-01' = {
  parent: keyVault
  name: 'azure-ai-services-key'
  properties: {
    value: aiServices.listKeys().key1
  }
}

// ============================================================================
// Outputs
// ============================================================================

@description('The AI Services endpoint')
output endpoint string = aiServices.properties.endpoint

@description('The AI Services resource ID')
output resourceId string = aiServices.id

@description('The AI Project name')
output projectName string = aiProject.name

@description('The AI Project endpoint for agents')
output projectEndpoint string = '${aiServices.properties.endpoint}api/projects/${aiProject.name}'

@description('The AI Services name')
output aiServicesName string = aiServices.name
