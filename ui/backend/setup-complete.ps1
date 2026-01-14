# ========================================
# Azure Optimizer - Complete Setup Script
# ========================================
# This script performs the complete setup for Azure Optimizer including:
# 1. Azure OpenAI resource and GPT-4 model deployment
# 2. Storage account for policies and data
# 3. Service Principal with proper RBAC roles
# 4. App Registration for frontend authentication with roles and API permissions
# 5. Environment file configuration

param(
    [Parameter(Mandatory=$false)]
    [string]$ResourceGroupName = "AzureOptimizer-RG",
    
    [Parameter(Mandatory=$false)]
    [string]$Location = "eastus",
    
    [Parameter(Mandatory=$false)]
    [string]$UserEmail = "jamel.achahbar@hotmail.com",
    
    [Parameter(Mandatory=$false)]
    [string]$ServicePrincipalName = "AzureOptimizerSP",
    
    [Parameter(Mandatory=$false)]
    [string]$OpenAIModelName = "gpt-4",
    
    [Parameter(Mandatory=$false)]
    [string]$OpenAIModelVersion = "0613"
)

# Variables
$openaiAccountName = "azureoptimizer-openai-$(Get-Random -Maximum 9999)"
$storageAccountName = "azureoptimizer$(Get-Random -Maximum 999999)"
$deploymentName = "gpt-4"

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Azure Optimizer - Complete Setup" -ForegroundColor Cyan
Write-Host "========================================`n" -ForegroundColor Cyan

# ========================================
# Step 1: Login and Get Subscription
# ========================================
Write-Host "[1/9] Checking Azure login status..." -ForegroundColor Yellow
$account = az account show 2>$null
if (-not $account) {
    Write-Host "Not logged in. Logging in to Azure..." -ForegroundColor Yellow
    az login
}

$subscriptionId = (az account show --query id -o tsv)
$tenantId = (az account show --query tenantId -o tsv)
Write-Host "✓ Subscription ID: $subscriptionId" -ForegroundColor Green
Write-Host "✓ Tenant ID: $tenantId`n" -ForegroundColor Green

# ========================================
# Step 2: Create Resource Group
# ========================================
Write-Host "[2/9] Creating Resource Group..." -ForegroundColor Yellow
az group create --name $ResourceGroupName --location $Location --output none
Write-Host "✓ Resource Group created: $ResourceGroupName`n" -ForegroundColor Green

# ========================================
# Step 3: Create Azure OpenAI Resource
# ========================================
Write-Host "[3/9] Creating Azure OpenAI resource..." -ForegroundColor Yellow
az cognitiveservices account create `
    --name $openaiAccountName `
    --resource-group $ResourceGroupName `
    --kind OpenAI `
    --sku S0 `
    --location $Location `
    --yes `
    --output none

$openaiEndpoint = az cognitiveservices account show `
    --name $openaiAccountName `
    --resource-group $ResourceGroupName `
    --query properties.endpoint `
    -o tsv

$openaiKey = az cognitiveservices account keys list `
    --name $openaiAccountName `
    --resource-group $ResourceGroupName `
    --query key1 `
    -o tsv

Write-Host "✓ Azure OpenAI created: $openaiAccountName" -ForegroundColor Green
Write-Host "  Endpoint: $openaiEndpoint`n" -ForegroundColor Cyan

# Deploy GPT-4 Model
Write-Host "  Deploying GPT-4 model..." -ForegroundColor Yellow
az cognitiveservices account deployment create `
    --name $openaiAccountName `
    --resource-group $ResourceGroupName `
    --deployment-name $deploymentName `
    --model-name $OpenAIModelName `
    --model-version $OpenAIModelVersion `
    --model-format OpenAI `
    --sku-capacity 1 `
    --sku-name Standard `
    --output none

Write-Host "✓ GPT-4 model deployed: $deploymentName`n" -ForegroundColor Green

