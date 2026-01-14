using './main.bicep'

// ============================================================================
// Azure Cost Optimizer - Bicep Parameters
// ============================================================================
// Default parameters for azd deployment
// Override these in your azure.yaml or via azd env set
// ============================================================================

param environmentName = readEnvironmentVariable('AZURE_ENV_NAME', 'dev')
param location = readEnvironmentVariable('AZURE_LOCATION', 'eastus2')

// Optional: Use existing OpenAI resource
param useExistingOpenAI = false
param existingOpenAIName = ''
param existingOpenAIResourceGroup = ''

// Container images (auto-populated by azd deploy)
param backendImageName = ''
param frontendImageName = ''

// App Registration configuration
param userObjectId = readEnvironmentVariable('AZURE_USER_OBJECT_ID', '')
param frontendRedirectUris = [
  'http://localhost:3000'
]
