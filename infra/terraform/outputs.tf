# Reference only, non-deploying architecture example.
# No Azure resources are provisioned by this repository.

output "reference_resource_group_name" {
  description = "Reference resource group name for architecture mapping only."
  value       = azurerm_resource_group.reference.name
}

output "reference_storage_account_name" {
  description = "Reference storage account name for architecture mapping only."
  value       = azurerm_storage_account.data_lake_reference.name
}