# ========================================
# Step 4: Create Storage Account
# ========================================
Write-Host "[4/9] Creating Storage Account..." -ForegroundColor Yellow
az storage account create `
    --name $storageAccountName `
    --resource-group $ResourceGroupName `
    --location $Location `
    --sku Standard_LRS `
    --output none

$storageConnectionString = az storage account show-connection-string `
    --name $storageAccountName `
    --resource-group $ResourceGroupName `
    --query connectionString `
    -o tsv

$storageAccountUrl = "https://$storageAccountName.blob.core.windows.net"

# Create container
az storage container create `
    --name "costopttool" `
    --account-name $storageAccountName `
    --connection-string $storageConnectionString `
    --output none

Write-Host "✓ Storage Account created: $storageAccountName`n" -ForegroundColor Green

# ========================================
# Step 5: Create Service Principal
# ========================================
Write-Host "[5/9] Creating Service Principal..." -ForegroundColor Yellow

# Check if SP already exists
$existingSP = az ad sp list --display-name $ServicePrincipalName --query "[0].appId" -o tsv 2>$null

if ($existingSP) {
    Write-Host "Service Principal already exists. Using existing: $existingSP" -ForegroundColor Yellow
    $clientId = $existingSP
    $frontendAppId = $existingSP
    
    # Get app object ID
    $appObjectId = az ad app show --id $clientId --query id -o tsv
    
    Write-Host "⚠ Using existing Service Principal - you'll need to retrieve the client secret manually or reset it" -ForegroundColor Yellow
    $clientSecret = "EXISTING_SP_SECRET_NEEDS_MANUAL_RETRIEVAL"
} else {
    $spOutput = az ad sp create-for-rbac `
        --name $ServicePrincipalName `
        --role Contributor `
        --scopes /subscriptions/$subscriptionId `
        --output json | ConvertFrom-Json

    $clientId = $spOutput.appId
    $clientSecret = $spOutput.password
    $frontendAppId = $clientId
    
    # Get app object ID
    $appObjectId = az ad app show --id $clientId --query id -o tsv
    
    Write-Host "✓ Service Principal created" -ForegroundColor Green
}

Write-Host "  Client ID: $clientId" -ForegroundColor Cyan
Write-Host "  App Object ID: $appObjectId`n" -ForegroundColor Cyan

# ========================================
# Step 6: Assign RBAC Roles at Subscription Level
# ========================================
Write-Host "[6/9] Assigning RBAC roles at subscription level..." -ForegroundColor Yellow

$roles = @(
    "Contributor",
    "Reader",
    "Cost Management Reader",
    "Monitoring Reader",
    "Monitoring Contributor"
)

foreach ($role in $roles) {
    Write-Host "  Assigning $role..." -ForegroundColor Cyan
    az role assignment create `
        --assignee $clientId `
        --role $role `
        --scope /subscriptions/$subscriptionId `
        --output none 2>$null
}

# Assign Storage Blob Data Contributor at storage account level
Write-Host "  Assigning Storage Blob Data Contributor..." -ForegroundColor Cyan
az role assignment create `
    --assignee $clientId `
    --role "Storage Blob Data Contributor" `
    --scope /subscriptions/$subscriptionId/resourceGroups/$ResourceGroupName/providers/Microsoft.Storage/storageAccounts/$storageAccountName `
    --output none 2>$null

Write-Host "✓ RBAC roles assigned at subscription level`n" -ForegroundColor Green

# Assign Reader role at Management Group level
Write-Host "  Assigning Reader at Management Group root level..." -ForegroundColor Yellow
$managementGroupId = $tenantId
az role assignment create `
    --assignee $clientId `
    --role "Reader" `
    --scope /providers/Microsoft.Management/managementGroups/$managementGroupId `
    --output none 2>$null
Write-Host "✓ Reader role assigned at Management Group level`n" -ForegroundColor Green

# ========================================
# Step 7: Configure App Registration for Frontend
# ========================================
Write-Host "[7/9] Configuring App Registration for Frontend..." -ForegroundColor Yellow

