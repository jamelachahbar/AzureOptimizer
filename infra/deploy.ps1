# ========================================
# Azure Optimizer - Bicep Deployment Script
# ========================================
# This script deploys Azure Optimizer infrastructure using Bicep

param(
    [Parameter(Mandatory=$false)]
    [string]$ParametersFile = "main.bicepparam",
    
    [Parameter(Mandatory=$false)]
    [string]$ServicePrincipalName = "AzureOptimizerSP",
    
    [Parameter(Mandatory=$false)]
    [string]$UserEmail = "jamel.achahbar@hotmail.com",
    
    [Parameter(Mandatory=$false)]
    [switch]$WhatIf
)

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Azure Optimizer - Bicep Deployment" -ForegroundColor Cyan
Write-Host "========================================`n" -ForegroundColor Cyan

# Check if logged in
Write-Host "[1/7] Checking Azure login..." -ForegroundColor Yellow
$account = az account show 2>$null
if (-not $account) {
    Write-Host "Not logged in. Logging in to Azure..." -ForegroundColor Yellow
    az login
}

$subscriptionId = (az account show --query id -o tsv)
$tenantId = (az account show --query tenantId -o tsv)
Write-Host "✓ Subscription: $subscriptionId" -ForegroundColor Green
Write-Host "✓ Tenant: $tenantId`n" -ForegroundColor Green

# Create or get Service Principal
Write-Host "[2/7] Setting up Service Principal..." -ForegroundColor Yellow
$existingSP = az ad sp list --display-name $ServicePrincipalName --query "[0]" -o json 2>$null | ConvertFrom-Json

if ($existingSP) {
    Write-Host "✓ Using existing Service Principal: $ServicePrincipalName" -ForegroundColor Green
    $spObjectId = $existingSP.id
    $clientId = $existingSP.appId
    Write-Host "  Object ID: $spObjectId" -ForegroundColor Cyan
    Write-Host "⚠ Note: You'll need the client secret from your secure storage`n" -ForegroundColor Yellow
    $clientSecret = "RETRIEVE_FROM_SECURE_STORAGE"
} else {
    Write-Host "Creating new Service Principal..." -ForegroundColor Yellow
    $spOutput = az ad sp create-for-rbac `
        --name $ServicePrincipalName `
        --role "Reader" `
        --scopes /subscriptions/$subscriptionId `
        --output json | ConvertFrom-Json
    
    $clientId = $spOutput.appId
    $clientSecret = $spOutput.password
    
    # Get the object ID
    Start-Sleep -Seconds 5  # Wait for AD replication
    $spObjectId = az ad sp show --id $clientId --query id -o tsv
    
    Write-Host "✓ Service Principal created: $ServicePrincipalName" -ForegroundColor Green
    Write-Host "  Object ID: $spObjectId" -ForegroundColor Cyan
    Write-Host "  Client ID: $clientId" -ForegroundColor Cyan
    Write-Host "  Client Secret: $($clientSecret.Substring(0,10))...`n" -ForegroundColor Cyan
}

# Update parameters file with SP Object ID
Write-Host "[3/7] Updating parameters file..." -ForegroundColor Yellow
$paramsContent = Get-Content $ParametersFile -Raw
$paramsContent = $paramsContent -replace '<REPLACE_WITH_SP_OBJECT_ID>', $spObjectId
$paramsContent | Set-Content $ParametersFile
Write-Host "✓ Parameters file updated with SP Object ID`n" -ForegroundColor Green

# Deploy Bicep template
Write-Host "[4/7] Deploying Bicep template..." -ForegroundColor Yellow
if ($WhatIf) {
    Write-Host "Running in WhatIf mode - no changes will be made`n" -ForegroundColor Yellow
    $deploymentOutput = az deployment sub what-if `
        --location eastus `
        --template-file main.bicep `
        --parameters $ParametersFile `
        --output json 2>&1
} else {
    $deploymentOutput = az deployment sub create `
        --location eastus `
        --template-file main.bicep `
        --parameters $ParametersFile `
        --output json 2>&1 | ConvertFrom-Json
}

