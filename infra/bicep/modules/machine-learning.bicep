// Reference only, non-deploying architecture example.
// No Azure resources are provisioned by this repository.

param environment string
param location string
param workloadPrefix string

resource workspace 'Microsoft.MachineLearningServices/workspaces@2024-04-01' = {
  name: '${workloadPrefix}-${environment}-aml-placeholder'
  location: location
  identity: {
    type: 'SystemAssigned'
  }
  properties: {
    friendlyName: 'Airline operations intelligence reference AML workspace'
    publicNetworkAccess: 'Disabled'
  }
}

output referenceMachineLearningWorkspace string = workspace.name