# Configure app to support both work/school and personal Microsoft accounts
Write-Host "  Setting sign-in audience..." -ForegroundColor Cyan
az rest --method PATCH `
    --uri "https://graph.microsoft.com/v1.0/applications/$appObjectId" `
    --headers "Content-Type=application/json" `
    --body '{\"signInAudience\":\"AzureADandPersonalMicrosoftAccount\",\"api\":{\"requestedAccessTokenVersion\":2}}' `
    --output none

# Configure as SPA with redirect URIs
Write-Host "  Configuring SPA redirect URIs..." -ForegroundColor Cyan
az rest --method PATCH `
    --uri "https://graph.microsoft.com/v1.0/applications/$appObjectId" `
    --headers "Content-Type=application/json" `
    --body '{\"spa\":{\"redirectUris\":[\"http://localhost:3000\"]},\"web\":{\"redirectUris\":[]}}' `
    --output none

# Create App Roles
Write-Host "  Creating App Roles..." -ForegroundColor Cyan
$appRolesJson = @'
[
  {
    "allowedMemberTypes": ["User"],
    "description": "Admins can perform all operations including Apply mode",
    "displayName": "Admin",
    "id": "00000000-0000-0000-0000-000000000001",
    "isEnabled": true,
    "value": "Admin"
  },
  {
    "allowedMemberTypes": ["User"],
    "description": "Users can view reports and run in Audit mode only",
    "displayName": "User",
    "id": "00000000-0000-0000-0000-000000000002",
    "isEnabled": true,
    "value": "User"
  }
]
'@

$tempFile = "$env:TEMP\approles.json"
$appRolesJson | Out-File -FilePath $tempFile -Encoding UTF8
az ad app update --id $frontendAppId --app-roles "@$tempFile" --output none
Remove-Item $tempFile

Write-Host "  Getting Service Principal..." -ForegroundColor Cyan
$spId = az ad sp list --filter "appId eq '$frontendAppId'" --query "[0].id" -o tsv

if (-not $spId) {
    Write-Host "  Creating Service Principal..." -ForegroundColor Cyan
    az ad sp create --id $frontendAppId --output none
    $spId = az ad sp list --filter "appId eq '$frontendAppId'" --query "[0].id" -o tsv
}

# Assign Admin role to user
Write-Host "  Assigning Admin role to user..." -ForegroundColor Cyan
$userId = az ad user show --id $UserEmail --query id -o tsv 2>$null

if ($userId) {
    $adminRoleId = az ad app show --id $frontendAppId --query "appRoles[?value=='Admin'].id" -o tsv
    
    $assignmentBody = @{
        principalId = $userId
        resourceId = $spId
        appRoleId = $adminRoleId
    } | ConvertTo-Json

    # Check if already assigned
    $existingAssignment = az rest --method GET `
        --uri "https://graph.microsoft.com/v1.0/servicePrincipals/$spId/appRoleAssignedTo" `
        --query "value[?principalId=='$userId' && appRoleId=='$adminRoleId']" -o tsv 2>$null

    if (-not $existingAssignment) {
        az rest --method POST `
            --uri "https://graph.microsoft.com/v1.0/servicePrincipals/$spId/appRoleAssignments" `
            --headers "Content-Type=application/json" `
            --body $assignmentBody `
            --output none 2>$null
    }
    Write-Host "✓ Admin role assigned to $UserEmail" -ForegroundColor Green
} else {
    Write-Host "⚠ User $UserEmail not found - skipping role assignment" -ForegroundColor Yellow
}

# Add API Permissions
Write-Host "  Adding API permissions..." -ForegroundColor Cyan

# Microsoft Graph - User.Read
az ad app permission add --id $frontendAppId `
    --api 00000003-0000-0000-c000-000000000000 `
    --api-permissions e1fe6dd8-ba31-4d61-89e7-88639da4683d=Scope `
    --output none 2>$null

# Microsoft Graph - Directory.Read.All
az ad app permission add --id $frontendAppId `
    --api 00000003-0000-0000-c000-000000000000 `
    --api-permissions 7ab1d382-f21e-4acd-a863-ba3e13f7da61=Role `
    --output none 2>$null

