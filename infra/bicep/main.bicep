// Reference only, non-deploying architecture example.
// No Azure resources are provisioned by this repository.
// Placeholder skeleton only; review and adapt before any future infrastructure work.

targetScope = 'resourceGroup'

param environment string = 'dev'
param location string = 'uksouth'
param workloadPrefix string = 'aoi'

module storage 'modules/storage.bicep' = {
  name: 'reference-storage-${environment}'
  params: {
    environment: environment
    location: location
    workloadPrefix: workloadPrefix
  }
}

module monitoring 'modules/monitoring.bicep' = {
  name: 'reference-monitoring-${environment}'
  params: {
    environment: environment
    location: location
    workloadPrefix: workloadPrefix
  }
}

module keyvault 'modules/keyvault.bicep' = {
  name: 'reference-keyvault-${environment}'
  params: {
    environment: environment
    location: location
    workloadPrefix: workloadPrefix
  }
}

module machineLearning 'modules/machine-learning.bicep' = {
  name: 'reference-aml-${environment}'
  params: {
    environment: environment
    location: location
    workloadPrefix: workloadPrefix
  }
}

module dataFactory 'modules/data-factory.bicep' = {
  name: 'reference-datafactory-${environment}'
  params: {
    environment: environment
    location: location
    workloadPrefix: workloadPrefix
  }
}

module purview 'modules/purview.bicep' = {
  name: 'reference-purview-${environment}'
  params: {
    environment: environment
    location: location
    workloadPrefix: workloadPrefix
  }
}

module aiFoundry 'modules/ai-foundry.bicep' = {
  name: 'reference-aifoundry-${environment}'
  params: {
    environment: environment
    location: location
    workloadPrefix: workloadPrefix
  }
}
