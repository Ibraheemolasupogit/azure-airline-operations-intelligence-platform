# Reference only, non-deploying architecture example.
# No Azure resources are provisioned by this repository.
# Placeholder skeleton only; review before any future infrastructure work.

locals {
  workload_name = "airline-operations-intelligence"
  reference_only = true
}

resource "azurerm_resource_group" "reference" {
  name     = "rg-aoi-${var.environment}-${var.region}"
  location = var.region
  tags = {
    workload       = local.workload_name
    environment    = var.environment
    reference_only = tostring(local.reference_only)
  }
}

resource "azurerm_storage_account" "data_lake_reference" {
  name                     = "aoi${var.environment}stplaceholder"
  resource_group_name      = azurerm_resource_group.reference.name
  location                 = azurerm_resource_group.reference.location
  account_tier             = "Standard"
  account_replication_type = "LRS"
  is_hns_enabled           = true
  min_tls_version          = "TLS1_2"
}
