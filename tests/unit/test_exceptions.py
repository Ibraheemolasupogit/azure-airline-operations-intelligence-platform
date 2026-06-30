from airline_operations_intelligence.common.exceptions import (
    AirlineOperationsError,
    ConfigurationError,
    RepositoryValidationError,
)


def test_custom_exceptions_share_package_base_type() -> None:
    assert issubclass(ConfigurationError, AirlineOperationsError)
    assert issubclass(RepositoryValidationError, AirlineOperationsError)
