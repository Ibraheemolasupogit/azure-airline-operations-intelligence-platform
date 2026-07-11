// Reference only, non-deploying architecture example.
// No Azure resources are provisioned by this repository.

param environment string
param location string
param workloadPrefix string

resource account 'Microsoft.Purview/accounts@2021-12-01' = {
  name: '${workloadPrefix}-${environment}-purview-placeholder'
  location: location
  identity: {
    type: 'SystemAssigned'
  }
  properties: {
    publicNetworkAccess: 'Disabled'
  }
}

output referencePurviewName string = account.name
