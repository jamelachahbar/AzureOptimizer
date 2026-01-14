// ============================================================================
// Microsoft Graph Module - App Registration
// ============================================================================
// Creates App Registration for React frontend with SPA authentication
// Requires Microsoft Graph Bicep extension (Bicep 0.24.0+)
// 
// NOTE: This module is deployed at resource group scope but uses MS Graph
// extension which operates at tenant level for Entra ID resources.
// ============================================================================

// Import Microsoft Graph extension
extension microsoftGraphV1_0

@description('Application display name')
param applicationDisplayName string

@description('Redirect URIs for SPA')
param redirectUris array = [
  'http://localhost:3000'
]

@description('User Object ID for Admin role assignment')
param userObjectId string = ''

// ============================================================================
// Variables
// ============================================================================

// App Role GUIDs (deterministic for idempotency)
var adminRoleId = 'f8e7a3f4-7b8c-4d2e-9f1a-5b6c8d9e0f2a'
var userRoleId = 'a1b2c3d4-e5f6-7890-1234-567890abcdef'

// Well-known API Permission IDs
// Microsoft Graph API
var microsoftGraphAppId = '00000003-0000-0000-c000-000000000000'
var userReadPermissionId = 'e1fe6dd8-ba31-4d61-89e7-88639da4683d' // User.Read (Delegated)
var directoryReadAllPermissionId = '06da0dbc-49e2-44d2-8312-53f166ab848a' // Directory.Read.All (Delegated)

// Azure Management API  
var azureManagementAppId = '797f4846-ba00-4fd7-ba43-dac1f8f63013'
var userImpersonationPermissionId = '41094075-9dad-400e-a0bd-54e686782033' // user_impersonation (Delegated)

// ============================================================================
// Application Registration
// ============================================================================

resource application 'Microsoft.Graph/applications@v1.0' = {
  uniqueName: applicationDisplayName
  displayName: applicationDisplayName
  signInAudience: 'AzureADandPersonalMicrosoftAccount'
  
  // SPA Configuration for React
  spa: {
    redirectUris: redirectUris
  }
  
  // API Configuration
  api: {
    requestedAccessTokenVersion: 2
  }
  
  // Web configuration (optional - for additional redirect URIs)
  web: {
    implicitGrantSettings: {
      enableIdTokenIssuance: true
      enableAccessTokenIssuance: false
    }
  }
  
  // App Roles for authorization
  appRoles: [
    {
      id: adminRoleId
      allowedMemberTypes: [
        'User'
      ]
      description: 'Administrators have full access to all Azure Optimizer features including Apply mode'
      displayName: 'Admin'
      isEnabled: true
      value: 'Admin'
    }
    {
      id: userRoleId
      allowedMemberTypes: [
        'User'
      ]
      description: 'Users have read-only access to Azure Optimizer features'
      displayName: 'User'
      isEnabled: true
      value: 'User'
    }
  ]
  
  // Required API Permissions
  requiredResourceAccess: [
    {
      // Microsoft Graph permissions
      resourceAppId: microsoftGraphAppId
      resourceAccess: [
        {
          id: userReadPermissionId
          type: 'Scope' // Delegated permission
        }
        {
          id: directoryReadAllPermissionId
          type: 'Scope' // Delegated permission
        }
      ]
    }
    {
      // Azure Management API permissions
      resourceAppId: azureManagementAppId
      resourceAccess: [
        {
          id: userImpersonationPermissionId
          type: 'Scope' // Delegated permission
        }
      ]
    }
  ]
}

// ============================================================================
// Service Principal for the Application
// ============================================================================

resource servicePrincipal 'Microsoft.Graph/servicePrincipals@v1.0' = {
  appId: application.appId
  accountEnabled: true
  
  // Tags for enterprise apps visibility
  tags: [
    'WindowsAzureActiveDirectoryIntegratedApp'
  ]
}

// ============================================================================
// Role Assignments (optional - if userObjectId provided)
// ============================================================================

resource adminRoleAssignment 'Microsoft.Graph/appRoleAssignedTo@v1.0' = if (!empty(userObjectId)) {
  appRoleId: adminRoleId
  principalId: userObjectId
  resourceId: servicePrincipal.id
}

// ============================================================================
// OAuth2 Permission Grants (Admin Consent)
// ============================================================================

// Note: Admin consent for delegated permissions
// This grants consent for all users in the tenant
resource oauth2PermissionGrant 'Microsoft.Graph/oauth2PermissionGrants@v1.0' = {
  clientId: servicePrincipal.id
  consentType: 'AllPrincipals'
  resourceId: servicePrincipal.id
  scope: 'User.Read Directory.Read.All user_impersonation'
}

// ============================================================================
// Outputs
// ============================================================================

@description('The Application (Client) ID')
output applicationClientId string = application.appId

@description('The Application Object ID')
output applicationObjectId string = application.id

@description('The Service Principal ID')
output servicePrincipalId string = servicePrincipal.id

@description('Admin Role ID')
output adminRoleId string = adminRoleId

@description('User Role ID')
output userRoleId string = userRoleId
