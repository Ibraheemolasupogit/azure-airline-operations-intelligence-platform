"""Custom exception hierarchy for the platform foundation."""


class AirlineOperationsError(Exception):
    """Base exception for package-specific errors."""


class ConfigurationError(AirlineOperationsError):
    """Raised when platform configuration is missing or invalid."""


class RepositoryValidationError(AirlineOperationsError):
    """Raised when repository foundation validation fails."""


class GenerationConfigurationError(AirlineOperationsError):
    """Raised when synthetic data-generation configuration is invalid."""


class GenerationError(AirlineOperationsError):
    """Raised when synthetic data generation fails."""


class GenerationInvariantError(GenerationError):
    """Raised when generation-time invariants fail."""


class OutputCollisionError(GenerationError):
    """Raised when a generation run would overwrite an existing output."""
