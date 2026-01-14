# Configure Frontend App Registration with Admin and User Roles
# This sets up the user authentication app with proper roles

$frontendAppId = "02fb84dd-8908-47de-bcec-daff54959a76"  # Using the app registration we created
$userEmail = "jamel.achahbar@hotmail.com"  # Your user email

Write-Host "Configuring Frontend App Registration with Roles..." -ForegroundColor Green

# Step 1: Get App Object ID
Write-Host "`nStep 1: Getting App Registration details..." -ForegroundColor Yellow
$appObjectId = az ad app show --id $frontendAppId --query id -o tsv
Write-Host "App Object ID: $appObjectId" -ForegroundColor Cyan

# Step 2: Configure app to support both work/school and personal Microsoft accounts
Write-Host "`nStep 2: Configuring sign-in audience and token version..." -ForegroundColor Yellow
az rest --method PATCH --uri "https://graph.microsoft.com/v1.0/applications/$appObjectId" --headers "Content-Type=application/json" --body '{\"signInAudience\":\"AzureADandPersonalMicrosoftAccount\",\"api\":{\"requestedAccessTokenVersion\":2}}'
Write-Host "✓ App configured to support work/school and personal Microsoft accounts" -ForegroundColor Green

# Step 3: Check current app roles
Write-Host "`nStep 3: Checking current app roles..." -ForegroundColor Yellow
$currentRoles = az ad app show --id $frontendAppId --query appRoles -o json | ConvertFrom-Json

if ($currentRoles.Count -eq 0) {
    Write-Host "No app roles defined. Creating Admin and User roles..." -ForegroundColor Yellow
    
    # Create app roles manifest
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
    
    # Save to temp file
    $tempFile = "$env:TEMP\approles.json"
    $appRolesJson | Out-File -FilePath $tempFile -Encoding UTF8
    
    # Update app with roles
    az ad app update --id $frontendAppId --app-roles "@$tempFile"
    Write-Host "✓ App roles created successfully" -ForegroundColor Green
    
    Remove-Item $tempFile
} else {
    Write-Host "App roles already defined:" -ForegroundColor Green
    $currentRoles | ForEach-Object {
        Write-Host "  - $($_.displayName): $($_.value)" -ForegroundColor Cyan
    }
}

# Step 4: Get Service Principal for the app
Write-Host "`nStep 4: Getting Enterprise Application (Service Principal)..." -ForegroundColor Yellow
$spId = az ad sp list --filter "appId eq '$frontendAppId'" --query "[0].id" -o tsv

if (-not $spId) {
    Write-Host "Service Principal not found. Creating..." -ForegroundColor Yellow
    az ad sp create --id $frontendAppId
    $spId = az ad sp list --filter "appId eq '$frontendAppId'" --query "[0].id" -o tsv
    Write-Host "✓ Service Principal created" -ForegroundColor Green
} else {
    Write-Host "✓ Service Principal exists: $spId" -ForegroundColor Green
}

# Step 5: Get user object ID
Write-Host "`nStep 5: Getting user object ID..." -ForegroundColor Yellow
$userId = az ad user show --id $userEmail --query id -o tsv
Write-Host "User Object ID: $userId" -ForegroundColor Cyan

# Step 6: Get Admin role ID
Write-Host "`nStep 6: Getting Admin role ID..." -ForegroundColor Yellow
$adminRoleId = az ad app show --id $frontendAppId --query "appRoles[?value=='Admin'].id" -o tsv
Write-Host "Admin Role ID: $adminRoleId" -ForegroundColor Cyan

# Step 7: Assign Admin role to user
Write-Host "`nStep 7: Assigning Admin role to user..." -ForegroundColor Yellow
$assignmentBody = @{
    principalId = $userId
    resourceId = $spId
    appRoleId = $adminRoleId
} | ConvertTo-Json

# Check if assignment already exists
$existingAssignment = az rest --method GET --uri "https://graph.microsoft.com/v1.0/servicePrincipals/$spId/appRoleAssignedTo" --query "value[?principalId=='$userId' && appRoleId=='$adminRoleId']" -o tsv

if ($existingAssignment) {
    Write-Host "✓ Admin role already assigned to user" -ForegroundColor Green
} else {
    az rest --method POST --uri "https://graph.microsoft.com/v1.0/servicePrincipals/$spId/appRoleAssignments" --headers "Content-Type=application/json" --body $assignmentBody
    Write-Host "✓ Admin role assigned to user" -ForegroundColor Green
}

# Step 8: Configure API permissions
Write-Host "`nStep 8: Ensuring API permissions..." -ForegroundColor Yellow

# Microsoft Graph - User.Read
az ad app permission add --id $frontendAppId --api 00000003-0000-0000-c000-000000000000 --api-permissions e1fe6dd8-ba31-4d61-89e7-88639da4683d=Scope 2>$null

# Microsoft Graph - Directory.Read.All (for reading user roles)
az ad app permission add --id $frontendAppId --api 00000003-0000-0000-c000-000000000000 --api-permissions 7ab1d382-f21e-4acd-a863-ba3e13f7da61=Role 2>$null

# Azure Service Management - user_impersonation (for Azure Management API access)
Write-Host "Adding Azure Management API permission..." -ForegroundColor Yellow
az ad app permission add --id $frontendAppId --api 797f4846-ba00-4fd7-ba43-dac1f8f63013 --api-permissions 41094075-9dad-400e-a0bd-54e686782033=Scope 2>$null
az ad app permission grant --id $frontendAppId --api 797f4846-ba00-4fd7-ba43-dac1f8f63013 --scope user_impersonation 2>$null

Write-Host "✓ API permissions configured" -ForegroundColor Green

# Step 9: Grant admin consent
Write-Host "`nStep 9: Granting admin consent..." -ForegroundColor Yellow
az ad app permission admin-consent --id $frontendAppId
Write-Host "✓ Admin consent granted" -ForegroundColor Green

# Summary
Write-Host "`n========================================" -ForegroundColor Green
Write-Host "FRONTEND APP REGISTRATION CONFIGURED!" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Green
Write-Host "`nApp Registration ID: $frontendAppId" -ForegroundColor Cyan
Write-Host "App Object ID: $appObjectId" -ForegroundColor Cyan
Write-Host "Service Principal ID: $spId" -ForegroundColor Cyan
Write-Host "`nApp Roles Defined:" -ForegroundColor Cyan
Write-Host "- Admin (full access, can use Apply mode)" -ForegroundColor White
Write-Host "- User (read-only, Audit mode only)" -ForegroundColor White
Write-Host "`nRole Assignment:" -ForegroundColor Cyan
Write-Host "✓ $userEmail assigned as Admin" -ForegroundColor Green
Write-Host "`nAPI Permissions:" -ForegroundColor Cyan
Write-Host "- User.Read (delegated)" -ForegroundColor White
Write-Host "- Directory.Read.All (application)" -ForegroundColor White
Write-Host "- Azure Management API - user_impersonation (delegated)" -ForegroundColor White
Write-Host "`nNext Steps:" -ForegroundColor Yellow
Write-Host "1. Users logging in will now receive role claims in their tokens" -ForegroundColor White
Write-Host "2. Admins can use Apply mode in the UI" -ForegroundColor White
Write-Host "3. Regular Users are restricted to Audit mode" -ForegroundColor White
Write-Host "`nTo assign more users:" -ForegroundColor Yellow
Write-Host "Go to Azure Portal > Enterprise Applications > AzureOptimizerSP > Users and groups" -ForegroundColor Cyan
Write-Host "========================================`n" -ForegroundColor Green
