# Azure OpenAI and Service Principal Setup Script
# Run this script to create all necessary Azure resources

# Variables - Update these as needed
$resourceGroupName = "AzureOptimizer-RG"
$location = "eastus"
$openaiAccountName = "azureoptimizer-openai-$(Get-Random -Maximum 9999)"
$servicePrincipalName = "AzureOptimizerSP"
$deploymentName = "gpt-4"
$modelName = "gpt-4"
$modelVersion = "0613"

Write-Host "Starting Azure resource setup..." -ForegroundColor Green

# Login to Azure (if not already logged in)
Write-Host "`nStep 1: Checking Azure login status..." -ForegroundColor Yellow
$account = az account show 2>$null
if (-not $account) {
    Write-Host "Not logged in. Logging in to Azure..." -ForegroundColor Yellow
    az login
}

# Get subscription ID
$subscriptionId = (az account show --query id -o tsv)
Write-Host "Using Subscription ID: $subscriptionId" -ForegroundColor Cyan

# Create Resource Group
Write-Host "`nStep 2: Creating Resource Group..." -ForegroundColor Yellow
az group create --name $resourceGroupName --location $location
Write-Host "Resource Group created: $resourceGroupName" -ForegroundColor Green

# Create Azure OpenAI resource
Write-Host "`nStep 3: Creating Azure OpenAI resource..." -ForegroundColor Yellow
az cognitiveservices account create `
    --name $openaiAccountName `
    --resource-group $resourceGroupName `
    --kind OpenAI `
    --sku S0 `
    --location $location `
    --yes

Write-Host "Azure OpenAI resource created: $openaiAccountName" -ForegroundColor Green

# Get OpenAI endpoint and key
Write-Host "`nStep 4: Retrieving OpenAI credentials..." -ForegroundColor Yellow
$openaiEndpoint = az cognitiveservices account show `
    --name $openaiAccountName `
    --resource-group $resourceGroupName `
    --query properties.endpoint `
    -o tsv

$openaiKey = az cognitiveservices account keys list `
    --name $openaiAccountName `
    --resource-group $resourceGroupName `
    --query key1 `
    -o tsv

Write-Host "OpenAI Endpoint: $openaiEndpoint" -ForegroundColor Cyan
Write-Host "OpenAI Key: $openaiKey" -ForegroundColor Cyan

# Deploy GPT-4 model
Write-Host "`nStep 5: Deploying GPT-4 model..." -ForegroundColor Yellow
az cognitiveservices account deployment create `
    --name $openaiAccountName `
    --resource-group $resourceGroupName `
    --deployment-name $deploymentName `
    --model-name $modelName `
    --model-version $modelVersion `
    --model-format OpenAI `
    --sku-capacity 1 `
    --sku-name Standard

Write-Host "GPT-4 model deployed: $deploymentName" -ForegroundColor Green

# Create Service Principal
Write-Host "`nStep 6: Creating Service Principal..." -ForegroundColor Yellow
$spOutput = az ad sp create-for-rbac `
    --name $servicePrincipalName `
    --role Contributor `
    --scopes /subscriptions/$subscriptionId `
    --output json | ConvertFrom-Json

$clientId = $spOutput.appId
$clientSecret = $spOutput.password
$tenantId = $spOutput.tenant

Write-Host "Service Principal created successfully!" -ForegroundColor Green
Write-Host "Client ID: $clientId" -ForegroundColor Cyan
Write-Host "Client Secret: $clientSecret" -ForegroundColor Cyan
Write-Host "Tenant ID: $tenantId" -ForegroundColor Cyan

# Add Reader role for Cost Management
Write-Host "`nStep 7: Adding Cost Management Reader role..." -ForegroundColor Yellow
az role assignment create `
    --assignee $clientId `
    --role "Cost Management Reader" `
    --scope /subscriptions/$subscriptionId

Write-Host "Cost Management Reader role assigned" -ForegroundColor Green

# Update .env file
Write-Host "`nStep 8: Updating .env file..." -ForegroundColor Yellow
$envPath = "C:\__repos\AzureOptimizer\ui\backend\.env"
$envContent = @"
# Azure Configuration
AZURE_SUBSCRIPTION_ID=$subscriptionId
AZURE_TENANT_ID=$tenantId
AZURE_CLIENT_ID=$clientId
AZURE_CLIENT_SECRET=$clientSecret

# Azure OpenAI Configuration
AZURE_OPENAI_ENDPOINT=$openaiEndpoint
AZURE_OPENAI_API_KEY=$openaiKey
AZURE_OPENAI_DEPLOYMENT_NAME=$deploymentName
OPENAI_API_KEY=$openaiKey

# Azure Storage Configuration (if needed)
AZURE_STORAGE_CONNECTION_STRING=your-storage-connection-string-here
AZURE_STORAGE_ACCOUNT_NAME=your-storage-account-name-here
AZURE_STORAGE_ACCOUNT_KEY=your-storage-account-key-here

# Flask Configuration
FLASK_ENV=development
FLASK_DEBUG=True

# Application Settings
LOG_LEVEL=INFO
"@

Set-Content -Path $envPath -Value $envContent
Write-Host ".env file updated successfully!" -ForegroundColor Green

# Summary
Write-Host "`n========================================" -ForegroundColor Green
Write-Host "SETUP COMPLETE!" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Green
Write-Host "`nResource Group: $resourceGroupName" -ForegroundColor Cyan
Write-Host "OpenAI Resource: $openaiAccountName" -ForegroundColor Cyan
Write-Host "OpenAI Endpoint: $openaiEndpoint" -ForegroundColor Cyan
Write-Host "Model Deployment: $deploymentName" -ForegroundColor Cyan
Write-Host "`nService Principal: $servicePrincipalName" -ForegroundColor Cyan
Write-Host "Client ID: $clientId" -ForegroundColor Cyan
Write-Host "Tenant ID: $tenantId" -ForegroundColor Cyan
Write-Host "`n.env file has been updated with all credentials." -ForegroundColor Green
Write-Host "`nIMPORTANT: Store the Client Secret securely: $clientSecret" -ForegroundColor Red
Write-Host "`nYou can now run your backend with: python app.py" -ForegroundColor Yellow
Write-Host "========================================`n" -ForegroundColor Green
