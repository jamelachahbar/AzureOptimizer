// ============================================================================
// Frontend Container App Module
// ============================================================================

@description('Location for the Container App')
param location string

@description('Tags to apply to all resources')
param tags object = {}

@description('Name of the Container App')
param containerAppName string

@description('Container Apps Environment ID')
param containerAppsEnvironmentId string

@description('Container image name')
param imageName string

@description('Backend URL for API calls')
param backendUrl string

@description('Target port for the container')
param targetPort int = 80

@description('CPU cores')
param cpu string = '0.25'

@description('Memory')
param memory string = '0.5Gi'

@description('Min replicas')
param minReplicas int = 0

@description('Max replicas')
param maxReplicas int = 3

// ============================================================================
// Container App
// ============================================================================

resource containerApp 'Microsoft.App/containerApps@2024-03-01' = {
  name: containerAppName
  location: location
  tags: union(tags, { 'azd-service-name': 'frontend' })
  properties: {
    managedEnvironmentId: containerAppsEnvironmentId
    workloadProfileName: 'Consumption'
    configuration: {
      activeRevisionsMode: 'Single'
      ingress: {
        external: true
        targetPort: targetPort
        transport: 'http'
        allowInsecure: false
      }
      registries: []
    }
    template: {
      containers: [
        {
          name: 'frontend'
          image: imageName
          resources: {
            cpu: json(cpu)
            memory: memory
          }
          env: [
            {
              name: 'VITE_API_URL'
              value: 'https://${backendUrl}'
            }
          ]
        }
      ]
      scale: {
        minReplicas: minReplicas
        maxReplicas: maxReplicas
        rules: [
          {
            name: 'http-scaling'
            http: {
              metadata: {
                concurrentRequests: '100'
              }
            }
          }
        ]
      }
    }
  }
}

// ============================================================================
// Outputs
// ============================================================================

output containerAppId string = containerApp.id
output containerAppName string = containerApp.name
output fqdn string = containerApp.properties.configuration.ingress.fqdn
output uri string = 'https://${containerApp.properties.configuration.ingress.fqdn}'
