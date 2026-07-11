// Reference only, non-deploying architecture example.
// No Azure resources are provisioned by this repository.

param environment string
param location string
param workloadPrefix string
param tenantPlaceholder string = 'placeholder-tenant-id'

resource keyVault 'Microsoft.KeyVault/vaults@2023-07-01' = {
  name: '${workloadPrefix}-${environment}-kv-placeholder'
  location: location
  properties: {
    sku: {
      family: 'A'
      name: 'standard'
    }
    tenantId: tenantPlaceholder
    enableRbacAuthorization: true
    enabledForTemplateDeployment: false
  }
}

output referenceKeyVaultName string = keyVault.name