# Azure Service Management - user_impersonation
az ad app permission add --id $frontendAppId `
    --api 797f4846-ba00-4fd7-ba43-dac1f8f63013 `
    --api-permissions 41094075-9dad-400e-a0bd-54e686782033=Scope `
    --output none 2>$null

# Grant admin consent
Write-Host "  Granting admin consent..." -ForegroundColor Cyan
az ad app permission admin-consent --id $frontendAppId --output none 2>$null

# Grant delegated permissions for Azure Management API
az ad app permission grant --id $frontendAppId `
    --api 797f4846-ba00-4fd7-ba43-dac1f8f63013 `
    --scope user_impersonation `
    --output none 2>$null

Write-Host "✓ App Registration configured for frontend authentication`n" -ForegroundColor Green

# ========================================
# Step 8: Create Environment Files
# ========================================
Write-Host "[8/9] Creating environment files..." -ForegroundColor Yellow

# Backend .env
$backendEnvPath = Join-Path $PSScriptRoot ".env"
$backendEnvContent = @"
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

# Azure Storage Configuration
STORAGE_ACCOUNT_URL=$storageAccountUrl
AZURE_STORAGE_CONNECTION_STRING=$storageConnectionString
AZURE_STORAGE_ACCOUNT_NAME=$storageAccountName

# Application Insights Configuration
APPINSIGHTS_INSTRUMENTATIONKEY=00000000-0000-0000-0000-000000000000
"@

Set-Content -Path $backendEnvPath -Value $backendEnvContent
Write-Host "✓ Backend .env created: $backendEnvPath" -ForegroundColor Green

# Frontend .env
$frontendEnvPath = Join-Path $PSScriptRoot "..\frontend\.env"
$frontendEnvContent = @"
REACT_APP_AZURE_CLIENT_ID=$frontendAppId
REACT_APP_AZURE_TENANT_ID=$tenantId
REACT_APP_REDIRECT_URI=http://localhost:3000
"@

Set-Content -Path $frontendEnvPath -Value $frontendEnvContent
Write-Host "✓ Frontend .env created: $frontendEnvPath`n" -ForegroundColor Green

# ========================================
# Step 9: Summary
# ========================================
Write-Host "[9/9] Setup Complete!`n" -ForegroundColor Yellow

Write-Host "========================================" -ForegroundColor Green
Write-Host "AZURE OPTIMIZER - SETUP COMPLETE!" -ForegroundColor Green
Write-Host "========================================`n" -ForegroundColor Green

Write-Host "Resource Details:" -ForegroundColor Cyan
Write-Host "├─ Resource Group: $ResourceGroupName" -ForegroundColor White
Write-Host "├─ Location: $Location" -ForegroundColor White
Write-Host "├─ Subscription: $subscriptionId" -ForegroundColor White
Write-Host "└─ Tenant: $tenantId`n" -ForegroundColor White

Write-Host "Azure OpenAI:" -ForegroundColor Cyan
Write-Host "├─ Resource Name: $openaiAccountName" -ForegroundColor White
Write-Host "├─ Endpoint: $openaiEndpoint" -ForegroundColor White
Write-Host "├─ Model: $deploymentName" -ForegroundColor White
Write-Host "└─ Key: $($openaiKey.Substring(0,10))...`n" -ForegroundColor White

Write-Host "Storage:" -ForegroundColor Cyan
Write-Host "├─ Account Name: $storageAccountName" -ForegroundColor White
Write-Host "├─ URL: $storageAccountUrl" -ForegroundColor White
Write-Host "└─ Container: costopttool`n" -ForegroundColor White