if ($LASTEXITCODE -eq 0 -and !$WhatIf) {
    Write-Host "✓ Bicep deployment completed successfully`n" -ForegroundColor Green
    
    # Extract outputs
    $outputs = $deploymentOutput.properties.outputs
    $resourceGroupName = $outputs.resourceGroupName.value
    $openAIEndpoint = $outputs.openAIEndpoint.value
    $openAIDeploymentName = $outputs.openAIDeploymentName.value
    $storageAccountName = $outputs.storageAccountName.value
    $storageBlobEndpoint = $outputs.storageBlobEndpoint.value
} elseif ($WhatIf) {
    Write-Host "✓ WhatIf completed - review changes above`n" -ForegroundColor Green
    exit 0
} else {
    Write-Host "✗ Deployment failed. Error:" -ForegroundColor Red
    Write-Host $deploymentOutput -ForegroundColor Red
    exit 1
}

# Get OpenAI key
Write-Host "[5/7] Retrieving OpenAI key..." -ForegroundColor Yellow
$openAIAccountName = $outputs.openAIResourceId.value.Split('/')[-1]
$openAIKey = az cognitiveservices account keys list `
    --name $openAIAccountName `
    --resource-group $resourceGroupName `
    --query key1 `
    -o tsv
Write-Host "✓ OpenAI key retrieved`n" -ForegroundColor Green

# Get storage connection string
Write-Host "  Retrieving storage connection string..." -ForegroundColor Yellow
$storageConnectionString = az storage account show-connection-string `
    --name $storageAccountName `
    --resource-group $resourceGroupName `
    --query connectionString `
    -o tsv
Write-Host "✓ Storage connection string retrieved`n" -ForegroundColor Green

# Assign Reader role at Management Group level
Write-Host "[6/7] Assigning Reader role at Management Group level..." -ForegroundColor Yellow
$managementGroupId = $tenantId
az role assignment create `
    --assignee $clientId `
    --role "Reader" `
    --scope /providers/Microsoft.Management/managementGroups/$managementGroupId `
    --output none 2>$null
Write-Host "✓ Management Group role assigned`n" -ForegroundColor Green

# Configure App Registration for Frontend
Write-Host "[7/7] Configuring App Registration..." -ForegroundColor Yellow

# Get app object ID
$appObjectId = az ad app show --id $clientId --query id -o tsv

# Configure as SPA
az rest --method PATCH `
    --uri "https://graph.microsoft.com/v1.0/applications/$appObjectId" `
    --headers "Content-Type=application/json" `
    --body '{\"signInAudience\":\"AzureADandPersonalMicrosoftAccount\",\"api\":{\"requestedAccessTokenVersion\":2}}' `
    --output none

az rest --method PATCH `
    --uri "https://graph.microsoft.com/v1.0/applications/$appObjectId" `
    --headers "Content-Type=application/json" `
    --body '{\"spa\":{\"redirectUris\":[\"http://localhost:3000\"]},\"web\":{\"redirectUris\":[]}}' `
    --output none

# Create App Roles
$appRolesJson = @'
[
  {
    "allowedMemberTypes": ["User"],
    "description": "Admins can perform all operations including Apply mode",
    "displayName": "Admin",
    "id": "f8e7a3f4-7b8c-4d2e-9f1a-5b6c8d9e0f2a",
    "isEnabled": true,
    "value": "Admin"
  },
  {
    "allowedMemberTypes": ["User"],
    "description": "Users can view reports and run in Audit mode only",
    "displayName": "User",
    "id": "a1b2c3d4-e5f6-7890-1234-567890abcdef",
    "isEnabled": true,
    "value": "User"
  }
]
'@

$tempFile = "$env:TEMP\approles.json"
$appRolesJson | Out-File -FilePath $tempFile -Encoding UTF8
az ad app update --id $clientId --app-roles "@$tempFile" --output none 2>$null
Remove-Item $tempFile

# Add API permissions
az ad app permission add --id $clientId --api 00000003-0000-0000-c000-000000000000 --api-permissions e1fe6dd8-ba31-4d61-89e7-88639da4683d=Scope --output none 2>$null
az ad app permission add --id $clientId --api 00000003-0000-0000-c000-000000000000 --api-permissions 06da0dbc-49e2-44d2-8312-53f166ab848a=Scope --output none 2>$null
az ad app permission add --id $clientId --api 797f4846-ba00-4fd7-ba43-dac1f8f63013 --api-permissions 41094075-9dad-400e-a0bd-54e686782033=Scope --output none 2>$null
az ad app permission admin-consent --id $clientId --output none 2>$null
az ad app permission grant --id $clientId --api 797f4846-ba00-4fd7-ba43-dac1f8f63013 --scope user_impersonation --output none 2>$null

