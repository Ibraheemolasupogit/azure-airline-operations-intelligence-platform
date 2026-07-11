// Reference only, non-deploying architecture example.
// No Azure resources are provisioned by this repository.

param environment string
param location string
param workloadPrefix string

resource workspace 'Microsoft.OperationalInsights/workspaces@2023-09-01' = {
  name: '${workloadPrefix}-${environment}-law-placeholder'
  location: location
  properties: {
    retentionInDays: 30
    sku: {
      name: 'PerGB2018'
    }
  }
}

resource appInsights 'Microsoft.Insights/components@2020-02-02' = {
  name: '${workloadPrefix}-${environment}-appi-placeholder'
  location: location
  kind: 'web'
  properties: {
    Application_Type: 'web'
    WorkspaceResourceId: workspace.id
  }
}

output referenceWorkspaceName string = workspace.name
