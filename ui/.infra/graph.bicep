extension 'br:mcr.microsoft.com/bicep/extensions/microsoftgraph/v1.0:0.1.8-preview'

param spazureoptimizerName string = 'Azure Optimizer App Test'
param spazureoptimizerUniqueName string = 'azoptimizerapp'
param spazureoptimizerRedirectUris array = [
  'https://localhost:3000'
]
// param spazureoptimizerAppRoles array = [
//   {
//     displayName: 'Admin'
//     value: 'Admin'
//     description: 'Admin'
//     allowedMemberTypes: [
//       'User'
//       'Group'
//     ]
//     id: 'c6e1c721-efd3-4b90-b0aa-b7d4e2d831dd'


//   }
// ]
// param principalId string = '637ce71f-d686-4b54-8e8e-839d3b95a7f5' //aksops group // The unique identifier (id) for the user, security group, or service principal being granted the app role. Security groups with dynamic memberships are supported. Required on create.

resource spazureoptimizer 'Microsoft.Graph/applications@v1.0' = {
  displayName: spazureoptimizerName
  uniqueName: spazureoptimizerUniqueName

  spa: {
    redirectUris: spazureoptimizerRedirectUris
  }
  // appRoles: spazureoptimizerAppRoles

  
}
// output adminAppRoleId string = spazureoptimizer.appRoles[0].id
output spazureoptimizerprincipalId string = spazureoptimizer.id



// resource AdminRoleAssignment 'Microsoft.Graph/appRoleAssignedTo@v1.0' = {
//   appRoleId: spazureoptimizer.appRoles[0].id
//   principalId:  principalId 
//   resourceDisplayName: 'string'
//   resourceId: spazureoptimizer.id
// }
