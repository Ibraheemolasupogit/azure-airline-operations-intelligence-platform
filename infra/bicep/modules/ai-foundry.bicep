// Reference only, non-deploying architecture example.
// No Azure resources are provisioned by this repository.

param environment string
param location string
param workloadPrefix string

resource account 'Microsoft.CognitiveServices/accounts@2024-04-01-preview' = {
  name: '${workloadPrefix}-${environment}-aif-placeholder'
  location: location
  kind: 'AIServices'
  sku: {
    name: 'S0'
  }
  identity: {
    type: 'SystemAssigned'
  }
  properties: {
    publicNetworkAccess: 'Disabled'
  }
}

output referenceAiFoundryAccountName string = account.name
