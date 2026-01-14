# Azure Storage Account Setup Script
# Run this script to create storage account and configure it for AzureOptimizer

# Variables - Update these if needed
$resourceGroupName = "AzureOptimizer-RG"
$location = "eastus"
$storageAccountName = "azureoptimizer$(Get-Random -Maximum 999999)"
$containerName = "costopttool"
$servicePrincipalId = "02fb84dd-8908-47de-bcec-daff54959a76"  # From your existing SP

Write-Host "Starting Azure Storage Account setup..." -ForegroundColor Green

# Get subscription ID
$subscriptionId = (az account show --query id -o tsv)
Write-Host "Using Subscription ID: $subscriptionId" -ForegroundColor Cyan

# Create Storage Account
Write-Host "`nStep 1: Creating Storage Account..." -ForegroundColor Yellow
az storage account create `
    --name $storageAccountName `
    --resource-group $resourceGroupName `
    --location $location `
    --sku Standard_LRS `
    --kind StorageV2 `
    --allow-blob-public-access false `
    --min-tls-version TLS1_2

Write-Host "Storage Account created: $storageAccountName" -ForegroundColor Green

# Get Storage Account details
Write-Host "`nStep 2: Retrieving Storage Account details..." -ForegroundColor Yellow
$storageAccountId = az storage account show `
    --name $storageAccountName `
    --resource-group $resourceGroupName `
    --query id `
    -o tsv

$storageAccountUrl = "https://$storageAccountName.blob.core.windows.net"

Write-Host "Storage Account URL: $storageAccountUrl" -ForegroundColor Cyan

# Assign Storage Blob Data Contributor role to Service Principal
Write-Host "`nStep 3: Assigning Storage Blob Data Contributor role to Service Principal..." -ForegroundColor Yellow
az role assignment create `
    --assignee $servicePrincipalId `
    --role "Storage Blob Data Contributor" `
    --scope $storageAccountId

Write-Host "Role assigned successfully" -ForegroundColor Green

# Create container using Azure CLI (requires authentication)
Write-Host "`nStep 4: Creating blob container..." -ForegroundColor Yellow
az storage container create `
    --name $containerName `
    --account-name $storageAccountName `
    --auth-mode login

Write-Host "Container created: $containerName" -ForegroundColor Green

# Upload initial files to container
Write-Host "`nStep 5: Uploading initial files..." -ForegroundColor Yellow
$policiesPath = ".\policies\policies.yaml"
$schemaPath = ".\src\schema.json"

if (Test-Path $policiesPath) {
    az storage blob upload `
        --account-name $storageAccountName `
        --container-name $containerName `
        --name "policies.yaml" `
        --file $policiesPath `
        --auth-mode login `
        --overwrite
    Write-Host "Uploaded policies.yaml" -ForegroundColor Green
} else {
    Write-Host "Warning: policies.yaml not found at $policiesPath" -ForegroundColor Yellow
}

if (Test-Path $schemaPath) {
    az storage blob upload `
        --account-name $storageAccountName `
        --container-name $containerName `
        --name "schema.json" `
        --file $schemaPath `
        --auth-mode login `
        --overwrite
    Write-Host "Uploaded schema.json" -ForegroundColor Green
} else {
    Write-Host "Warning: schema.json not found at $schemaPath" -ForegroundColor Yellow
}

# Update .env file
Write-Host "`nStep 6: Updating .env file..." -ForegroundColor Yellow
$envPath = ".\.env"
$envContent = Get-Content $envPath -Raw

# Update STORAGE_ACCOUNT_URL
$envContent = $envContent -replace 'STORAGE_ACCOUNT_URL=.*', "STORAGE_ACCOUNT_URL=$storageAccountUrl"

Set-Content -Path $envPath -Value $envContent
Write-Host ".env file updated successfully!" -ForegroundColor Green

# Summary
Write-Host "`n========================================" -ForegroundColor Green
Write-Host "STORAGE ACCOUNT SETUP COMPLETE!" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Green
Write-Host "`nStorage Account Name: $storageAccountName" -ForegroundColor Cyan
Write-Host "Storage Account URL: $storageAccountUrl" -ForegroundColor Cyan
Write-Host "Container Name: $containerName" -ForegroundColor Cyan
Write-Host "`nPermissions:" -ForegroundColor Cyan
Write-Host "- Storage Blob Data Contributor role assigned to Service Principal" -ForegroundColor Cyan
Write-Host "`n.env file has been updated." -ForegroundColor Green
Write-Host "`nYou can now run your backend with: python app.py" -ForegroundColor Yellow
Write-Host "========================================`n" -ForegroundColor Green
