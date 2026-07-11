// Reference only, non-deploying architecture example.
// No Azure resources are provisioned by this repository.

param environment string
param location string
param workloadPrefix string

resource factory 'Microsoft.DataFactory/factories@2018-06-01' = {
  name: '${workloadPrefix}-${environment}-adf-placeholder'
  location: location
  identity: {
    type: 'SystemAssigned'
  }
}

output referenceDataFactoryName string = factory.name