Write-Host "Service Principal:" -ForegroundColor Cyan
Write-Host "├─ Name: $ServicePrincipalName" -ForegroundColor White
Write-Host "├─ Client ID: $clientId" -ForegroundColor White
Write-Host "├─ App Object ID: $appObjectId" -ForegroundColor White
Write-Host "└─ Client Secret: $($clientSecret.Substring(0,10))...`n" -ForegroundColor White

Write-Host "RBAC Roles Assigned:" -ForegroundColor Cyan
Write-Host "├─ Subscription Level:" -ForegroundColor White
Write-Host "│  ├─ Contributor" -ForegroundColor Gray
Write-Host "│  ├─ Reader" -ForegroundColor Gray
Write-Host "│  ├─ Cost Management Reader" -ForegroundColor Gray
Write-Host "│  ├─ Monitoring Reader" -ForegroundColor Gray
Write-Host "│  └─ Monitoring Contributor" -ForegroundColor Gray
Write-Host "├─ Storage Account:" -ForegroundColor White
Write-Host "│  └─ Storage Blob Data Contributor" -ForegroundColor Gray
Write-Host "└─ Management Group Root:" -ForegroundColor White
Write-Host "   └─ Reader`n" -ForegroundColor Gray

Write-Host "Frontend App Registration:" -ForegroundColor Cyan
Write-Host "├─ App ID: $frontendAppId" -ForegroundColor White
Write-Host "├─ Sign-in Audience: Work/School + Personal Microsoft Accounts" -ForegroundColor White
Write-Host "├─ Redirect URI: http://localhost:3000" -ForegroundColor White
Write-Host "├─ App Roles: Admin, User" -ForegroundColor White
Write-Host "├─ API Permissions:" -ForegroundColor White
Write-Host "│  ├─ Microsoft Graph: User.Read" -ForegroundColor Gray
Write-Host "│  ├─ Microsoft Graph: Directory.Read.All" -ForegroundColor Gray
Write-Host "│  └─ Azure Management: user_impersonation" -ForegroundColor Gray
Write-Host "└─ Admin User: $UserEmail`n" -ForegroundColor White

Write-Host "Environment Files:" -ForegroundColor Cyan
Write-Host "├─ Backend: $backendEnvPath" -ForegroundColor White
Write-Host "└─ Frontend: $frontendEnvPath`n" -ForegroundColor White

Write-Host "========================================" -ForegroundColor Green
Write-Host "NEXT STEPS:" -ForegroundColor Yellow
Write-Host "========================================" -ForegroundColor Green
Write-Host "1. Start Backend:" -ForegroundColor White
Write-Host "   cd C:\__repos\AzureOptimizer\ui\backend" -ForegroundColor Cyan
Write-Host "   python app.py`n" -ForegroundColor Cyan

Write-Host "2. Start Frontend:" -ForegroundColor White
Write-Host "   cd C:\__repos\AzureOptimizer\ui\frontend" -ForegroundColor Cyan
Write-Host "   npm start`n" -ForegroundColor Cyan

Write-Host "3. Access Application:" -ForegroundColor White
Write-Host "   http://localhost:3000`n" -ForegroundColor Cyan

Write-Host "4. Login with:" -ForegroundColor White
Write-Host "   $UserEmail`n" -ForegroundColor Cyan

if ($clientSecret -eq "EXISTING_SP_SECRET_NEEDS_MANUAL_RETRIEVAL") {
    Write-Host "⚠ IMPORTANT: Service Principal already existed." -ForegroundColor Red
    Write-Host "You need to either:" -ForegroundColor Yellow
    Write-Host "- Retrieve the existing client secret from your secure storage, OR" -ForegroundColor Yellow
    Write-Host "- Reset the client secret in Azure Portal and update the .env file`n" -ForegroundColor Yellow
} else {
    Write-Host "⚠ IMPORTANT: Store the Client Secret securely!" -ForegroundColor Red
    Write-Host "Client Secret: $clientSecret`n" -ForegroundColor Yellow
}

Write-Host "========================================`n" -ForegroundColor Green
