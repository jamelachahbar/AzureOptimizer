// ========================================
// Azure Optimizer - Bicep Parameters File
// ========================================
using './main.bicep'

// Location for all resources
param location = 'eastus'

// Resource group name
param resourceGroupName = 'AzureOptimizer-RG'

// Service Principal Object ID (Service Principal must be created first)
// Run: az ad sp list --display-name "AzureOptimizerSP" --query "[0].id" -o tsv
param servicePrincipalObjectId = '<REPLACE_WITH_SP_OBJECT_ID>'

// Azure OpenAI configuration
param openAIAccountName = 'azureoptimizer-openai'

// Storage account configuration
param storageAccountName = 'azureoptimizer'

// GPT-4 deployment configuration
param gpt4Deployment = {
  name: 'gpt-4'
  modelName: 'gpt-4'
  modelVersion: '0613'
  skuCapacity: 1
  skuName: 'Standard'
}

// Tags for all resources
param tags = {
  Environment: 'Production'
  Application: 'AzureOptimizer'
  ManagedBy: 'Bicep'
  Owner: 'CloudTeam'
}