# Assign admin role to user
$spId = az ad sp show --id $clientId --query id -o tsv
$userId = az ad user show --id $UserEmail --query id -o tsv 2>$null

if ($userId) {
    $adminRoleId = az ad app show --id $clientId --query "appRoles[?value=='Admin'].id" -o tsv
    $assignmentBody = @{
        principalId = $userId
        resourceId = $spId
        appRoleId = $adminRoleId
    } | ConvertTo-Json
    
    az rest --method POST `
        --uri "https://graph.microsoft.com/v1.0/servicePrincipals/$spId/appRoleAssignments" `
        --headers "Content-Type=application/json" `
        --body $assignmentBody `
        --output none 2>$null
}

Write-Host "✓ App Registration configured`n" -ForegroundColor Green

# Create environment files
Write-Host "Creating environment files..." -ForegroundColor Yellow

$backendEnvPath = Join-Path $PSScriptRoot "..\ui\backend\.env"
$backendEnvContent = @"
# Azure Configuration
AZURE_SUBSCRIPTION_ID=$subscriptionId
AZURE_TENANT_ID=$tenantId
AZURE_CLIENT_ID=$clientId
AZURE_CLIENT_SECRET=$clientSecret

# Azure OpenAI Configuration
AZURE_OPENAI_ENDPOINT=$openAIEndpoint
AZURE_OPENAI_API_KEY=$openAIKey
AZURE_OPENAI_DEPLOYMENT_NAME=$openAIDeploymentName
OPENAI_API_KEY=$openAIKey

# Azure Storage Configuration
STORAGE_ACCOUNT_URL=$storageBlobEndpoint
AZURE_STORAGE_CONNECTION_STRING=$storageConnectionString
AZURE_STORAGE_ACCOUNT_NAME=$storageAccountName

# Application Insights Configuration
APPINSIGHTS_INSTRUMENTATIONKEY=00000000-0000-0000-0000-000000000000
"@

Set-Content -Path $backendEnvPath -Value $backendEnvContent

$frontendEnvPath = Join-Path $PSScriptRoot "..\ui\frontend\.env"
$frontendEnvContent = @"
REACT_APP_AZURE_CLIENT_ID=$clientId
REACT_APP_AZURE_TENANT_ID=$tenantId
REACT_APP_REDIRECT_URI=http://localhost:3000
"@

Set-Content -Path $frontendEnvPath -Value $frontendEnvContent

Write-Host "✓ Environment files created`n" -ForegroundColor Green

# Summary
Write-Host "========================================" -ForegroundColor Green
Write-Host "BICEP DEPLOYMENT COMPLETE!" -ForegroundColor Green
Write-Host "========================================`n" -ForegroundColor Green

Write-Host "Deployed Resources:" -ForegroundColor Cyan
Write-Host "├─ Resource Group: $resourceGroupName" -ForegroundColor White
Write-Host "├─ Azure OpenAI: $openAIAccountName" -ForegroundColor White
Write-Host "│  ├─ Endpoint: $openAIEndpoint" -ForegroundColor Gray
Write-Host "│  └─ Model: $openAIDeploymentName" -ForegroundColor Gray
Write-Host "└─ Storage Account: $storageAccountName`n" -ForegroundColor White

Write-Host "Service Principal:" -ForegroundColor Cyan
Write-Host "├─ Name: $ServicePrincipalName" -ForegroundColor White
Write-Host "├─ Object ID: $spObjectId" -ForegroundColor White
Write-Host "├─ Client ID: $clientId" -ForegroundColor White
Write-Host "├─ Roles: Contributor, Reader, Cost Management Reader, Monitoring Reader/Contributor" -ForegroundColor White
Write-Host "├─ App Roles: Admin, User" -ForegroundColor White
Write-Host "├─ API Permissions: User.Read, Directory.Read.All, user_impersonation" -ForegroundColor White
Write-Host "└─ User Assignment: $UserEmail → Admin role`n" -ForegroundColor White

Write-Host "Environment Files:" -ForegroundColor Cyan
Write-Host "├─ Backend: $backendEnvPath" -ForegroundColor White
Write-Host "└─ Frontend: $frontendEnvPath`n" -ForegroundColor White

if ($clientSecret -ne "RETRIEVE_FROM_SECURE_STORAGE") {
    Write-Host "⚠ IMPORTANT: Store Client Secret securely!" -ForegroundColor Red
    Write-Host "Client Secret: $clientSecret`n" -ForegroundColor Yellow
}

Write-Host "========================================`n" -ForegroundColor Green
