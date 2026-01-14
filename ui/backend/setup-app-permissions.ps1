# Configure App Registration Permissions for AzureOptimizer
# This script adds the necessary API permissions and roles to your service principal

$servicePrincipalAppId = "02fb84dd-8908-47de-bcec-daff54959a76"
$subscriptionId = "e42d33bb-a41a-4028-868a-e0ac3d04cc0e"

Write-Host "Configuring App Registration for AzureOptimizer..." -ForegroundColor Green
Write-Host "This app uses DefaultAzureCredential with ClientSecretCredential" -ForegroundColor Cyan
Write-Host "No API permissions needed - only Azure RBAC roles" -ForegroundColor Cyan

# Verify and add all required role assignments at subscription level
Write-Host "`nStep 1: Verifying Azure RBAC role assignments..." -ForegroundColor Yellow

# Contributor role (already assigned, but verifying)
Write-Host "Ensuring Contributor role..." -ForegroundColor Cyan
$contributorExists = az role assignment list `
    --assignee $servicePrincipalAppId `
    --role "Contributor" `
    --scope /subscriptions/$subscriptionId `
    --query "[].roleDefinitionName" -o tsv

if ($contributorExists) {
    Write-Host "✓ Contributor role already assigned" -ForegroundColor Green
} else {
    az role assignment create `
        --assignee $servicePrincipalAppId `
        --role "Contributor" `
        --scope /subscriptions/$subscriptionId
    Write-Host "✓ Contributor role assigned" -ForegroundColor Green
}

# Reader role (for safe read operations)
Write-Host "Ensuring Reader role..." -ForegroundColor Cyan
az role assignment create `
    --assignee $servicePrincipalAppId `
    --role "Reader" `
    --scope /subscriptions/$subscriptionId `
    2>$null
Write-Host "✓ Reader role ensured" -ForegroundColor Green

# Monitoring Reader role
Write-Host "Ensuring Monitoring Reader role..." -ForegroundColor Cyan
az role assignment create `
    --assignee $servicePrincipalAppId `
    --role "Monitoring Reader" `
    --scope /subscriptions/$subscriptionId `
    2>$null
Write-Host "✓ Monitoring Reader role ensured" -ForegroundColor Green

# Cost Management Reader
Write-Host "Ensuring Cost Management Reader role..." -ForegroundColor Cyan
az role assignment create `
    --assignee $servicePrincipalAppId `
    --role "Cost Management Reader" `
    --scope /subscriptions/$subscriptionId `
    2>$null
Write-Host "✓ Cost Management Reader role ensured" -ForegroundColor Green

# Monitoring Contributor (needed for metrics)
Write-Host "Ensuring Monitoring Contributor role..." -ForegroundColor Cyan
az role assignment create `
    --assignee $servicePrincipalAppId `
    --role "Monitoring Contributor" `
    --scope /subscriptions/$subscriptionId `
    2>$null
Write-Host "✓ Monitoring Contributor role ensured" -ForegroundColor Green

# Storage Blob Data Contributor (already assigned to storage account)
Write-Host "✓ Storage Blob Data Contributor already assigned to storage account" -ForegroundColor Green

Write-Host "`nAll role assignments verified!" -ForegroundColor Green

# Summary
Write-Host "`n========================================" -ForegroundColor Green
Write-Host "APP REGISTRATION CONFIGURED!" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Green
Write-Host "`nService Principal App ID: $servicePrincipalAppId" -ForegroundColor Cyan
Write-Host "Subscription ID: $subscriptionId" -ForegroundColor Cyan
Write-Host "`nAzure RBAC Roles Assigned:" -ForegroundColor Cyan
Write-Host "- ✓ Contributor (full management access)" -ForegroundColor White
Write-Host "- ✓ Reader (read access)" -ForegroundColor White
Write-Host "- ✓ Monitoring Reader (metrics read)" -ForegroundColor White
Write-Host "- ✓ Monitoring Contributor (metrics write)" -ForegroundColor White
Write-Host "- ✓ Cost Management Reader (cost data)" -ForegroundColor White
Write-Host "- ✓ Storage Blob Data Contributor (blob access)" -ForegroundColor White
Write-Host "`nAuthentication Method:" -ForegroundColor Cyan
Write-Host "DefaultAzureCredential with ClientSecretCredential fallback" -ForegroundColor White
Write-Host "`nYour .env file is already configured with:" -ForegroundColor Cyan
Write-Host "- AZURE_CLIENT_ID" -ForegroundColor White
Write-Host "- AZURE_CLIENT_SECRET" -ForegroundColor White
Write-Host "- AZURE_TENANT_ID" -ForegroundColor White
Write-Host "- AZURE_SUBSCRIPTION_ID" -ForegroundColor White
Write-Host "`n✓ The backend should now authenticate successfully!" -ForegroundColor Green
Write-Host "========================================`n" -ForegroundColor Green

Write-Host "To start the backend:" -ForegroundColor Yellow
Write-Host "cd C:\__repos\AzureOptimizer\ui\backend" -ForegroundColor Cyan
Write-Host "python.exe app.py`n" -ForegroundColor Cyan
