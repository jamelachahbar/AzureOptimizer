using './main.bicep'

// ============================================================================
// Azure Cost Optimizer - Bicep Parameters
// ============================================================================
// Default parameters for azd deployment
// Override these via azd env set or environment variables
// ============================================================================

param environmentName = readEnvironmentVariable('AZURE_ENV_NAME', 'dev')
param location = readEnvironmentVariable('AZURE_LOCATION', 'eastus2')

// Container images (auto-populated by azd deploy)
param backendImageName = ''
param frontendImageName = ''

// App Registration configuration
param userObjectId = readEnvironmentVariable('AZURE_USER_OBJECT_ID', '')
param frontendRedirectUris = [
  'http://localhost:3000'
]

// AI Model configuration
param azureAiAgentModelDeploymentName = 'gpt-4o'
